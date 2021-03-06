import time
import numpy
import sqlite3
from matplotlib.ticker import MaxNLocator

class PlotDepth(object):
    def __init__(self, figure, canvas, axconf=None):
        self._setup_db()

        self.fig = figure
        self.canvas = canvas

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

        self._last_old = 'bid'

    def _setup_db(self):
        self._depth = sqlite3.connect(':memory:')
        self._depth.execute("""CREATE TABLE
                bid (price INTEGER PRIMARY KEY, amount REAL)""")
        self._depth.execute("""CREATE TABLE
                ask (price INTEGER PRIMARY KEY, amount REAL)""")


    def clean_db(self):
        print("Cleaning database..")

        # Clean bids.
        dnum = self._depth.execute("""
            DELETE FROM bid WHERE price IN (
                SELECT a.price FROM bid a
                WHERE ((SELECT b.price FROM bid b ORDER BY b.price DESC
                        LIMIT 1) - a.price) > ?)""", (
                            self.price_factor * 2*self.price_threshold,
                            )).rowcount
        print("  Bids removed:", dnum)

        # Clean asks.
        dnum = self._depth.execute("""
            DELETE FROM ask WHERE price IN (
                SELECT a.price FROM ask a
                WHERE (a.price - (SELECT b.price FROM ask b ORDER BY b.price
                        ASC LIMIT 1)) > ?)""", (
                            self.price_factor * 2*self.price_threshold,
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
        table = 'ask' if typ.startswith('a') else 'bid'
        price = int(price * self.price_factor)
        if str(amount_now) != '0':
            self._depth.execute("INSERT OR REPLACE INTO [%s] VALUES (?, ?)" %
                    table, (price, float(amount_now)))
        else:
            self._depth.execute("DELETE FROM [%s] WHERE price = ?" % table,
                    (price, ))

        self.need_replot += 1
        if self.need_replot > self.replot_after:
            # More than n changes since the last replot.
            print("Forcing replot", self.need_replot)
            self.replot()

