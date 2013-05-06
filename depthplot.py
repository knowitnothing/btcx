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

        self.price_threshold = 10

        self.need_replot = 0
        self.replot_after = 20
        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.replot)
        self.timer.start(timeout) # x ms.

        self.timer_clean = QC.QTimer()
        self.timer_clean.timeout.connect(self._clean_db)
        # Remove unused data from in-memory database each n seconds.
        self.timer_clean.start(30 * 1000)


    def _clean_db(self):
        print("Cleaning database..")

        # Clean bids.
        self._depth.execute("""
            DELETE FROM bid WHERE price IN (
                SELECT a.price FROM bid a
                WHERE ((SELECT b.price FROM bid b ORDER BY b.price DESC
                        LIMIT 1) - a.price) > ?)""", (self.price_threshold, ))

        # Clean asks.
        self._depth.execute("""
            DELETE FROM ask WHERE price IN (
                SELECT a.price FROM ask a
                WHERE (a.price - (SELECT b.price FROM ask b ORDER BY b.price
                        ASC LIMIT 1)) > ?)""", (self.price_threshold, ))


    def replot(self):
        # If you are calling this function, make sure you meant to do it.

        if not self.need_replot:
            return
        self.need_replot = 0

        now = time.time()
        # Grab up-to-date bid data.
        result = self._depth.execute("""
                SELECT a.price, CAST(sum(c.amount) AS REAL)
                FROM bid a LEFT JOIN bid c ON (c.price >= a.price)
                WHERE ((SELECT b.price FROM bid b ORDER BY b.price
                        DESC LIMIT 1) - a.price) <= ?
                GROUP BY a.price ORDER BY a.price DESC LIMIT ?""",
                (self.price_threshold, self.nbin))
        data_bid = numpy.array(result.fetchall())

        # Grab up-to-date ask data.
        result = self._depth.execute("""
                SELECT a.price, CAST(SUM(c.amount) AS REAL)
                FROM ask a LEFT JOIN ask c ON (c.price <= a.price)
                WHERE (a.price - (SELECT b.price
                        FROM ask b ORDER BY b.price ASC LIMIT 1)) <= ?
                GROUP BY a.price ORDER BY a.price ASC LIMIT ?""",
                (self.price_threshold, self.nbin))
        data_ask = numpy.array(result.fetchall())

        if not len(data_bid) or not len(data_ask):
            return

        x_bid_data = data_bid[:,0]
        y_bid_data = data_bid[:,1]

        x_ask_data = data_ask[:,0]
        y_ask_data = data_ask[:,1]

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

