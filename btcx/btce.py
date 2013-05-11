# See https://btc-e.com/api/documentation and https://btc-e.com/page/2

from __future__ import print_function

import time
import hmac
import hashlib
from urllib import urlencode
from decimal import Decimal

import treq
from twisted.internet import reactor, task
from twisted.web.http_headers import Headers

import common
from http import HTTPAPI

class BTCe(HTTPAPI):

    def __init__(self, key, secret, host):
        super(BTCe, self).__init__(host)
        self.evt = common.Event(eventprefix="//btce")
        self.key = key.encode('ascii')
        self.secret = secret
        self.host = host

        # Ideally the nonce should be synced between various clients.
        self.nonce = int(time.time())


    def signed_call(self, method, cb, **kwargs):
        if self.nonce > time.time():
            # Let us keep the nonce behind the clock so
            # the +1 increment keeps working after this client
            # restarts.
            task.deferLater(reactor, 0.35, self.signed_call,
                    method, cb, **kwargs)
            return
        self.nonce += 1

        call_p = {"method": method, "nonce": self.nonce}
        call_p.update(kwargs)
        call = urlencode(call_p)
        sign = hmac.new(self.secret, call, digestmod=hashlib.sha512)
        headers = Headers({
                "Content-type": ["application/x-www-form-urlencoded"],
                "Key": [self.key],
                "Sign": [sign.hexdigest()],
                "User-Agent": [common.USER_AGENT],
        })
        d = treq.post('%s/tapi' % self.host, data=call_p, headers=headers)
        d.addCallback(lambda response: self.decode_or_error(
            response, cb, method, kwargs))


    # BTC-e API

    # Public
    def fee(self, p1='btc', p2='usd'):
        p1, p2 = p1.lower(), p2.lower()
        self.http_call('api/2/%s_%s/fee' % (p1, p2),
                lambda data, _: self.evt.emit('fee', data))

    def ticker(self, p1='btc', p2='usd'):
        p1, p2 = p1.lower(), p2.lower()
        self.http_call('api/2/%s_%s/ticker' % (p1, p2), self._handle_ticker,
                pair=(p1, p2))

    def trades(self, p1='btc', p2='usd'):
        # For each trade fetched, an 'trade_fetch' event will be emitted.
        p1, p2 = p1.lower(), p2.lower()
        self.http_call('api/2/%s_%s/trades' % (p1, p2), self._handle_trades)

    def depth(self, p1='btc', p2='usd'):
        # For each item from depth fetched, an 'depth_fetch' event will be
        # emitted.
        p1, p2 = p1.lower(), p2.lower()
        self.http_call('api/2/%s_%s/depth' % (p1, p2), self._handle_depth)

    def _handle_ticker(self, data, url, pair):
        data = data['ticker']
        ticker = [data[key] for key in ('sell', 'buy', 'last', 'low', 'avg',
            'high', 'vol')]
        ticker.append(None) # No VWAP data.
        ticker.append(pair)
        self.evt.emit('ticker_fetch', common.Ticker(*ticker))

    def _handle_trades(self, data, url):
        for trade in reversed(data): # Return from older to most recent.
            trade = common.Trade(trade['tid'], trade['date'],
                                 trade['trade_type'][0],
                                 Decimal(str(trade['price'])),
                                 Decimal(str(trade['amount'])))
            self.evt.emit('trade_fetch', trade)
        self.evt.emit('trade_fetch', common.TRADE_EMPTY)

    def _handle_depth(self, data, url):
        for typ, items in data.iteritems():
            for price, volume in items:
                depth = common.Depth(typ[0],
                                     Decimal(str(price)), Decimal(str(volume)))
                self.evt.emit('depth_fetch', depth)
        self.evt.emit('depth_fetch', common.DEPTH_EMPTY)


    # Private (these retrieve data only about the own account)
    def info(self):
        self.signed_call('getInfo', self._generic_cb('info'))

    def trans_history(self, **kwargs):
        """
        Accepted keywords: from, count, from_id, end_id, order, since, end
        """
        params = dict((k.rstrip('_'), v) for k, v in kwargs.iteritems())
        self.signed_call('TransHistory', self._generic_cb('trans_hist'),
                **params)

    def trade_history(self, **kwargs):
        """
        Accepted keywords: from, count, from_id, end_id, order, since,
                           end, pair
        """
        params = dict((k.rstrip('_'), v) for k, v in kwargs.iteritems())
        self.signed_call('TradeHistory', self._generic_cb('trade_hist'),
                **params)

    def order_list(self, **kwargs):
        """
        Accepted keywords: from, count, from_id, end_id, order, since,
                           end, pair, active

        Requests a list of open orders.
        """
        params = dict((k.rstrip('_'), v) for k, v in kwargs.iteritems())
        self.signed_call('OrderList', self._generic_cb('order_list'), **params)

    def order_cancel(self, oid):
        self.signed_call('CancelOrder', self._generic_cb('order_cancel'),
                **{'order_id': oid})

    def trade(self, pair, ttype, rate, amount):
        self.signed_call('Trade', self._generic_cb('trade'),
                **{'pair': pair, 'type': ttype,
                   'rate': rate, 'amount': amount})


    def _generic_cb(self, evtname):
        def result(data, *args):
            if data['success']:
                self.evt.emit(evtname, data['return'])
            else:
                if data['error'].startswith('invalid nonce parameter'):
                    # XXX This and every other print should be logged.
                    print(">>> Retrying", evtname)
                    self.nonce = int(time.time())
                    self.signed_call(args[0], self._generic_cb(evtname),
                            **args[1])
                else:
                    self.evt.emit('error', (evtname, data['error'], args))
        return result


def create_client(key='', secret='', addr="https://btc-e.com"):
    return BTCe(key, secret, addr)
