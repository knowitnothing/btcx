import time
import numpy
import pylab
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC
from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


class PlotDepth(QG.QWidget):
    def __init__(self, parent=None, timeout=1000):
        QG.QWidget.__init__(self, parent)

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)

        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.ax = self.fig.add_subplot(111)
        self.ax.xaxis.set_major_locator(MaxNLocator(9))

        self.bid = self.ax.plot([], [], 'g', lw=3)[0]
        self.ask = self.ax.plot([], [], 'r', lw=3)[0]

        self.data = {'bid': {}, # (price, volume)
                     'ask': {}
                    }

        # Limit visual display to n points.
        self.nbin = 100
        self.y_bid = numpy.zeros(self.nbin)
        self.y_ask = numpy.zeros(self.nbin)
        self.x = numpy.zeros(self.nbin * 2)

        self.need_replot = 0
        self.replot_after = 10
        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.replot)
        self.timer.start(timeout) # x ms.


    def replot(self, threshold=10):
        # If you are calling this function, make sure you meant to do it.

        if not self.need_replot:
            return
        self.need_replot = 0

        if not len(self.data['bid']) or not len(self.data['ask']):
            return

        x, y_bid, y_ask = self.x, self.y_bid, self.y_ask

        # Up-to-date bid data.
        z = numpy.array(sorted(self.data['bid'].items())[-self.nbin:])
        bid_len = len(z)
        x[:bid_len] = z[:,0]
        y_bid[:bid_len] = z[:,1]

        # Up-to-date ask data.
        z = numpy.array(sorted(self.data['ask'].items())[:self.nbin])
        ask_len = len(z)
        i = ask_len + bid_len
        x[bid_len:i] = z[:,0]
        y_ask[:ask_len] = z[:,1]

        # Limit data to be displayed so "weird" things like
        # bid at 10 dollars when the current price is 110 dollars
        # is not displayed.
        if ask_len < self.nbin/10 or bid_len < self.nbin/10:
            # Except if there are too few data points.
            threshold = float('inf')
        x_bid = (x[bid_len - 1] - x[:bid_len]) < threshold
        x_ask = (x[bid_len:i] - x[bid_len]) < threshold

        y_bid_cs = y_bid[:bid_len][::-1].cumsum()[::-1]
        y_ask_cs = y_ask[:ask_len].cumsum()

        x = (x[:bid_len][x_bid], x[bid_len:i][x_ask])

        # Update lines.
        self.bid.set_data(x[0], y_bid_cs[x_bid])
        self.ask.set_data(x[1], y_ask_cs[x_ask])

        # Adjust axes.
        ax = self.ax
        ax.set_xlim(x[0][0], x[1][-1])
        y_max = max(y_bid_cs[x_bid][0], y_ask_cs[x_ask][-1])
        #y_min = -(y_max * 0.01)
        y_min = min(y_bid_cs[x_bid][-1], y_ask_cs[x_ask][0])
        ax.set_ylim(y_min, y_max)

        self.canvas.draw_idle()


    def new_data(self, typ, price, amount_now):
        if str(amount_now) != '0':
            # XXX self.data might grow too much, take care.
            self.data[typ][price] = float(amount_now)
        else:
            #print("remove", typ, price)
            if price in self.data[typ]:
                del self.data[typ][price]


        self.need_replot += 1
        if self.need_replot > self.replot_after:
            # More than n changes since the last replot.
            print("Forcing replot", self.need_replot)
            self.replot()


if __name__ == "__main__":
    import sys

    app = QG.QApplication([])

    pd = PlotDepth()

    # If you wish to run this, grab any data formatted in
    # three columns where the last two are numbers.
    for line in open(sys.argv[1]):
        if not line.strip():
            continue
        typ, price, amount = line.split()
        pd.new_data(typ, price, amount)

    pd.show()
    pd.raise_()
    app.exec_()

