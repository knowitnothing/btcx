# See https://www.bitstamp.net/api/

from __future__ import print_function

import sys
import time
from urllib import urlencode
from decimal import Decimal

import treq
from twisted.python import log
from twisted.internet import reactor, task
from twisted.web.http_headers import Headers

from common import USER_AGENT, ExchangeEvent


class Bitstamp(object): # XXX Only public data for the moment.

    def __init__(self, key, secret, host):
        self.evt = ExchangeEvent(eventprefix="//bitstamp")
        self.host = host

        # Ideally the nonce should be synced between various clients.
        self.nonce = int(time.time())


    def call(self, urlpart, cb, **kwargs):
        headers = Headers({"User-Agent": [USER_AGENT]})
        d = treq.get('%s/%s' % (self.host, urlpart),
                params=kwargs, headers=headers)
        d.addCallback(lambda response: self._decode_or_error(
            response, cb, urlpart))

    def _decode_or_error(self, response, cb, *args):
        d = treq.json_content(response)
        d.addCallback(cb, *args)
        errcb = lambda err, *args: print("Error when calling %s. %s" % (
            ' '.join(args), err.getBriefTraceback()))
        d.addErrback(errcb, *args)


    # Bitstamp API

    # Public
    def ticker(self):
        # last (last BTC price),
        # high (day), low (day), volume (day),
        # bid (highest buy order), ask (lowest sell order)
        self.call('api/ticker', lambda result, _:
                self.evt.emit('ticker', result)) # XXX Map to Decimal.

    def order_book(self, group=1):
        self.call('api/order_book', lambda result, _:
                self.evt.emit('order_book', result), # XXX Format.
                group=group)

    def transactions(self, timedelta=86400):
        """Obtain transactions for the last timedelta seconds."""
        self.call('api/transactions', lambda result, _:
                self.evt.emit('trades', result), # XXX Format.
                timedelta=timedelta)

    def reserves(self):
        """Obtain the Bitinstant USD reserves."""
        self.call('api/bitinstant', lambda result, _:
                self.evt.emit('reserves', Decimal(result['usd'])))

    def eur_usd_rate(self):
        # buy: buy conversion rate
        # sell: sell conversion rate
        self.call('api/eur_usd', lambda result, _:
                self.evt.emit('eur_usd', (
                    Decimal(result['buy']), Decimal(result['sell']))))

    # XXX Missing private.


def create_client(key='', secret='', addr='https://www.bitstamp.net',
        debug=False, extradebug=False):

    if extradebug:
        log.startLogging(sys.stdout)

    return Bitstamp(key, secret, addr)

def start(*args):
    # This intentionally does nothing. Consider it as a uniformity
    # layer among the different APIs.
    pass
