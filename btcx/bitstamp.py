# See https://www.bitstamp.net/api/

from __future__ import print_function

import sys
from decimal import Decimal
from twisted.python import log

from common import ExchangeEvent
from http import HTTPAPI


class Bitstamp(HTTPAPI): # XXX Only public data for the moment.

    def __init__(self, key, secret, host):
        super(Bitstamp, self).__init__(host)
        self.evt = ExchangeEvent(eventprefix="//bitstamp")


    # Public API

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
                # XXX Format.
                self.evt.emit('trades', result) if result else None,
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
