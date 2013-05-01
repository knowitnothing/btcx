from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

import sys
import numpy
from twisted.internet import reactor, task
from matplotlib.ticker import ScalarFormatter

# Own modules
from btcx import btce, mtgox, cfgmanager
from simpleplot import SimplePlot
print("woof!")


class Demo(QG.QMainWindow):

    def __init__(self, currency='USD'):
        QG.QMainWindow.__init__(self)

        yl = u'%s/BTC' % currency
        ax1_kw = {'lw': 2, 'ls': 'steps'}
        self.plot = SimplePlot(self, lineconfig=( # A plot with two axes
            # The first axis displays trades from MtGox and BTC-e
            ('trade', {'title': u'Trades', 'ylabel': yl,
                    'numpoints': 150, # Last 150 trades
                    'legend': {'loc': 'upper center',
                               'bbox_to_anchor': (0.5, -0.05), 'ncol': 2},
                    'grid': True,
                    'ylim_extra': 1.0,
                    # Blue and red lines, respectively.
                    'line': (('mtgox', u'MtGox', 'b', ax1_kw),
                             ('btce', u'BTC-e', 'r', ax1_kw))}
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
            ax_bbox=(([0.1, 0.4, 0.8, 0.55], # trade
                      [0.1, 0.05, 0.32, 0.2], # lag
                      [0.55, 0.05, 0.35, 0.2]  # vol
                      )),
            # Display a navigation bar with tools
            navbar=True,
            # Refresh the plots (if needed) each 300 ms
            timeout=300)

        self.plot.ax['vol'].yaxis.set_major_formatter(ScalarFormatter(False))

        # Keep the timestamp of the most recent trade in BTC-e.
        self.last_btce_ts = float('-inf')

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

    def mtgox_lag(self, lag):
        self.plot.append_value(float(lag), 'lag', 'mtgox')

    def mtgox_vol(self, (ask, bid, avg, low, high, vol, coin)):
        # Ticker data.
        self.plot.append_value(float(vol), 'vol', 'mtgox')


def main(key, secret):
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    plot = Demo(currency)

    mtgox_client = mtgox.create_client(key, secret, currency)
    # After connecting, subscribe to the channels 'lag' and 'trades.
    mtgox_client.evt.listen('connected', lambda _:
            (mtgox_client.subscribe_type('lag'),
             mtgox_client.subscribe_type('ticker'),
             mtgox_client.subscribe_type('trades')))
    # The first time a connection is established, load trades from the
    # last hour.
    mtgox_client.evt.listen_once('connected', lambda _:
             mtgox_client.load_trades_since(hours_ago=1))
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
    print('\nCreate or/and load a key/secret pair for MtGox to use '
          'in this demo.\n')
    key, secret = cfgmanager.obtain_key_secret(sys.argv[1:])
    if key is None:
        print("Warning: Continuing without a key/secret pair.")
        key = secret = ''
    main(key, secret)
