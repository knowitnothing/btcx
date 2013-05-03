import pylab
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC
from matplotlib.backends.backend_qt4agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib import patches, lines
from collections import deque


class Candlestick(QG.QWidget):
    def __init__(self, parent, max_candles=36, ylim_extra=0.1, **candle_kwargs):
        QG.QWidget.__init__(self, parent)

        # Candle layout configuration.
        self.config = {'empty': candle_kwargs.get('empty', 'none'),
                       'filled': candle_kwargs.get('filled', 'k'),
                       'edgecolor': candle_kwargs.get('edgecolor', 'k')}

        self.navbar = True
        self.max_candles = max_candles
        self.ylim_extra = ylim_extra
        self.ylim = [float('inf'), float('-inf')]
        self.vol_max = 0
        self.x = 0

        self.candle = deque()

        self.create_plot()
        self.setup_gui()


    def create_plot(self):
        self.fig = Figure(figsize=(8, 3.8))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)

        ax_bbox = ([0.1, 0.28, 0.87, 0.68], [0.1, 0.04, 0.87, 0.2])
        self.ax = self.fig.add_axes(ax_bbox[0]) # candlesticks
        self.ax_vol = self.fig.add_axes(ax_bbox[1], sharex=self.ax) # volume

        pylab.setp(self.ax.get_xticklabels(), visible=False)
        pylab.setp(self.ax_vol.get_xticklabels(), visible=False)
        # XXX Make the following settings configurable.
        self.vol = self.ax_vol.bar(range(-1, self.max_candles + 1),
                [0] + ([0] * self.max_candles) + [0], align='center',
                width=0.4, color='orange', alpha=0.5)
        self.ax.set_xlim(-1, self.max_candles + 1)
        self.ax_vol.set_ylim(0, 1)

    def setup_gui(self):
        layout = QG.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.canvas)
        if self.navbar:
            self.mpl_bar = NavigationToolbar(self.canvas, self)
            layout.addWidget(self.mpl_bar)
        self.setLayout(layout)


    def _make_candle(self, x, o, h, l, c):
        empty = self.config['empty']
        filled = self.config['filled']
        edgecolor = self.config['edgecolor']

        lower_val = min(o, c)
        upper_val = max(o, c)

        body_color = empty if c > o else filled
        body_width = 0.42
        body_height = abs(o - c)
        body_options = {'width': body_width, 'edgecolor': edgecolor,
                        'height': body_height, 'facecolor': body_color,
                        'xy': (x - body_width/2., lower_val)}

        line_options = {'color': body_options['edgecolor'], 'lw': 1,
                        'xdata': (x, x)}

        body = patches.Rectangle(**body_options)
        upper = lines.Line2D(ydata=(upper_val, h), **line_options)
        lower = lines.Line2D(ydata=(l, lower_val), **line_options)

        return upper, body, lower

    def _update_ylim(self, lu, ll, v):
        self.ylim[0] = min(self.ylim[0], ll.get_ydata()[0])
        self.ylim[1] = max(self.ylim[1], lu.get_ydata()[1])
        self.ax.set_ylim(self.ylim[0] - self.ylim_extra,
                         self.ylim[1] + self.ylim_extra)

        self.vol_max = max(self.vol_max, v)
        self.ax_vol.set_ylim(0, self.vol_max)


    def append_candle(self, o, h, l, c, v, redraw=True):
        x = self.x
        lu, b, ll = self._make_candle(x, o, h, l, c)
        lu = self.ax.add_line(lu)
        b = self.ax.add_patch(b)
        ll = self.ax.add_line(ll)
        self.candle.append((lu, b, ll, v))
        self._update_ylim(lu, ll, v)
        self.x += 1

        if self.x > self.max_candles:
            self.remove_left_candle()

        self.vol[self.x].set_height(v)

        if redraw:
            self.canvas.draw_idle()

    def update_right_candle(self, o, h, l, c, v, redraw=True):
        self.vol[self.x].set_height(v)
        lu, b, ll = self._make_candle(self.x - 1, o, h, l, c)
        for item in self.candle.pop()[:3]:
            item.remove()
        lu = self.ax.add_line(lu)
        b = self.ax.add_patch(b)
        ll = self.ax.add_line(ll)
        self.candle.append((lu, b, ll, v))
        self._update_ylim(lu, ll, v)

        if redraw:
            self.canvas.draw_idle()

    def remove_left_candle(self):
        for item in self.candle.popleft()[:3]:
            item.remove()

        self.x -= 1

        # Shift all the remaining candles to the left.
        self.vol_max = 0
        self.ylim = [float('inf'), float('-inf')]
        for i, (lu, b, ll, v) in enumerate(self.candle, start=1):
            xdata = lu.get_xdata()
            lu.set_xdata((xdata[0] - 1, xdata[1] - 1))
            ll.set_xdata((xdata[0] - 1, xdata[1] - 1))
            xy = b.get_xy()
            b.set_xy((xy[0] - 1, xy[1]))

            self.vol[i].set_height(v)

            self.ylim[0] = min(self.ylim[0], ll.get_ydata()[0])
            self.ylim[1] = max(self.ylim[1], lu.get_ydata()[1])
            self.vol_max = max(self.vol_max, v)

        self.ax.set_ylim(self.ylim[0] - self.ylim_extra,
                         self.ylim[1] + self.ylim_extra)
        self.ax_vol.set_ylim(0, self.vol_max)


if __name__ == "__main__":
    app = QG.QApplication([])

    cs = Candlestick(None, max_candles=12 * 4)
    cs.show()
    cs.raise_()

    import random
    random.seed(0)
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
    timer = QC.QTimer()
    timer.timeout.connect(random_data)
    timer.start(25)

    app.exec_()
