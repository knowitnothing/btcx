import os
from decimal import Decimal
from twisted.internet import reactor, task
from twisted.words.xish.utility import EventDispatcher

USER_AGENT = 'btcx-bot'

CURRENCY_FACTOR = {
        "BTC": Decimal(100000000),
        "JPY": Decimal(1000),
        "LAG": Decimal(1000000)
}
CURRENCY_DEFAULT_FACTOR = Decimal(100000)

def currency_factor(currency):
    cur = currency.upper()
    if cur not in CURRENCY_FACTOR:
        return CURRENCY_DEFAULT_FACTOR
    return CURRENCY_FACTOR[cur]


class ExchangeEvent(EventDispatcher):
    def __init__(self, **kwargs):
        EventDispatcher.__init__(self, **kwargs)
        self.listener = {}

    def listen(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.addObserver(event, cb)

        lid = self._gen_lid()
        self.listener[lid] = (msg, cb)
        return lid

    def listen_once(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.addOnetimeObserver(event, cb)

        lid = self._gen_lid()
        self.listener[lid] = (msg, cb)
        return lid

    def emit(self, msg, data=None):
        event = "%s/%s" % (self.prefix, msg)
        # Instead of calling dispatch directly, we circumvent the bug
        # https://twistedmatrix.com/trac/ticket/6507 by doing:
        task.deferLater(reactor, 0, self.dispatch, data, event)

    def remove(self, lid):
        if lid in self.listener:
            msg, cb = self.listener.pop(lid)
            self._remove_listener(msg, cb)
        else:
            print "Listener %s not found." % lid

    def _remove_listener(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.removeObserver(event, cb)

    def _gen_lid(self):
        return os.urandom(16)
