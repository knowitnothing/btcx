from __future__ import print_function

import numpy
import pylab
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC
from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure


class SimplePlot(QG.QWidget):

    def __init__(self, parent, lineconfig, ax_bbox, navbar=True, timeout=350):
        #
        # lineconfig is expected to be an ordered sequence of (key, value):
        #       key: plot name
        #       value: a dict with the mandatory keys:
        #                 title: plot title
        #                 ylabel: plot ylabel
        #                 numpoints: number of points in the plot
        #                 line: a sequence of (name, label, color,, kwargs)
        #              optional keys:
        #                 grid
        #                 legend
        #
        #       The pair key (plot name) and name (line name) must be unique.
        #
        QG.QWidget.__init__(self, parent)

        self.navbar = navbar
        self.ax_bbox = ax_bbox
        self.lineconfig = lineconfig

        self.xdata = {}
        self.ydata = {}
        self.last_xi = {}
        for k, v in lineconfig:
            for opt in ('grid', 'legend', 'ylim_extra'):
                if opt not in v:
                    v[opt] = 0
            npoints = v['numpoints']
            for lname, _, _, _ in v['line']:
                self.ydata[k, lname] = numpy.zeros(npoints)
                self.xdata[k, lname] = numpy.arange(npoints, dtype=int)
                self.last_xi[k, lname] = 0

        self.create_gui_plot()

        self.need_replot = True
        self.timer = QC.QTimer()
        self.timer.timeout.connect(self._replot)
        self.timer.start(timeout) # x ms for timeout.

    def closeEvent(self, event):
        # This widget is going away.
        self.timer.stop()
        event.accept()


    def create_gui_plot(self):
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        ax_cfg = iter(self.ax_bbox)
        self.ax = {}
        for name, _ in self.lineconfig:
            self.ax[name] = self.fig.add_axes(next(ax_cfg))
        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.canvas)
        if self.navbar:
            self.mpl_bar = NavigationToolbar(self.canvas, self)
            layout.addWidget(self.mpl_bar)
        self.setLayout(layout)

        # Trade plot
        self.line = {}
        self.ylim = {}
        self.ylim_extra = {}
        for name, value in self.lineconfig:
            ax = self.ax[name]
            ax.set_title(value['title'])
            ax.set_ylabel(value['ylabel'])
            for lname, llbl, lcolor, kwargs in value['line']:
                line = ax.plot([], [], lcolor, label=llbl, **kwargs)[0]
                self.line[name, lname] = line

            ax.set_xlim(0, value['numpoints'] - 1)
            pylab.setp(ax.get_xticklabels(), visible=False)
            self.ylim[name] = [float('inf'), float('-inf')]
            self.ylim_extra[name] = value['ylim_extra']

            if value['grid']:
                ax.grid()
            if value['legend']:
                ax.legend(**value['legend'])


    def append_value(self, value, plotname, linename, update=True):
        if (plotname, linename) not in self.ydata:
            raise Exception("Unknown plot '%s-%s'" % (plotname, linename))

        ydata = self.ydata[plotname, linename]
        i = self.last_xi[plotname, linename]
        if i == len(ydata):
            self.ydata[plotname, linename] = numpy.roll(ydata, -1)
            i -= 1
        else:
            self.last_xi[plotname, linename] += 1

        self.ydata[plotname, linename][i] = value
        if update:
            self.update_line(plotname, linename)


    def update_line(self, plotname, linename):
        line = self.line[plotname, linename]
        ydata = self.ydata[plotname, linename]
        xdata = self.xdata[plotname, linename]
        i = self.last_xi[plotname, linename]
        ylim = list(self.ylim[plotname])

        if i == len(xdata):
            line.set_data(xdata, ydata)
            ylim[0] = min(ylim[0], ydata.min())
            ylim[1] = max(ylim[1], ydata.max())
        else:
            line.set_data(xdata[:i], ydata[:i])
            ylim[0] = min(ylim[0], ydata[:i].min())
            ylim[1] = max(ylim[1], ydata[:i].max())

        self.ylim[plotname] = ylim
        self.ax[plotname].set_ylim(
                ylim[0] - self.ylim_extra[plotname],
                ylim[1] + self.ylim_extra[plotname])
        self.need_replot = True


    def _replot(self):
        if self.need_replot:
            self.fig.canvas.draw()
            self.need_replot = False


def main(key, secret):

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


if __name__ == "__main__":
    app = QG.QApplication([])

    currency = 'USD'
    yl = u'%s/COIN' % currency
    ax1_kw = {'lw': 2, 'ls': 'steps'}
    plot = SimplePlot(None, lineconfig=(
        ('trades', {'title': u'Trades', 'ylabel': yl, 'numpoints': 120,
                    'legend': {'loc': 'upper center',
                               'bbox_to_anchor': (0.5, -0.05), 'ncol': 2},
                    'grid': True,
                    'ylim_extra': 1.0,
                    'line': (('a', u'R', 'r', ax1_kw),
                             ('b', u'B', 'b', ax1_kw))}
        ),
        ('foo',    {'title': u'', 'ylabel': u'Some label', 'numpoints': 40,
                    'ylim_extra': 0.1,
                    'line': (('x', u'', 'k', {'lw': 1, 'ls': 'steps'}), )}
        )),
        ax_bbox=(([0.1, 0.4, 0.8, 0.55], [0.1, 0.05, 0.8, 0.2])),
        navbar=True, timeout=20)
    plot.show()
    plot.raise_()

    def random_data():
        import random
        pname, lname = random.choice(plot.ydata.keys())
        plot.append_value(random.random(), pname, lname)
    timer = QC.QTimer()
    timer.timeout.connect(random_data)
    timer.start(20)

    app.exec_()
