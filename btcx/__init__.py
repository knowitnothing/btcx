import sys
from twisted.python import log
from twisted.internet import reactor

import btce
import mtgox
import bitstamp
import btcchina
import cfgmanager
from version import __version__, VERSION

def enable_debug(fobj=sys.stdout):
    log.startLogging(fobj)

def run(): reactor.run()
def stop(): reactor.stop()
