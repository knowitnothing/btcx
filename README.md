btcx
====

Handling of Multiple Bitcoin (and other cryptocurrencies) Exchanges


Dependencies
============

+ Every API secret is encrypted through scrypt, and then stored.

+ This project relies on Twisted for proper network communication.
The Autobahn library provides a WebSocket client for using the
MtGox Streaming API. For other API calls through HTTP(S) (this includes
fetching some public data from MtGox, and also the entire BTC-e and
Bitstamp APIs), the treq package is used in order to keep a clean
interface to the requests.

+ Qt and Matplotlib are used for the GUI/plotting in the current demos.


Demo
====

![demo1](screenshot/demo_1_up2.png?raw=True)

![demo4](screenshot/demo_4.png?raw=True)


Bitcoin Donations
=================

1BTCXAPHWyFheYWzM3mbWztEaX8GqCXiH3
