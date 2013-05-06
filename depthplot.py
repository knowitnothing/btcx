import time
import numpy
import sqlite3
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC
from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


class PlotDepth(QG.QWidget):
    def __init__(self, parent=None, timeout=1500):
        QG.QWidget.__init__(self, parent)

        self._depth = sqlite3.connect(':memory:')
        self._depth.execute("""CREATE TABLE
                bid (price REAL PRIMARY KEY, amount TEXT)""")
        self._depth.execute("""CREATE TABLE
                ask (price REAL PRIMARY KEY, amount TEXT)""")

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

        # Limit visual display to n points.
        self.nbin = 100

        self.need_replot = 0
        self.replot_after = 20
        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.replot)
        self.timer.start(timeout) # x ms.

        self.timer_clean = QC.QTimer()
        self.timer_clean.timeout.connect(self._clean_db)
        # Remove unused data from in-memory database each n seconds.
        self.timer_clean.start(120 * 1000)


    def _clean_db(self):
        print("Cleaning database..")

        # Clean bids.
        nrow = self._depth.execute("SELECT COUNT(*) FROM bid").fetchone()[0]
        print("  ", nrow, "bid")
        if nrow > self.nbin:
            print("  Rows to remove from bids: %d" % (nrow - self.nbin))
            self._depth.execute("""
                DELETE FROM bid WHERE price IN (
                    SELECT price FROM bid ORDER BY price ASC
                    LIMIT ?)""", (nrow - self.nbin, ))
        else:
            print("  'bids' is clean")

        # Clean asks.
        nrow = self._depth.execute("SELECT COUNT(*) FROM ask").fetchone()[0]
        print("  ", nrow, "ask")
        if nrow > self.nbin:
            print("  Rows to remove from asks: %d" % (nrow - self.nbin))
            self._depth.execute("""
                DELETE FROM ask WHERE price IN (
                        SELECT price FROM ask ORDER BY price DESC
                        LIMIT ?)""", (nrow - self.nbin, ))
        else:
            print("  'asks' is clean")


    def replot(self, threshold=10):
        # If you are calling this function, make sure you meant to do it.

        if not self.need_replot:
            return
        self.need_replot = 0

        now = time.time()
        # Grab up-to-date bid data.
        result = self._depth.execute("""
                SELECT a.price, CAST(sum(b.amount) AS REAL)
                FROM bid a LEFT JOIN bid b ON (b.price >= a.price)
                GROUP BY a.price ORDER BY a.price DESC LIMIT ?""",
                (self.nbin, ))
        data_bid = numpy.array(result.fetchall())

        # Grab up-to-date ask data.
        result = self._depth.execute("""
                SELECT a.price, CAST(sum(b.amount) AS REAL)
                FROM ask a LEFT JOIN ask b on (b.price <= a.price)
                GROUP BY a.price ORDER BY a.price ASC LIMIT ?""",
                (self.nbin, ))
        data_ask = numpy.array(result.fetchall())

        if not len(data_bid) or not len(data_ask):
            return

        # Limit data to be displayed so "weird" things like
        # bid at 10 dollars when the current price is 110 dollars
        # is not displayed.
        if len(data_ask) < self.nbin/10 or len(data_bid) < self.nbin/10:
            # Except if there are too few data points.
            threshold = float('inf')
        x_bid = (data_bid[:,0][0] - data_bid[:,0]) < threshold
        x_ask = (data_ask[:,0] - data_ask[:,0][0]) < threshold

        x_bid_data = data_bid[:,0][x_bid]
        y_bid_data = data_bid[:,1][x_bid]

        x_ask_data = data_ask[:,0][x_ask]
        y_ask_data = data_ask[:,1][x_ask]

        # Update lines.
        self.bid.set_data(x_bid_data[::-1], y_bid_data[::-1])
        self.ask.set_data(x_ask_data, y_ask_data)

        print("took", time.time() - now)

        # Adjust axes.
        ax = self.ax
        ax.set_xlim(x_bid_data[-1], x_ask_data[-1])
        y_max = max(y_bid_data[-1], y_ask_data[-1])
        ##y_min = -(y_max * 0.01)
        y_min = min(y_bid_data[0], y_ask_data[0])
        ax.set_ylim(y_min, y_max)

        # Redraw.
        self.canvas.draw_idle()


    def new_data(self, typ, price, amount_now):
        if str(amount_now) != '0':
            self._depth.execute("INSERT OR REPLACE INTO %s VALUES (?, ?)" % typ,
                    (float(price), float(amount_now)))
        else:
            self._depth.execute("DELETE FROM %s WHERE price = ?" % typ,
                    (float(price), ))

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

