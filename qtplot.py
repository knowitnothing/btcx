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
