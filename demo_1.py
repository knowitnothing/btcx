from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

import sys
import numpy
import pylab
from twisted.internet import reactor, task

# Own modules
from btcx import btce, mtgox, cfgmanager
print("woof!")

#def inf_i():
#    i = 0
#    while True:
#        yield i
#        i += 1


class Plot(QG.QMainWindow):
    def __init__(self, currency='USD', numpoints=120):
        QG.QMainWindow.__init__(self)

        self.currency = currency

        self.trade_i = self.trade_i_btce = 0
        self.last_btce_ts = float('-inf')
        self.mtgox_ydata = numpy.zeros(numpoints)
        self.btce_ydata = numpy.zeros(numpoints)
        self.xdata = numpy.arange(numpoints)

        lag_n = 60
        self.lag_i = 0
        self.lag_ydata = numpy.zeros(lag_n)
        self.lag_xdata = numpy.arange(lag_n)

        self.create_gui_plot()

        #self._frame = inf_i()

        self.timer = QC.QTimer()
        self.timer.timeout.connect(self._replot)
        self.timer.start(350) # x ms for timeout.

    def closeEvent(self, event):
        # Window asked to closed.
        self.timer.stop()
        event.accept()
        print("closeEvent")


    def create_gui_plot(self):
        widget = QG.QWidget()

        quit_btn = QG.QPushButton(u'Quit')
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(widget)
        self.ax_trade = self.fig.add_axes([0.1, 0.4, 0.8, 0.55])
        self.ax_lag = self.fig.add_axes([0.1, 0.05, 0.8, 0.2])
        self.mpl_bar = NavigationToolbar(self.canvas, widget)
        layout = QG.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.mpl_bar)
        layout.addWidget(quit_btn)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        quit_btn.pressed.connect(self.close)

        # Trade plot
        self.ax_trade.grid()
        self.ax_trade.set_title(u'Trades')
        self.ax_trade.set_ylabel(u'%s/BTC' % self.currency)
        self.line_trade = [
                self.ax_trade.plot([],[],'b',lw=2,ls='steps',label=u'MtGox')[0],
                self.ax_trade.plot([],[],'r',lw=2,ls='steps',label=u'BTC-e')[0]
                ]

        self.ylim = [float('inf'), float('-inf')]
        pylab.setp(self.ax_trade.get_xticklabels(), visible=False)
        self.ax_trade.set_xlim(0, len(self.xdata) - 1)
        self.ax_trade.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
                ncol=2)

        # Lag plot
        self.line_lag = self.ax_lag.plot([], [], 'k', lw=1, ls='steps')[0]
        self.ax_lag.set_ylabel(u'MtGox Lag (s)')
        self.ax_lag.set_xlim(0, len(self.lag_xdata) - 1)
        pylab.setp(self.ax_lag.get_xticklabels(), visible=False)
        self.ax_lag.set_ylim(0, 1) # We wish :)
        self.lag_ylim = list(self.ax_lag.get_ylim())

    def _update_line_trade(self):
        new_ylim = [float('inf'), float('-inf')]
        for k, (i, ydata) in enumerate(((self.trade_i, self.mtgox_ydata),
                (self.trade_i_btce, self.btce_ydata))):
            if i == len(self.xdata):
                self.line_trade[k].set_data(self.xdata, ydata)
                new_ylim[0] = min(new_ylim[0], ydata.min())
                new_ylim[1] = max(new_ylim[1], ydata.max())
            elif i:
                self.line_trade[k].set_data(self.xdata[:i], ydata[:i])
                new_ylim[0] = min(new_ylim[0], ydata[:i].min())
                new_ylim[1] = max(new_ylim[1], ydata[:i].max())
        new_ylim[0] -= 1
        new_ylim[1] += 1
        self.ax_trade.set_ylim(*new_ylim)

    def _update_line_lag(self):
        i = self.lag_i
        ylim = self.lag_ylim
        if i == len(self.lag_xdata):
            self.line_lag.set_data(self.lag_xdata, self.lag_ydata)
            ylim[0] = self.lag_ydata.min()
            ylim[1] = self.lag_ydata.max()
        else:
            self.line_lag.set_data(self.lag_xdata[:i], self.lag_ydata[:i])
            ylim[0] = self.lag_ydata[:i].min()
            ylim[1] = self.lag_ydata[:i].max()
        ylim[0] -= 0.1
        ylim[1] += 0.1
        self.ax_lag.set_ylim(*ylim)


    def mtgox_trade(self, (ttype, timestamp, price, amount, coin)):
        if ttype is None: # End of pre-fetch.
            return
        print('mtgox trade:', ttype, timestamp, float(price), amount, coin)
        i = self.trade_i
        if i == len(self.mtgox_ydata):
            self.mtgox_ydata = numpy.roll(self.mtgox_ydata, -1)
            i -= 1
        else:
            self.trade_i += 1
        self.mtgox_ydata[i] = float(price)
        self._update_line_trade()

    def _load_btce_trade(self, price):
        i = self.trade_i_btce
        if i == len(self.btce_ydata):
            self.btce_ydata = numpy.roll(self.btce_ydata, -1)
            i -= 1
        else:
            self.trade_i_btce += 1
        self.btce_ydata[i] = price

    def btce_trade(self, data):
        for item in data:
            ttype = item['trade_type']
            timestamp = item['date']
            price = item['price']
            amount = item['amount']
            if timestamp <= self.last_btce_ts:
                break
            self._load_btce_trade(price)
            print('btce trade:', ttype, timestamp, price, amount)
        self.last_btce_ts = data[0]['date']
        self._update_line_trade()

    def mtgox_lag(self, lag):
        i = self.lag_i
        if i == len(self.lag_ydata):
            self.lag_ydata = numpy.roll(self.lag_ydata, -1)
            i -= 1
        else:
            self.lag_i += 1
        self.lag_ydata[i] = float(lag)
        self._update_line_lag()


    def _replot(self):
        #sshot = QG.QPixmap.grabWidget(self)
        #name = 'sshot_%04d.png' % next(self._frame)
        #sshot.save(name)
        #print("Wrote", name)
        self.fig.canvas.draw()


def main(key, secret):
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    plot = Plot(currency)

    mtgox_client = mtgox.create_client(key, secret, currency)
    # After connecting, subscribe to the channels 'lag' and 'trades,
    # and load trades from the last hour.
    mtgox_client.evt.listen('connected', lambda _:
            (mtgox_client.subscribe_type('lag'),
             mtgox_client.subscribe_type('trades'),
             mtgox_client.load_trades_short_history(1)))
    mtgox_client.evt.listen('trade_fetch', plot.mtgox_trade)
    mtgox_client.evt.listen('trade', plot.mtgox_trade)
    mtgox_client.evt.listen('lag', plot.mtgox_lag)
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
