#!/bin/sh

# Dependencies:
#  * scrypt: used for storing API key secret or any other sensitive data
#  * autobahn: Websocket for Twisted, used for MtGox
#  * treq: simple way for making HTTP requests through Twisted
#
#  Not used in the master branch for now:
#  * pandas: efficient handling of time series and co.
#  * tables: used for wrapping HDF5 storage (aka PyTables)
#    * numexpr: PyTables dependency
#    + HDF5 library: PyTables depends on it, build manually if needed

DEST_DIR="dep"
EASY_INSTALL="easy_install-2.7"

# For PyTables, adjust as needed.
HDF5_DIR="/opt/local"

for dep in scrypt autobahn treq #pandas numexpr tables
do
  HDF5_DIR=${HDF5_DIR} PYTHONPATH=${DEST_DIR} ${EASY_INSTALL} \
	  --install-dir=${DEST_DIR} ${dep}
done
