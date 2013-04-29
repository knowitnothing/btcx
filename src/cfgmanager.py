import json
import scrypt
import getpass
import binascii

class ExchangeConfig(object):
    def __init__(self, cfgname='btcx.cfg'):
        self.cfgname = cfgname
        self.cfg = None

    def load_config(self):
        with open(self.cfgname, 'a+b') as f:
            f.seek(0)
            try:
                cfg = json.load(f)
            except ValueError: # Empty file.
                cfg = {} # Empty configuration.
                json.dump(cfg, f)
        self.cfg = cfg

    def load_key_secret(self, exchange, keyname, password):
        if exchange not in self.cfg or keyname not in self.cfg[exchange]:
            return None, None
        enc_secret = self.cfg[exchange][keyname]['secret']
        key = self.cfg[exchange][keyname]['key']

        try:
            secret = scrypt.decrypt(binascii.unhexlify(enc_secret), password)
        except scrypt.error, e:
            return None, None
        else:
            return key, secret

    def list_all_keys(self):
        for exchange in self.cfg:
            for keyname in self.cfg[exchange]:
                yield exchange, keyname

    def add_key_secret(self, exchange, keyname, key, enc_sec):
        """
        Add an API key/encrypted secret pair under a keyname
        for a given exchange. If keyname already exists for the
        exchange, the old pair is replaced.
        """
        if exchange not in self.cfg:
            self.cfg[exchange] = {}
        exc = self.cfg[exchange]
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

def obtain_key_secret(argl, **kwargs):
    cfgman = ExchangeConfig(**kwargs)
    cfgman.load_config()

    if len(argl) == 1 and argl[0] == "-n":
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


if __name__ == "__main__":
    enc = scrypt.encrypt('x', 'hello', maxtime=0.5)
    print repr(enc)
    print scrypt.decrypt(enc, 'hello')
