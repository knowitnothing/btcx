btcx
====

Handling of Multiple Bitcoin (and other cryptocurrencies) Exchanges


Can I run it ?
==============

The minimum  expected version  for Python is  2.6, but  `deps.sh` uses
Python 2.7 by default (adjust it if  needed). If you are not sure that
you have  the dependencies  installed, run  `./deps.sh` and  the basic
packages will be installed in the `dep/` directory.

After running `./deps.sh`, do (the equivalent of) the following:

	$ PYTHONPATH=dep python2.7

	>>> import btcx
	>>>

If  no messages  are shown,  then  you can  run it.  Next, two  simple
examples are presented in a wordy fashion.


Two very simple examples
------------------------

Our first example will query  certain currencies through the Streaming
API from MtGox. This involves importing `btcx`

	import btcx

creating a MtGox client

	client = btcx.mtgox.create_client()

telling the client  to listen for events  "currency\_info", which will
call into  a function  whenever they  are emitted.  To do  this, first
create a function to handle such event and then define the listener

	def got_currency(data):
		print (u"{name:17}: {symbol:4}   "
		   	   u"Decimals : {decimals}   "
		   	   u"Virtual : {virtual}".format(**data))

	client.evt.listen('currency_info', got_currency)

In this example we will query  the symbols 'EUR', 'BTC', 'JPY', 'AUD',
and 'LTC'

	currencies = ['EUR', 'BTC', 'JPY', 'AUD', 'LTC']

for each one of them, we need to call the "currency\_info" method that
becomes available after the client  connects. This is handled by using
the  `call` method  from  the client,  which by  default  waits for  a
"connected" event and then makes the requested call.

	for currency in currencies:
    		client.call('currency_info', currency, once=True)
        	print "Will ask for %s" % currency

Finally we start the event loop and things actually start happening

	btcx.run()

Note that  the example is very  short, do not let  the step-wise build
fool you.  You will observe  that every call returns immediately, this
is mainly due to how Twisted  works. The example will run forever, you
can finish it by pressing Ctrl+C.

The second  example requires  authentication in  order to  request the
pending  orders  as   well  live  updates  as  the   user  orders  are
modified. If  this is  the first time  running the  following example,
pass a "-n"  argument and the function  `obtain_key_secret` will first
ask for a new API key/secret pair.  Your secret will go through scrypt
before being  stored, so a  password is required for  later decrypting
it. The password is not  stored anywhere and forgetting it practically
means the API secret is lost (i.e., not recoverable).

	import sys

	import btcx

	def show_userorder(order):
		print order

	key, secret = btcx.cfgmanager.obtain_key_secret(sys.argv[1:])
	client = btcx.mtgox.create_client(key, secret)
	client.evt.listen('userorder', show_userorder)
	client.call('order_list')

	btcx.run()


Dependencies
============

+ Every API secret is encrypted through scrypt, and then stored.

+ This  project relies  on Twisted  for proper  network communication.
The Autobahn library  provides a WebSocket client for  using the MtGox
Streaming  API. For  other API  calls through  HTTP(S) (this  includes
fetching some  public data from MtGox,  and also the entire  BTC-e and
Bitstamp APIs),  the treq  package is  used in order  to keep  a clean
interface to the requests.

+  Qt, Numpy,  and Matplotlib  are used  for the  GUI/plotting in  the
current  demos.    These  dependencies   are  not   installed  through
`deps.sh`.


Demo
====

![demo1](screenshot/demo_1_up2.png?raw=True)

![demo4](screenshot/demo_4.png?raw=True)

![demo7](screenshot/demo_7.png?raw=True)


Bitcoin Donations
=================

1BTCXAPHWyFheYWzM3mbWztEaX8GqCXiH3
