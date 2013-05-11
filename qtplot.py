import PyQt4.QtGui as QG
import PyQt4.QtCore as QC
from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg, NavigationToolbar2QTAgg)
from matplotlib.figure import Figure

from depthplot import PlotDepth
from simpleplot import SimplePlot
from candlechart import Candlestick


class PlotDepthWidget(QG.QWidget):
    def __init__(self, parent=None, axconf=None, timeout=2000):
        QG.QWidget.__init__(self, parent)

        figure = Figure(figsize=(8, 3))
        canvas = FigureCanvasQTAgg(figure)
        canvas.setParent(self)
        self.plot = PlotDepth(figure, canvas, axconf)

        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.plot.canvas)
        self.setLayout(layout)

        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.plot.replot)
        self.timer.start(timeout) # x ms.

        self.timer_clean = QC.QTimer()
        self.timer_clean.timeout.connect(self.plot.clean_db)
        # Remove unused/old data from in-memory database each n seconds.
        self.timer_clean.start(5 * 1000)

    def closeEvent(self, event):
        self.timer.stop()
        self.timer_clean.stop()
        event.accept()


class SimplePlotWidget(QG.QWidget):
    def __init__(self, parent, lineconfig, ax_bbox, navbar=True, timeout=350,
            **kwargs):
        QG.QWidget.__init__(self, parent)

        figure = Figure()
        canvas = FigureCanvasQTAgg(figure)
        self.plot = SimplePlot(figure, canvas, lineconfig, ax_bbox, **kwargs)

        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.plot.canvas)
        if navbar:
            self.mpl_bar = NavigationToolbar2QTAgg(self.plot.canvas, self)
            layout.addWidget(self.mpl_bar)
        self.setLayout(layout)

        self.timer = QC.QTimer()
        self.timer.timeout.connect(self.plot.replot)
        self.timer.start(timeout) # x ms for timeout.

    def closeEvent(self, event):
        # This widget is going away.
        self.timer.stop()
        event.accept()


class CandlestickWidget(QG.QWidget):
    def __init__(self, parent, navbar=True, **kwargs):
        QG.QWidget.__init__(self, parent)

        figure = Figure(figsize=(8, 3.8))
        canvas = FigureCanvasQTAgg(figure)
        canvas.setParent(self)
        self.plot = Candlestick(figure, canvas, **kwargs)

        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.plot.canvas)
        if navbar:
            self.mpl_bar = NavigationToolbar2QTAgg(self.plot.canvas, self)
            layout.addWidget(self.mpl_bar)
        self.setLayout(layout)


if __name__ == "__main__":
    import random
    random.seed(0)
    app = QG.QApplication([])

    # SimplePlot usage.
    currency = 'USD'
    yl = u'%s/COIN' % currency
    ax1_kw = {'lw': 2, 'ls': 'steps'}
    plotw = SimplePlotWidget(None, lineconfig=(
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
        navbar=True, timeout=5)
    plotw.show()
    plotw.raise_()
    plot = plotw.plot

    def random_data():
        pname, lname = random.choice(plot.ydata.keys())
        if random.random() < 0.05:
            plot.append_value(random.random() * 100, pname, lname)
        else:
            plot.append_value(random.random(), pname, lname)
    timer1 = QC.QTimer()
    timer1.timeout.connect(random_data)
    timer1.start(10)

    # Candlestick usage
    csw = CandlestickWidget(None, max_candles=12 * 4)
    csw.show()
    csw.raise_()
    cs = csw.plot

    def random_data():
        o, c = [random.randint(9, 12) for _ in xrange(2)]
        h = random.randint(max(o, c), 14)
        l = random.randint(6, min(o, c))
        v = random.random()
        if random.random() < 0.25 or not cs.candle:
            cs.append_candle(o, h, l, c, v)
        else:
            vol_last = cs.candle[-1][-1]
            cs.update_right_candle(o, h, l, c, vol_last + v)
    timer2 = QC.QTimer()
    timer2.timeout.connect(random_data)
    timer2.start(25)


    app.exec_()
