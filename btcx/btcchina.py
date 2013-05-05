# See -- if you know what to see, please tell me --

from __future__ import print_function

import sys
from twisted.python import log

from common import ExchangeEvent
from http import HTTPAPI


class BTCChina(HTTPAPI): # XXX Only public data for the moment.

    def __init__(self, key, secret, host):
        super(BTCChina, self).__init__(host)
        self.evt = ExchangeEvent(eventprefix="//btcchina")


    # Public API

    def ticker(self):
        # last (last BTC price),
        # high (day), low (day), vol (day),
        # buy (highest buy order), sell (lowest sell order)
        # Coin RMB (Renminbi)
        self.call('bc/ticker', lambda result, _:
                self.evt.emit('ticker', result['ticker']))

    def trades(self):
        # A list of trades. Each item contains date, price, amount, tid.
        self.call('bc/trades', lambda result, _:
                self.evt.emit('trades', result))

    # XXX Not sure what is missing.



def create_client(key='', secret='', addr='https://btcchina.com/',
        debug=False, extradebug=False):

    if extradebug:
        log.startLogging(sys.stdout)

    return BTCChina(key, secret, addr)
