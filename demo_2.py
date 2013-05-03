from __future__ import print_function

import sqlite3
from twisted.internet import reactor

# Own modules
from btcx import mtgox
import mtgox_tradehist

def main():
    """
    Download the entire history of trades from MtGox.
    If there is partial download, the download will resume from the last
    stored transaction id.
    """
    mtgox_client, tradefetch, db = mtgox_tradehist.setup_client(
            verbose=1, max_hours_ago=None)
    mtgox_client.evt.listen('done', lambda _: reactor.stop())
    mtgox.start(mtgox_client)
    reactor.run()

if __name__ == "__main__":
    main()
