from __future__ import print_function

import treq
from twisted.web.http_headers import Headers

from common import USER_AGENT


class HTTPAPI(object):

    def __init__(self, host):
        self.host = host

    def http_call(self, urlpart, cb, **kwargs):
        headers = Headers({"User-Agent": [USER_AGENT]})
        d = treq.get('%s/%s' % (self.host, urlpart),
                params=kwargs, headers=headers)
        d.addCallback(lambda response: self.decode_or_error(
            response, cb, urlpart, **kwargs))

    def decode_or_error(self, response, cb, *args, **kwargs):
        d = treq.json_content(response)
        d.addCallback(cb, *args, **kwargs)
        errcb = lambda err, *args, **kwargs: print(
                "Error when calling %s %s: %s" % (' '.join(map(str, args)),
                    kwargs, err.getBriefTraceback()))
        d.addErrback(errcb, *args, **kwargs)
