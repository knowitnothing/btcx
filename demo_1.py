from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

from decimal import Decimal
from twisted.internet import reactor, task
from matplotlib.ticker import ScalarFormatter

# Own modules
import systray
from btcx import btce, mtgox, bitstamp, btcchina, common
from simpleplot import SimplePlot
print("woof!")


WINDOW_TITLE = u'MtGox - High: $ %(high)s - Low: $ %(low)s - VWAP: $ %(vwap)s'

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
                               'bbox_to_anchor': (0.5, -0.05), 'ncol': 4},
                    'grid': True,
                    'ylim_extra': 0.3,
                    # Blue, red, green and black lines, respectively.
                    'line': (('btcchina', u'BTCChina', 'k', ax1_kw),
                             ('bitstamp', u'Bitstamp', 'g', ax1_kw),
                             ('btce', u'BTC-e', 'r', ax1_kw),
                             ('mtgox', u'MtGox', 'b', ax1_kw))}
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

        # Keep the timestamp of the most recent trade in the exchances.
        self.last_btce = [float('-inf'), float('-inf')]
        self.last_bitstamp = [float('-inf'), float('-inf')]
        self.last_btcchina = [float('-inf'), float('-inf')]

        self.setup_gui()

    def closeEvent(self, event):
        reactor.stop()
        event.accept()
        print("Now we wait..")

    def setup_gui(self):
        widget = QG.QWidget()

        quit_btn = QG.QPushButton(u'Quit')
        layout = QG.QVBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(quit_btn)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        quit_btn.pressed.connect(self.close)


    def mtgox_trade(self, trade):#(tid, timestamp, ttype, price, amount, coin)):
        if trade.id is None:
            # End of pre-fetch.
            return
        elif trade.price is None:
            # Trade in a different currency or not primary.
            return
        print('mtgox trade:', trade)
        self.plot.append_value(float(trade.price), 'trade', 'mtgox')

        # Show price in systray.
        last_s_price = str(trade.price)
        if last_s_price.find('.') > 0:
            last_s_price = last_s_price[:last_s_price.find('.') + 2]
        self.stray.update_text(last_s_price, chunk_size=3)

    def btce_trade(self, trade):
        if trade is common.TRADE_EMPTY:
            # Fetch finished.
            if self.last_btce[0] != self.last_btce[1]:
                # At least one new trade from last fetch.
                self.last_btce[0] = self.last_btce[1]
                self.plot.update_line('trade', 'btce')
            return

        if trade.id > self.last_btce[1]:
            print('btce trade:', trade)
            self.plot.append_value(float(trade.price), 'trade', 'btce', False)
            self.last_btce[1] = trade.id

    def bitstamp_trade(self, trade):
        if trade is common.TRADE_EMPTY:
            # Fetch finished
            if self.last_bitstamp[0] != self.last_bitstamp[1]:
                # At least one new trade from last fetch.
                self.last_bitstamp[0] = self.last_bitstamp[1]
                self.plot.update_line('trade', 'bitstamp')
            return

        if trade.id > self.last_bitstamp[1]:
            print('bitstamp trade:', trade)
            self.plot.append_value(float(trade.price),'trade','bitstamp',False)
            self.last_bitstamp[1] = trade.id

    _cnyusd = Decimal('0.1625') # XXX Retrieve the updated value.
    def btcchina_trade(self, trade):
        if trade is common.TRADE_EMPTY:
            # Fetch finished
            if self.last_btcchina[0] != self.last_btcchina[1]:
                # At least one new trade from last fetch.
                self.last_btcchina[0] = self.last_btcchina[1]
                self.plot.update_line('trade', 'btcchina')
            return

        if trade.id > self.last_btcchina[1]:
            print("btcchina trade:", trade)
            self.plot.append_value(float(trade.price * self._cnyusd),
                    'trade', 'btcchina', False)
            self.last_btcchina[1] = trade.id


    def mtgox_lag(self, lag):
        self.plot.append_value(float(lag), 'lag', 'mtgox')

    def mtgox_vol(self, ticker):
        self.plot.append_value(float(ticker.vol), 'vol', 'mtgox')
        # Show ticker data in window's title.
        self.setWindowTitle(WINDOW_TITLE % {
            'high': ticker.high, 'low': ticker.low, 'vwap': ticker.vwap})


def main(key, secret):
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    plot = Demo(currency)

    mtgox_client = mtgox.create_client(key, secret, currency)
    # After connecting, subscribe to the channels 'lag' and 'trades.
    for ch in ('lag', 'ticker', 'trades'):
        mtgox_client.call('subscribe_type', ch)
    # The first time a connection is established, load some of the
    # last trades (it should be trades from 2 hours ago, but MtGox
    # does not actually send all of it).
    mtgox_client.call('load_trades_since', hours_ago=2, once=True)
    mtgox_client.evt.listen('trade_fetch', plot.mtgox_trade)
    # Listen for events in the registered channels.
    mtgox_client.evt.listen('trade', plot.mtgox_trade)
    mtgox_client.evt.listen('lag', plot.mtgox_lag)
    mtgox_client.evt.listen('ticker', plot.mtgox_vol)

    btce_client = btce.create_client()
    btce_client.evt.listen('trade_fetch', plot.btce_trade)
    # Get the last trades each x seconds.
    btce_pool = task.LoopingCall(btce_client.trades, p2=currency)
    btce_pool.start(10) # x seconds

    btcchina_cli = btcchina.create_client()
    btcchina_cli.evt.listen('trade_fetch', plot.btcchina_trade)
    btcchina_pool = task.LoopingCall(btcchina_cli.trades)
    btcchina_pool.start(10)

    bitstamp_cli = bitstamp.create_client()
    bitstamp_cli.evt.listen('trade_fetch', plot.bitstamp_trade)
    bitstamp_cli.transactions(timedelta=60*60) # Trades from last hour.
    # Get the last trades each x seconds.
    bitstamp_pool = task.LoopingCall(bitstamp_cli.transactions, timedelta=60)
    bitstamp_pool.start(10, now=False) # x seconds.


    print('Showing GUI..')
    plot.show()
    plot.raise_()

    reactor.addSystemEventTrigger('after', 'shutdown', app.quit)
    reactor.run()


if __name__ == "__main__":
    main('', '')
