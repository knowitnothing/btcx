import sys
from twisted.python import log

import btce
import mtgox
import bitstamp
import cfgmanager
from version import __version__, VERSION

def enable_debug(fobj=sys.stdout):
    log.startLogging(fobj)
