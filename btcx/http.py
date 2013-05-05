from __future__ import print_function

import treq
from twisted.web.http_headers import Headers

from common import USER_AGENT


class HTTPAPI(object):

    def __init__(self, host):
        self.host = host

    def call(self, urlpart, cb, **kwargs):
        headers = Headers({"User-Agent": [USER_AGENT]})
        d = treq.get('%s/%s' % (self.host, urlpart),
                params=kwargs, headers=headers)
        d.addCallback(lambda response: self.decode_or_error(
            response, cb, urlpart))

    def decode_or_error(self, response, cb, *args):
        d = treq.json_content(response)
        d.addCallback(cb, *args)
        errcb = lambda err, *args: print("Error when calling %s: %s" % (
            ' '.join(args), err.getErrorMessage()))
        d.addErrback(errcb, *args)
