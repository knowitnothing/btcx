from twisted.words.xish.utility import EventDispatcher

USER_AGENT = 'btcx-bot'

class ExchangeEvent(EventDispatcher):
    def __init__(self, **kwargs):
        EventDispatcher.__init__(self, **kwargs)

    def listen(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.addObserver(event, cb)

    def emit(self, msg, data=None):
        event = "%s/%s" % (self.prefix, msg)
        ret = self.dispatch(data, event)

    def listen_once(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.addOnetimeObserver(event, cb)

    def remove_listener(self, msg, cb):
        event = "%s/%s" % (self.prefix, msg)
        self.removeObserver(event, cb)
