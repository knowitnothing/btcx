# See https://btc-e.com/api/documentation and https://btc-e.com/page/2

from __future__ import print_function

import sys
import time
import hmac
import hashlib
from urllib import urlencode
from decimal import Decimal

import treq
from twisted.python import log
from twisted.internet import reactor, task
from twisted.web.http_headers import Headers

from common import USER_AGENT, ExchangeEvent


class BTCe(object):

    def __init__(self, key, secret, host='https://btc-e.com'):
        self.evt = ExchangeEvent(eventprefix="//btce")
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
                "User-Agent": [USER_AGENT],
        })
        d = treq.post('%s/tapi' % self.host, data=call_p, headers=headers)
        d.addCallback(lambda response: self._decode_or_error(
            response, cb, method, kwargs))

    def call(self, urlpart, cb):
        headers = Headers({"User-Agent": [USER_AGENT]})
        d = treq.get('%s/%s' % (self.host, urlpart), headers=headers)
        d.addCallback(lambda response: self._decode_or_error(
            response, cb, urlpart))


    def _decode_or_error(self, response, cb, *args):
        d = treq.json_content(response)
        d.addCallback(cb, *args)
        errcb = lambda err, *args: print("Error when calling %s: %s" % (
            ' '.join(args), err.getErrorMessage()))
        d.addErrback(errcb, *args)



    # BTC-e API

    # Public
    def fee(self, coin='btc', currency='usd'):
        coin = coin.lower()
        currency = currency.lower()
        self.call('api/2/%s_%s/fee' % (coin, currency),
                lambda data, _: self.evt.emit('fee', data))

    def trades(self, coin='btc', currency='usd'):
        coin = coin.lower()
        currency = currency.lower()
        self.call('api/2/%s_%s/trades' % (coin, currency),
                lambda data, _: self.evt.emit('trades', data))

    def depth(self, coin='btc', currency='usd'):
        coin = coin.lower()
        currency = currency.lower()
        self.call('api/2/%s_%s/depth' % (coin, currency),
                lambda data, _: self.evt.emit('depth', data))

    # Private
    def get_info(self):
        self.signed_call('getInfo', self._generic_cb('info'))

    def trans_history(self, from_=0, count=1000, from_id=0, end_id=None,
            order=None, since=0, end=None):
        params = {'from': from_, 'count': count, 'from_id': from_id, 'since': 0}
        if end_id: params['end_id'] = end_id
        if end: params['end'] = end
        if order: params['order'] = order
        self.signed_call('TransHistory', self._generic_cb('trans_hist'),
                **params)

    def trade_history(self, from_=0, count=1000, from_id=0, end_id=None,
            order=None, since=0, end=None, pair=None):
        params = {'from': from_, 'count': count, 'from_id': from_id,
                  'since': 0}
        if end_id: params['end_id'] = end_id
        if end: params['end'] = end
        if order: params['order'] = order
        if pair: params['pair'] = pair
        self.signed_call('TradeHistory', self._generic_cb('trade_hist'),
                **params)

    def order_list(self, from_=0, count=1000, from_id=0, end_id=None,
            order=None, since=0, end=None, pair=None, active=1):
        params = {'from': from_, 'count': count, 'from_id': from_id,
                  'since': 0}
        if end_id: params['end_id'] = end_id
        if end: params['end'] = end
        if order: params['order'] = order
        if pair: params['pair'] = pair
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
                    self.nonce += 1
                    self.signed_call(args[0], self._generic_cb(evtname),
                            **args[1])
                else:
                    self.evt.emit('error', (evtname, data['error'], args))
        return result


def create_client(key, secret, addr="https://btc-e.com",
        debug=False, extradebug=False):

    if extradebug:
        log.startLogging(sys.stdout)

    btce = BTCe(key, secret, addr)
    return btce

def start(*args):
    # This intentionally does nothing. Consider it as a uniformity
    # layer among the different APIs.
    pass
