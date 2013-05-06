class CallOnEvent(object):
    def __init__(self, client):
        self.client = client

    def call(self, func, *args, **kwargs):
        event = kwargs.get('event', 'connected') # Call on this event.
        client = kwargs.get('client', True) # Call through the client.
        once = kwargs.get('once', False) # Call only once (listen once).

        call_func = self._call if client else self._callback
        listen = 'listen_once' if once else 'listen'
        listen_func = getattr(self.client.evt, listen)

        listen_func(event, lambda ignored: call_func(event, func, args))

    def _call(self, event, func, args):
        print("Client-Calling %s%s due to event %s" % (func, args, event))
        getattr(self.client, func)(*args)

    def _callback(self, event, func, args):
        print("Calling %s%s due to event %s" % (func, args, event))
        func(*args)
