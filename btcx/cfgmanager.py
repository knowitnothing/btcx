import os
import time
import json
import scrypt
import getpass
import binascii

from version import __version__

class Config(object):
    def __init__(self, cfgname='btcx.cfg'):
        self.cfgname = cfgname
        self.cfg = None
        self.load_config()

    def load_config(self):
        with open(self.cfgname, 'a+b') as f:
            f.seek(0)
            try:
                cfg = json.load(f)
            except ValueError: # Empty file.
                cfg = {'version': __version__,
                       'exchange': {}
                      } # Empty configuration.
                json.dump(cfg, f)
        if 'version' not in cfg:
            raise Exception("Configuration is invalid. Run the 'update' "
                            "function to adjust it.")
        self.cfg = cfg

    def load_key_secret(self, exchange, keyname, password):
        exchange = self.cfg['exchange'].get(exchange, None)
        if exchange is None or keyname not in exchange:
            return None, None
        enc_secret = exchange[keyname]['secret']
        key = exchange[keyname]['key']

        try:
            secret = scrypt.decrypt(binascii.unhexlify(enc_secret), password)
        except scrypt.error, e:
            return None, None
        else:
            return key, secret

    def list_all_keys(self):
        exchange = self.cfg['exchange']
        for exc, key in exchange.iteritems():
            for keyname in key:
                yield exc, keyname

    def add_key_secret(self, exchange, keyname, key, enc_sec):
        """
        Add an API key/encrypted secret pair under a keyname
        for a given exchange. If keyname already exists for the
        exchange, the old pair is replaced.
        """
        exchanges = self.cfg['exchange']
        if exchange not in exchanges:
            # Adding a new exchange
            exchanges[exchange] = {}
        exc = exchanges[exchange]
        exc[keyname] = {'key': key, 'secret': enc_sec}
        self.rewrite()

    def rewrite(self):
        if self.cfg is None:
            return
        with open(self.cfgname, 'wb') as f:
            json.dump(self.cfg, f)


def encrypt_data(data, password):
    enc = scrypt.encrypt(data, password, maxtime=0.5)
    return binascii.hexlify(enc)


# Helper functions

def loop_ask(func, msg):
    while True:
        answer = func(msg)
        if not answer:
            continue
        break
    return answer

def obtain_key_secret(argl=None, **kwargs):
    cfgman = Config(**kwargs)

    if argl and len(argl) == 1 and argl[0] == "-n":
        print "Setting up new key/secret pair"
        setup_new_key(cfgman)
        print "New pair stored"

    print "   Available keys   "
    print "Exchange     Keyname"
    print "===================="
    last_exc, last_kname = None, None
    for exchange, keyname in cfgman.list_all_keys():
        last_exc, last_kname = exchange, keyname
        print "%-13s%s" % (exchange, keyname)
    print "====================\n"

    if last_exc is None:
        print "** No keys available. You might want to re-run passing",
        print "the -n option. **"
        return None, None

    exchange = raw_input("Exchange [%s]: " % last_exc) or last_exc
    keyname = raw_input("Keyname [%s]: " % last_kname) or last_kname
    pwd = loop_ask(getpass.getpass, "Secret's password: ")
    print "Decrypting.."
    key, secret = cfgman.load_key_secret(exchange, keyname, pwd)

    if key is None:
        print "Error: data not found (check the password, keyname, exchange)"

    return key, secret

def setup_new_key(cfgman, default_exchange='mtgox', default_kname='none'):
    """
    Setup a new key/pair for a given exchange.
    """
    exchange = raw_input("Exchange [%s]: " % default_exchange)
    keyname = raw_input("Keyname [%s]: " % default_kname)
    api_key = loop_ask(raw_input, "API key: ")
    api_secret = loop_ask(raw_input, "API secret (will be encrypted): ")
    print
    print "Please enter some password to encrypt the API secret using scrypt"
    while True:
        pwd = loop_ask(getpass.getpass, "Password: ")
        pwd_repeat = loop_ask(getpass.getpass, "Confirm password: ")
        if pwd == pwd_repeat:
            break
        print "Error: passwords do not match"

    exchange = exchange or default_exchange
    keyname = keyname or default_kname

    enc_sec = encrypt_data(api_secret, pwd)
    cfgman.add_key_secret(exchange, keyname, api_key, enc_sec)


def update(cfgname='btcx.cfg'):
    """
    This function is meant to update your old configuration file.
    It is deemed old if it doesn't contain the version of this package.

    Note: this function might go away.
    """
    with open(cfgname, 'a+b') as f:
        f.seek(0)
        try:
            cfg = json.load(f)
        except ValueError:
            # Empty file is fine, there is nothing to update.
            return

    if 'version' in cfg and 'exchange' in cfg:
        # Nothing to update.
        return

    newcfg = {'version': __version__}
    if 'exchange' not in cfg:
        # When this configuration file was saved, each exchange
        # was a key in cfg. Now it exchange is a key in cfg['exchange']
        newcfg['exchange'] = {}
        for key, val in cfg.iteritems():
            newcfg['exchange'][key] = val
    else:
        newcfg.update(cfg)

    backup = '%s_%s' % (cfgname, time.time())
    os.rename(cfgname, backup)
    with open(cfgname, 'w') as f:
        json.dump(newcfg, f)

    return backup



if __name__ == "__main__":
    enc = scrypt.encrypt('x', 'hello', maxtime=0.5)
    print repr(enc)
    print scrypt.decrypt(enc, 'hello')
