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
    def __init__(self, parent=None, axconf=None, timeout=2000):
        QG.QWidget.__init__(self, parent)

        self._depth = sqlite3.connect(':memory:')
        self._depth.execute("""CREATE TABLE
                bid (price INTEGER PRIMARY KEY, amount REAL)""")
        self._depth.execute("""CREATE TABLE
                ask (price INTEGER PRIMARY KEY, amount REAL)""")

        self.fig = Figure(figsize=(8, 3))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)

        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        if axconf:
            self.ax = self.fig.add_axes(axconf)
        else:
            self.ax = self.fig.add_subplot(111)
        self.ax.xaxis.set_major_locator(MaxNLocator(9))

        self.bid = self.ax.plot([], [], 'g', lw=3)[0]
        self.ask = self.ax.plot([], [], 'r', lw=3)[0]

        self._bidfill = None
        self._askfill = None

        # Display only values +/- from price_threshold
        self.price_threshold = 7
        # Multiply price by price_factor and store as integer.
        self.price_factor = 100

        # Number of updates pending.
        self.need_replot = 0
        # Replot before timeout only if there are more than x
        # updates pending.
        self.replot_after = 30

        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.replot)
        self.timer.start(timeout) # x ms.

        self._last_old = 'bid'
        self.timer_clean = QC.QTimer()
        self.timer_clean.timeout.connect(self._clean_db)
        # Remove unused/old data from in-memory database each n seconds.
        self.timer_clean.start(15 * 1000)


    def _clean_db(self):
        print("Cleaning database..")

        # Clean bids.
        dnum = self._depth.execute("""
            DELETE FROM bid WHERE price IN (
                SELECT a.price FROM bid a
                WHERE ((SELECT b.price FROM bid b ORDER BY b.price DESC
                        LIMIT 1) - a.price) > ?)""", (
                            self.price_factor * self.price_threshold,
                            )).rowcount
        print("  Bids removed:", dnum)

        # Clean asks.
        dnum = self._depth.execute("""
            DELETE FROM ask WHERE price IN (
                SELECT a.price FROM ask a
                WHERE (a.price - (SELECT b.price FROM ask b ORDER BY b.price
                        ASC LIMIT 1)) > ?)""", (
                            self.price_factor * self.price_threshold,
                            )).rowcount
        print("  Asks removed:", dnum)

        # Check if the curves are crossing and remove that data.
        # This might happen after a reconnect where we have outdated
        # information. This also happens when the initial is old.
        #
        # Eventually (after running for some time) these queries
        # should stop removing rows.
        if self._last_old == 'bid':
            # Remove possibly old asks now.
            self._last_old = 'ask'
            comp, order = '<', 'DESC'
            t1, t2 = 'ask', 'bid'
        else:
            # Remove possibly old bids now.
            self._last_old = 'bid'
            comp, order = '>', 'ASC'
            t1, t2 = 'bid', 'ask'

        opts = {'t1': t1, 't2': t2, 'comp': comp, 'order': order}
        dnum = self._depth.execute("""
            DELETE FROM [%(t1)s] WHERE price IN (
                SELECT b.price FROM [%(t1)s] b WHERE b.price %(comp)s (
                    SELECT a.price FROM [%(t2)s] a ORDER BY a.price %(order)s
                    LIMIT 1))""" % opts).rowcount
        print("  Old %ss removed:" % self._last_old, dnum)
        if dnum:
            self.need_replot += 1
            self.replot()

        self._depth.execute("VACUUM")


    def replot(self):
        # If you are calling this function, make sure you meant to do it.

        if not self.need_replot:
            return
        self.need_replot = 0

        now = time.time()
        # Grab up-to-date bid data.
        result = self._depth.execute("""
                SELECT a.price, a.amount, SUM(c.amount)
                FROM bid a LEFT JOIN bid c ON (c.price >= a.price)
                WHERE ((SELECT b.price FROM bid b ORDER BY b.price
                        DESC LIMIT 1) - a.price) <= ?
                GROUP BY a.price, a.amount ORDER BY a.price DESC""",
                (self.price_factor * self.price_threshold, ))
        data_bid = numpy.array(result.fetchall())

        # Grab up-to-date ask data.
        result = self._depth.execute("""
                SELECT a.price, a.amount, SUM(c.amount)
                FROM ask a LEFT JOIN ask c ON (c.price <= a.price)
                WHERE (a.price - (SELECT b.price
                        FROM ask b ORDER BY b.price ASC LIMIT 1)) <= ?
                GROUP BY a.price, a.amount ORDER BY a.price ASC""",
                (self.price_factor * self.price_threshold, ))
        data_ask = numpy.array(result.fetchall())
        print("took", time.time() - now)

        if not len(data_bid) or not len(data_ask):
            return

        x_bid_data = data_bid[:,0].astype(numpy.float32) / self.price_factor
        y_bid_data = data_bid[:,2]

        x_ask_data = data_ask[:,0].astype(numpy.float32) / self.price_factor
        y_ask_data = data_ask[:,2]

        # Update lines.
        self.bid.set_data(x_bid_data[::-1], y_bid_data[::-1])
        self.ask.set_data(x_ask_data, y_ask_data)

        # Adjust axes.
        ax = self.ax
        ax.set_xlim(x_bid_data[-1], x_ask_data[-1])
        y_max = max(y_bid_data[-1], y_ask_data[-1])
        y_min = -(y_max * 0.01) # This is good for linear scale.
        #y_min = min(y_bid_data[0], y_ask_data[0]) # Better for log scale.
        ax.set_ylim(y_min, y_max)

        # Fill below the curves.
        if self._bidfill: self._bidfill.remove()
        if self._askfill: self._askfill.remove()
        self._bidfill = ax.fill_between(x_bid_data, y_min, y_bid_data,
                color='green', alpha=0.5)
        self._askfill = ax.fill_between(x_ask_data, y_min, y_ask_data,
                color='red', alpha=0.5)


        # Redraw.
        self.canvas.draw_idle()


    def new_data(self, typ, price, amount_now):
        price = int(price * self.price_factor)
        if str(amount_now) != '0':
            self._depth.execute("INSERT OR REPLACE INTO %s VALUES (?, ?)" % typ,
                    (price, float(amount_now)))
        else:
            self._depth.execute("DELETE FROM %s WHERE price = ?" % typ,
                    (price, ))

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

