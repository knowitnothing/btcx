import os
from twisted.words.xish.utility import EventDispatcher

USER_AGENT = 'btcx-bot'

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
        ret = self.dispatch(data, event)

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
