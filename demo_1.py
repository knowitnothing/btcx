from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

import sys
import numpy
from decimal import Decimal
from twisted.internet import reactor, task
from matplotlib.ticker import ScalarFormatter

# Own modules
from btcx import btce, mtgox, bitstamp, cfgmanager
from simpleplot import SimplePlot
import systray
print("woof!")


# Note: Avg is actually VWAP
WINDOW_TITLE = u'MtGox - High: $ %(high)s - Low: $ %(low)s - Avg: $ %(avg)s'

class Demo(QG.QMainWindow):

    def __init__(self, currency='USD'):
        QG.QMainWindow.__init__(self)

        # Show last trade price from MtGox in the systray.
        self.stray = systray.TextSysTray(self, "-")
        self.stray.show()

        yl = u'%s/BTC' % currency
        ax1_kw = {'lw': 2, 'ls': 'steps'}
        self.plot = SimplePlot(self, lineconfig=( # A plot with two axes
            # The first axis displays trades from the exchanges
            ('trade', {'title': u'Trades', 'ylabel': yl,
                    'numpoints': 150, # Last 150 trades
                    'legend': {'loc': 'upper center',
                               'bbox_to_anchor': (0.5, -0.05), 'ncol': 3},
                    'grid': True,
                    'ylim_extra': 0.3,
                    # Blue, red and green lines, respectively.
                    'line': (('mtgox', u'MtGox', 'b', ax1_kw),
                             ('btce', u'BTC-e', 'r', ax1_kw),
                             ('bitstamp', u'Bitstamp', 'g', ax1_kw))}
                ),
            # The second axis displays the lag reported by MtGox
            ('lag', {'title': u'', 'ylabel': u'MtGox Lag(s)', 'numpoints': 60,
                    'ylim_extra': 0.1,
                    # A black line, one pixel width, stepwise.
                    'line': (('mtgox', u'', 'k', {'lw': 1, 'ls': 'steps'}), )}
                ),
            ('vol', {'title': u'', 'ylabel': u'MtGox BTC Vol.',
                    'numpoints': 60, 'ylim_extra': 10,
                    'line': (('mtgox', u'', 'k', {}), )})
            ),
            # Bounding box configuration for the two axes
            ax_bbox=(([0.1, 0.38, 0.88, 0.55], # trade
                      [0.1, 0.03, 0.38, 0.2], # lag
                      [0.6, 0.03, 0.38, 0.2]  # vol
                      )),
            # Display a navigation bar with tools
            navbar=True,
            # Refresh the plots (if needed) each 300 ms
            timeout=300)

        # Disable scientific notation.
        self.plot.ax['vol'].yaxis.set_major_formatter(ScalarFormatter(False))

        # Keep the timestamp of the most recent trade in BTC-e and Bitstamp.
        self.last_btce_ts = float('-inf')
        self.last_bitstamp_ts = float('-inf')

        self.setup_gui()


    def setup_gui(self):
        widget = QG.QWidget()

        quit_btn = QG.QPushButton(u'Quit')
        layout = QG.QVBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(quit_btn)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        quit_btn.pressed.connect(self.close)


    def mtgox_trade(self, (tid, timestamp, ttype, price, amount, coin)):
        if tid is None:
            # End of pre-fetch.
            return
        elif price is None:
            # Trade in a different currency or not primary.
            return
        print('mtgox trade:', ttype, timestamp, float(price), amount)
        self.plot.append_value(float(price), 'trade', 'mtgox')

        # Show price in systray.
        last_s_price = str(price)
        if last_s_price.find('.') > 0:
            last_s_price = last_s_price[:last_s_price.find('.') + 2]
        self.stray.update_text(last_s_price, chunk_size=3)

    def btce_trade(self, data):
        for item in data:
            ttype = item['trade_type']
            timestamp = item['date']
            price = item['price']
            amount = item['amount']
            if timestamp <= self.last_btce_ts:
                break
            print('btce trade:', ttype, timestamp, price, amount)
            self.plot.append_value(price, 'trade', 'btce', False)
        self.last_btce_ts = data[0]['date']
        self.plot.update_line('trade', 'btce')

    def bitstamp_trade(self, data):
        for item in data:
            #tid = item['tid']
            timestamp = int(item['date'])
            price = Decimal(item['price'])
            amount = Decimal(item['amount'])
            if timestamp <= self.last_bitstamp_ts:
                break
            print('bitstamp trade:', timestamp, price, amount)
            self.plot.append_value(float(price), 'trade', 'bitstamp', False)
        self.last_bitstamp_ts = int(data[0]['date'])
        self.plot.update_line('trade', 'bitstamp')


    def mtgox_lag(self, lag):
        self.plot.append_value(float(lag), 'lag', 'mtgox')

    def mtgox_vol(self, (ask, bid, vwap, low, high, vol, coin)):
        self.plot.append_value(float(vol), 'vol', 'mtgox')
        # Show ticker data in window's title.
        self.setWindowTitle(WINDOW_TITLE % {'high':high, 'low':low, 'avg':vwap})


def main(key, secret):
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    plot = Demo(currency)

    mtgox_client = mtgox.create_client(key, secret, currency)
    # After connecting, subscribe to the channels 'lag' and 'trades.
    mtgox_client.evt.listen('connected', lambda _:
            (mtgox_client.subscribe_type('lag'),
             mtgox_client.subscribe_type('ticker'),
             mtgox_client.subscribe_type('trades')))
    # The first time a connection is established, load some of the
    # last trades (it should be trades from 2 hours ago, but MtGox
    # does not actually send all of it).
    mtgox_client.evt.listen_once('connected', lambda _:
             mtgox_client.load_trades_since(hours_ago=2))
    mtgox_client.evt.listen('trade_fetch', plot.mtgox_trade)
    mtgox_client.evt.listen('trade', plot.mtgox_trade)
    mtgox_client.evt.listen('lag', plot.mtgox_lag)
    mtgox_client.evt.listen('ticker', plot.mtgox_vol)
    mtgox.start(mtgox_client)

    btce_client = btce.create_client('', '') # No key/secret.
    btce_client.evt.listen('trades', plot.btce_trade)
    # Get the last trades each x seconds.
    btce_trade_pool = task.LoopingCall(lambda:
            btce_client.trades(currency=currency))
    btce_trade_pool.start(10) # x seconds

    bitstamp_cli = bitstamp.create_client()
    bitstamp_cli.evt.listen('trades', plot.bitstamp_trade)
    bitstamp_cli.transactions(timedelta=60*60) # Trades from last hour.
    # Get the last trades each x seconds.
    bitstamp_trade_pool = task.LoopingCall(lambda:
            bitstamp_cli.transactions(timedelta=60) if
                plot.last_bitstamp_ts > 0 else None)
    bitstamp_trade_pool.start(10) # x seconds.

    print('Showing GUI..')
    plot.show()
    plot.raise_()

    def finish():
        print("Finishing..")
        if mtgox_client.connected:
            mtgox_client.sendClose()
        if btce_trade_pool.running:
            btce_trade_pool.stop()
        if reactor.running:
            reactor.stop()
            print("Reactor stopped")

    reactor.runReturn()
    app.lastWindowClosed.connect(finish)
    app.exec_()


if __name__ == "__main__":
    # XXX
    # Authentication is no longer needed given the current
    # functionality.
    #print('\nCreate or/and load a key/secret pair for MtGox to use '
    #      'in this demo.\n')
    #key, secret = cfgmanager.obtain_key_secret(sys.argv[1:])
    #if key is None:
    #    print("Warning: Continuing without a key/secret pair.")
    #    key = secret = ''
    #main(key, secret)
    main('', '')
