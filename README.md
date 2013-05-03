btcx
====

Handling of Multiple Bitcoin (and other cryptocurrencies) Exchanges


Dependencies
============

+ Every API secret is encrypted through scrypt, and then stored.

+ This project relies on Twisted for proper network communication.
The Autobahn library provides a WebSocket client for using the
MtGox Streaming API. For other exchanges (currently this includes
only BTC-e), the treq package is used in order to keep a clean
interface to HTTP(S) requests.

+ Qt and Matplotlib are used for the GUI/plotting in the current demo.


Demo
====

![screenshot](screenshot/demo_1_up2.png?raw=True)


Bitcoin Donations
=================

1BTCXAPHWyFheYWzM3mbWztEaX8GqCXiH3
