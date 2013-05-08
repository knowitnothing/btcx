#!/bin/sh

# Dependencies:
#  * scrypt: used for storing API key secret or any other sensitive data
#  * autobahn: Websocket for Twisted, used for MtGox
#  * treq: simple way for making HTTP requests through Twisted

DEST_DIR="dep"
EASY_INSTALL="easy_install-2.7"

for dep in scrypt autobahn treq
do
  PYTHONPATH=${DEST_DIR} ${EASY_INSTALL} --install-dir=${DEST_DIR} ${dep}
done
