# See https://en.bitcoin.it/wiki/MtGox/API/Streaming

from __future__ import print_function

import sys
import json
import time
import hmac
import base64
import hashlib
import binascii
from decimal import Decimal

import treq # Used for public HTTP-API calls
from twisted.python import log
from twisted.internet import reactor, task
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.web.http_headers import Headers
from twisted.words.xish.utility import EventDispatcher
from autobahn.websocket import (WebSocketProtocol, WebSocketClientProtocol,
                                WebSocketClientFactory, connectWS)


from common import USER_AGENT, ExchangeEvent


CURRENCY_FACTOR = {
        "BTC": Decimal(100000000),
        "JPY": Decimal(1000),
        "lag": Decimal(1000000)
}
CURRENCY_DEFAULT_FACTOR = Decimal(100000)


def calc_tid(hours_ago):
    hours_ago = Decimal(hours_ago)
    one_second = Decimal(1e6) # in microseconds
    now = int(time.time()) * one_second
    return int(now - (hours_ago * (one_second * 60 * 60)))


class MtgoxProtocol(WebSocketClientProtocol):

    def __init__(self, evt, key, secret, currency, coin, http_api):

        self.evt = evt
        self.key = key
        self.secret = secret
        self.currency = currency
        self.coin = coin
        self.http_api = http_api

        self.subscribed_channel = {}

        self.nonce = int(time.time() * 1e6)
        self.pending_scall = {}

        self.ping_payload = "hello"
        self.ping_when = 0   # ping's timestamp.
        self.ping_task = task.LoopingCall(self.ping)
        self.ping_delay = 30 # x seconds.
        self.ping_limit = 2  # Wait y second for a PONG, or disconnect.
        self.pong_task = task.LoopingCall(self.pong_check)


    def ping(self):
        if not self.ping_when:
            print("PING (%s)" % self.ping_payload)
            self.ping_when = time.time()
            self.pong_task.start(self.ping_limit / 2.)
            self.sendPing(self.ping_payload)

    def pong_check(self):
        if self.ping_when:
            diff = time.time() - self.ping_when
            if diff > self.ping_limit:
                self.sendClose(WebSocketProtocol.CLOSE_STATUS_CODE_NORMAL,
                        "PONG took too long")

    def signed_call(self, endpoint, params=None, item='BTC', **kwargs):
        if not self.key:
            # Running without key/secret pair.
            return None

        self.nonce += 1
        req_id = hashlib.md5(str(self.nonce)).hexdigest()

        query = {'call': endpoint,
                 'params': params or {},
                 'item': item,
                 'currency': self.currency,
                 'id': req_id,
                 'nonce': self.nonce}
        query.update(kwargs)
        jd_query = json.dumps(query)
        sign = hmac.new(self.secret, jd_query, hashlib.sha512)
        msg = '%s%s%s' % (self.key, sign.digest(), jd_query)
        call = {'op': 'call',
                'call': base64.b64encode(msg),
                'id': req_id,
                'context': 'mtgox.com'}

        self.pending_scall[req_id] = query
        self.sendMessage(json.dumps(call))
        return req_id

    def http_public_call(self, endpoint, version=2, **kwargs):
        #print('calling %s/%d/%s' % (self.http_api, version, endpoint), kwargs)
        headers = Headers({"User-Agent": [USER_AGENT]})
        d = treq.get('%s/%d/%s' % (self.http_api, version, endpoint),
                params=kwargs, headers=headers)
        d.addCallback(lambda response:
                self._handle_http_api(response, endpoint))

    def _handle_http_api(self, response, endpoint): # Take **kwargs too XXX
        d = treq.json_content(response)
        d.addCallback(self._handle_result, endpoint)
        d.addErrback(lambda err, endpoint:
                print("Error when calling %s: %s" % (endpoint,
                    err.getBriefTraceback())), endpoint)


    # Helper/semiAPI functions

    def order_add(self, otype, amount_int, price_int=0):
        params = {'type': otype, 'amount_int': amount_int}
        if price_int:
            params['price_int'] = price_int
        return self.signed_call('/order/add', params)

    def order_add_buy(self, amount_int, price_int=0):
        return self.order_add('bid', amount_int, price_int)

    def order_add_sell(self, amount_int, price_int=0):
        return self.order_add('ask', amount_int, price_int)

    def order_cancel(self, oid):
        return self.signed_call('/order/cancel', {'oid': oid})

    def order_list(self):
        """
        For each placed order, an 'userorder' event will be emitted with
        args (oid, otype, timestamp, status, price, amount, currency, coin).
        """
        return self.signed_call('/orders')

    def private_info(self):
        """
        On completion, an 'info' event will be emitted with
        args (trading fee, rights).
        """
        return self.signed_call('/info')

    def wallet_history(self, currency, **kwargs):
        kwargs.update({'currency': currency})
        return self.signed_call('/wallet/history', kwargs)

    def subscribe_type(self, typ):
        self.sendMessage(json.dumps({'op': 'mtgox.subscribe', 'type': typ}))

    def unsubscribe_cid(self, cid):
        self.sendMessage(json.dumps({'op': 'unsubscribe', 'channel': cid}))
        if cid in self.subscribed_channel:
            del self.subscribed_channel[cid]


    # Public calls on HTTP API

    def load_trades_since(self, hours_ago=Decimal('0.5'), tid=None):
        # If the "hours_ago" parameter (default half hour) is None,
        # the last 24 hours of trades will be returned. Otherwise,
        # it will fetch up to maximum of 24 hours of trades.
        #
        # If tid is specified, it takes preference over hours_ago.
        #
        # A 'trade_fetch' event will be emitted for each trade
        # returned. The last one will contain only None values.
        #
        if hours_ago is None and tid is None:
            params = {}
        elif tid is not None:
            params = {'since': tid}
        else:
            params = {'since': calc_tid(hours_ago)}

        self.http_public_call('%s%s/money/trades/fetch' % (
            self.coin, self.currency),
            version=2, **params)

    def depth_fetch(self):
        """Request data regarding recent market depth."""
        return self.http_public_call('%s%s/money/depth/fetch' % (
            self.coin, self.currency), version=2)

    def depth_full(self):
        """
        Request complete data regarding market depth.
        Limit yourself to 5 requests per hour for this information (from docs).
        """
        return self.http_public_call('%s%s/money/depth/full' % (
            self.coin, self.currency), version=2)


    # Methods called to handle MtGox responses.

    def _handle_remark(self, data):
        if not data["success"]:
            # Some typical reasons:
            # 'Method not found'
            # 'Currency parameter is mandatory'
            # 'Order amount is too low'
            # ...
            req_id = data["id"] if "id" in data else None
            orig_data = None
            if req_id in self.pending_scall:
                orig_data = self.pending_scall.pop(req_id)
            self.evt.emit('remark', (data['message'], req_id, orig_data))
        else:
            print("Unknown successfull remark: %s" % repr(data))


    def _extract_trade(self, trade):
        tid = int(trade['tid'])
        currency = trade["price_currency"]
        if currency != self.currency or trade['primary'].lower() != 'y':
            # Ignore trades in different currency or that are not
            # primary.
            return (tid, None, None, None, None, None)

        timestamp = int(trade['date'])
        ttype = trade['trade_type']
        factor = CURRENCY_FACTOR.get(currency, CURRENCY_DEFAULT_FACTOR)
        price = Decimal(trade['price_int']) / factor
        coin = trade['item']
        amount = Decimal(trade['amount_int']) / CURRENCY_FACTOR[coin]

        return (tid, timestamp, ttype, price, amount, coin)


    def _handle_result(self, result, req_id):
        if req_id in self.pending_scall:
            query = self.pending_scall.pop(req_id)
            start = 1 if query['call'].startswith('/') else 0
            name = query['call'][start:]
        else:
            # Result from HTTP API
            name = req_id
            # XXX Handle when result['result'] != 'success'
            if result['result'] != 'success':
                print("HTTP API FAILED!", name, result)
            result = result['data']

        if name == 'idkey':
            self.evt.emit(name, result)
        elif name == 'orders':
            for order in result:
                self.evt.emit('userorder', self._extract_order(order))
        elif name == 'info':
            # Result from private_info method.
            trade_fee = Decimal(str(result['Trade_Fee']))
            rights = result['Rights']
            self.evt.emit(name, (trade_fee, rights))
        elif name.endswith('money/trades/fetch'):
            # Result from load_trades_since method.
            for trade in result or []:
                trade = self._extract_trade(trade)
                if trade[0] is None:
                    continue
                self.evt.emit('trade_fetch', trade)
            self.evt.emit('trade_fetch', (None, ) * 6) # end
        elif name.endswith('money/depth/fetch') or name.endswith(
                'money/depth/full'):
            # Result from depth_fetch or depth_full method.
            factor = CURRENCY_FACTOR.get(self.currency, CURRENCY_DEFAULT_FACTOR)
            coin = CURRENCY_FACTOR['BTC']
            for typ in ('bid', 'ask'):
                entry = '%ss' % typ
                for order in result[entry]:
                    price = Decimal(order['price_int']) / factor
                    amount = Decimal(order['amount_int']) / coin
                    self.evt.emit('order_fetch', (typ, price, amount))
            self.evt.emit('order_fetch', (None, None, None))
        else:
            rtype = name.replace('/', '_')
            print("Emitting result event for %s" % rtype)
            self.evt.emit('result', (rtype, result))


    def _handle_depth(self, depth):
        currency = depth["currency"]
        if currency != self.currency:
            # Ignore bid/ask in other currencies.
            return

        coin = depth["item"]
        dtype = depth["type_str"]
        volume = Decimal(depth["total_volume_int"]) / CURRENCY_FACTOR[coin]
        factor = CURRENCY_FACTOR.get(currency, CURRENCY_DEFAULT_FACTOR)
        price = Decimal(depth["price_int"]) / factor

        self.evt.emit('depth', (dtype, price, volume, coin))

    def _handle_ticker(self, ticker):
        # Assumption: currency is the same in every field.
        currency = ticker["sell"]["currency"]
        if currency != self.currency:
            return

        factor = CURRENCY_FACTOR.get(currency, CURRENCY_DEFAULT_FACTOR)
        ask = Decimal(ticker["sell"]["value_int"]) / factor
        bid = Decimal(ticker["buy"]["value_int"]) / factor
        coin = ticker["vol"]["currency"]
        vol = Decimal(ticker["vol"]["value_int"]) / CURRENCY_FACTOR[coin]
        vwap = Decimal(ticker["vwap"]["value_int"]) / factor
        low = Decimal(ticker["low"]["value_int"]) / factor
        high = Decimal(ticker["high"]["value_int"]) / factor

        self.evt.emit('ticker', (ask, bid, vwap, low, high, vol, coin))

    def _handle_trade(self, trade):
        trade = self._extract_trade(trade)
        if trade[0] is None:
            return

        self.evt.emit('trade', trade)


    def _extract_order(self, order):
        oid = order['oid']
        coin = order['item']
        amount = Decimal(order['amount']['value_int']) / CURRENCY_FACTOR[coin]
        currency = order['currency']
        factor = CURRENCY_FACTOR.get(currency, CURRENCY_DEFAULT_FACTOR)
        price = Decimal(order['price']['value_int']) / factor
        timestamp = int(order['date'])
        status = order['status']
        otype = order['type']

        return (oid, otype, timestamp, status, price, amount, currency, coin)

    def _handle_private_user_order(self, order):
        if 'item' in order:
            self.evt.emit('userorder', self._extract_order(order))
        else:
            self.evt.emit('userorder', (order['oid'], None, None, 'removed',
                None, None, None, None))


    def _handle_private_wallet(self, wallet):
        # Reason for update (in, out, fee, earned, spent, withdraw, deposit)
        reason = wallet["op"]
        info = wallet["info"]
        ref = wallet["ref"] # Reference code for bank transfer, if applicable.

        currency = wallet['balance']['currency']
        factor = CURRENCY_FACTOR.get(currency, CURRENCY_DEFAULT_FACTOR)
        amount = Decimal(wallet['balance']['value_int']) / factor

        self.evt.emit('wallet_update', (currency, amount, reason, info, ref))

    def _handle_private_lag(self, lag):
        lag_sec = Decimal(lag['age']) / CURRENCY_FACTOR['lag']
        self.evt.emit('lag', lag_sec)


    # Methods called by Websocket.

    def onOpen(self):
        # Handshake completed.
        print("Connected")
        self.ping_task.start(self.ping_delay)
        self.factory.setup()
        self.evt.emit('connected')

    def onClose(self, clean, code, reason):
        print("Disconnected")
        for task in (self.ping_task, self.pong_task):
            if task.running:
                task.stop()
        self.evt.emit('disconnected')

    def onError(self, msg):
        print("ERROR!!!", msg)

    def onPong(self, payload):
        print("PONG (%s)" % payload, time.time() - self.ping_when)
        self.ping_when = 0
        self.pong_task.stop()

    def onMessage(self, payload, binary):
        # Message received from MtGox.

        data = json.loads(payload)
        op = data["op"]


        if op == "result":
            # Output from HTTP API version 1 that were sent over the websocket.
            self._handle_result(data["result"], data["id"])

        elif op == "private":
            # Real time market information
            msg_type = data["private"]

            if msg_type not in self.subscribed_channel:
                self.subscribed_channel[msg_type] = data['channel']
                self.evt.emit('channel', (msg_type, data['channel']))

            msg = data[msg_type]
            if msg_type == "ticker":
                self._handle_ticker(msg)
            elif msg_type == "trade":
                # Some transaction took place.
                self._handle_trade(msg)
            elif msg_type == "depth":
                # Order placed or removed.
                self._handle_depth(msg)
            elif msg_type == "result":
                print("Private result", msg_type, data)
            else:
                method = getattr(self, '_handle_private_%s' % msg_type, None)
                if method:
                    method(msg)
                else:
                    print("Unknown private message", msg_type)

        elif op == "remark":
            # A server message, usually a warning.
            self._handle_remark(data)

        elif op in ("subscribe", "unsubscribe"): # Ok
            print("%sd %s %s" % (op.title(),
                    'to' if op == 'subscribe' else 'from', msg["channel"]))

        else:
            print("Unknown op", op)



class MtgoxFactoryClient(WebSocketClientFactory, ReconnectingClientFactory):

    protocol = MtgoxProtocol

    def __init__(self, key, secret, currency, http_api, coin='BTC', **kwargs):
        WebSocketClientFactory.__init__(self, **kwargs)

        self.evt = ExchangeEvent(eventprefix="//mtgox")
        self.key = binascii.unhexlify(key.replace('-', ''))
        self.secret = base64.b64decode(secret)
        self.currency = currency
        self.http_api = http_api
        self.coin = coin

        self.known_channels = {
                'ticker': 'd5f06780-30a8-4a48-a2f8-7ed181b4a13f',
                'depth':  '24e67e0d-1cad-4cc0-9e7a-f8523ef460fe',
                'trade':  'dbf1dee9-4f2e-4a08-8cb7-748919a71b21',
                'lag':    '85174711-be64-4de1-b783-0628995d7914'}

        self.client = None
        self.connected = False

        self.evt.listen('idkey', self.got_idkey)
        self.evt.listen('remark', self.got_remark)
        self.evt.listen('result', self.got_result)
        self.evt.listen('channel', self.got_channel)

        self.idkey_refresh_task = task.LoopingCall(self.refresh_idkey)


    def clientConnectionFailed(self, connector, reason):
        """Connection failed to complete."""
        print("ConnectionFailed")
        self._disconnected()
        ReconnectingClientFactory.clientConnectionFailed(self,
                connector, reason)

    def clientConnectionLost(self, connector, reason):
        """Established connection has been lost."""
        print("ConnectionLost")
        self._disconnected()
        ReconnectingClientFactory.clientConnectionLost(self,
                connector, reason)

    def buildProtocol(self, addr):
        print("buildProtocol")
        self.resetDelay()
        proto = self.protocol(self.evt, self.key, self.secret,
                              self.currency, self.coin, self.http_api)
        proto.factory = self
        self.client = proto
        return proto

    def _disconnected(self):
        # Perform the mundane tasks when we disconnect.
        self.connected = False
        if self.idkey_refresh_task.running:
            self.idkey_refresh_task.stop()


    def setup(self):
        # Websocket connected.
        self.connected = True

        # "Light" client. Unsubscribe from known channels.
        for cid in self.known_channels.itervalues():
            self.client.unsubscribe_cid(cid)

        # idkey expires after 24 hours, so refreshing each 8 hours
        # looks good enough.
        if self.key:
            self.idkey_refresh_task.start(60 * 60 * 8)


    # Helpers

    def send_request(self, json_msg):
        if self.connected:
            self.client.sendMessage(json_msg)
        else:
            print("Client is not connected! Retrying in one second")
            task.deferLater(reactor, 1, self.send_request, json_msg)

    def send_signed_call(self, call, params=None, item='BTC', **kwargs):
        if self.connected:
            return self.client.signed_call(call, params, item, **kwargs)
        else:
            print("Client is not connected! Retrying in one second")
            task.deferLater(reactor, 1, self.send_signed_call, call,
                    params, item, **kwargs)

    def __getattr__(self, attr):
        try:
            return getattr(self.client, attr)
        except AttributeError:
            raise AttributeError('%r object has no attribute %r' % (
                    self.__class__.__name__, attr))

    # API Callbacks (due to events)

    def refresh_idkey(self):
        req_id = self.send_signed_call("/idkey")
        print("Sent request to /idkey [%s]" % req_id)

    def got_idkey(self, idkey):
        self.send_request(json.dumps({'op': 'mtgox.subscribe', 'key': idkey}))
        print("Sent message to subscribe for account-private messages")

    def got_result(self, (rtype, result)):
        print("Result for %s: %s" % (rtype, result))

    def got_remark(self, (msg, req_id, data)):
        print("Remark: %s [%s] -- %s" % (msg, req_id, data))

    def got_channel(self, (name, cid)):
        print("Subscribed in %s: %s" % (name, cid))
        if name not in self.known_channels:
            self.known_channels[name] = cid



def create_client(key='', secret='', currency="USD", secure=True,
        addr="websocket.mtgox.com", http_addr="data.mtgox.com/api",
        debug=False, extradebug=False):

    if extradebug:
        log.startLogging(sys.stdout)

    port = 443 if secure else 80
    ws_origin = "%s:%d" % (addr, port)
    ws_addr = "%s://%s:%d" % ('wss' if secure else 'ws', addr, port)
    ws_path = "/mtgox?Currency="

    http_api_url = '%s://%s' % ('https' if secure else 'http', http_addr)

    factory = MtgoxFactoryClient(key, secret, currency.upper(),
            http_api_url, url="%s%s%s" % (ws_addr, ws_path, currency),
            useragent="%s\x0d\x0aOrigin: %s" % (USER_AGENT, ws_origin),
            debug=debug, debugCodePaths=debug)
    factory.setProtocolOptions(version=13)

    return factory

def start(factory):
    connectWS(factory, timeout=5)
