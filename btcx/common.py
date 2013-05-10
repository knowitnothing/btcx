import os
from decimal import Decimal
from collections import namedtuple
from twisted.python import log
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

# Common format for events expected to be used by the different
# implementations.

# Currently, the currencies involved in a trade are determined
# by the application.
Trade = namedtuple('Trade', [
    'id',         # trade id
    'timestamp',  # trade timestamp
    'type',       # either 'a' (ask) or 'b' (buy) trade
    'price',      # value received/paid
    'amount'      # amount sold/bought
    ])
TRADE_EMPTY = Trade(None, None, None, None, None)

# An user order.
Order = namedtuple('Order', [
    'id',         # order id
    'timestamp',  # order timestamp
    'type',       # either 'a' (ask) or 'b' (buy) order
    'status',     # order status
    'price',      # value for selling/buying
    'amount',     # amount being sold/bought
    'pair'        # (x, y): currencies used for buying and receiving
    ])

# Depth data.
Depth = namedtuple('Depth', [
    'type',       # (b)id/(a)sk depth item
    'price',      # item price
    'volume'      # volume at price
    ])
DEPTH_EMPTY = Depth(None, None, None)

# Ticker data.
Ticker = namedtuple('Ticker', [
    'sell',       # Last sell price
    'buy',        # Last buy price
    'last',       # Last price
    'low',        # Lowest price in a period (day for example)
    'avg',        # Average price in a period
    'high',       # Highest price in a period
    'vol',        # Current volume
    'vwap',       # Volume-weighted average price in a period
    'pair'
    ])


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


class CallOnEvent(object):
    """
    CallOnEvent is to be used as a mixin. It is expected that
    the class inheriting it provides an ExchangeEvent instance
    through instance.evt

    The main intention of this class is to provide an easier way
    to call into a protocol instance built by buildProtocol (i.e.,
    not always available).
    """

    def call(self, func, *args, **kwargs):
        event = kwargs.pop('on_event', 'connected') # Call on this event.
        once = kwargs.pop('once', False) # Call only once (listen once).
        # If the function name is a string, then we should call it
        # through the client. Otherwise it is any kind of object that
        # is used as a callback.
        client = True if isinstance(func, str) else False

        call_func = self._call if client else self._callback
        listen = 'listen_once' if once else 'listen'
        listen_func = getattr(self.evt, listen)

        x = lambda ignored: call_func(event, func, args, kwargs)

        if isinstance(event, str): # Common case for the moment.
            listen_func(event, x)
            return
        # Otherwise, event is assumed to be a sequence of events.
        for evt in event:
            listen_func(evt, x)


    def _call(self, event, func, args, kwargs):
        log.msg("Client-Calling %s%s %s due to event %s" % (
            func, args, kwargs, event))
        getattr(self.client, func)(*args, **kwargs)

    def _callback(self, event, func, args, kwargs):
        log.msg("Calling %s%s %s due to event %s" % (
            func, args, kwargs, event))
        func(self.client, *args, **kwargs)
