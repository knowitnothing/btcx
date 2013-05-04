from collections import deque
from matplotlib import patches, lines

class Candlestick(object):
    def __init__(self, ax, **candle_kwargs):
        self.config = {'empty': candle_kwargs.get('empty', 'none'),
                       'filled': candle_kwargs.get('filled', 'k'),
                       'edgecolor': candle_kwargs.get('edgecolor', 'k')}

        self.ax = ax
        self.ylim = list(ax.get_ylim())

        self.x = ax.get_xlim()[0]
        self.candle = deque()

    def _make_candle(self, x, o, h, l, c):
        empty = self.config['empty']
        filled = self.config['filled']
        edgecolor = self.config['edgecolor']

        lower_val = min(o, c)
        upper_val = max(o, c)

        body_color = empty if c > o else filled
        body_width = 0.72
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

    def _update_ylim(self, lu, ll):
        self.ylim[0] = min(self.ylim[0], ll.get_ydata()[0])
        self.ylim[1] = max(self.ylim[1], lu.get_ydata()[1])
        self.ax.set_ylim(self.ylim[0], self.ylim[1])

    def append_candle(self, o, h, l, c):
        x = self.x
        lu, b, ll = self._make_candle(x, o, h, l, c)
        lu = self.ax.add_line(lu)
        b = self.ax.add_patch(b)
        ll = self.ax.add_line(ll)
        self.candle.append((lu, b, ll))
        self._update_ylim(lu, ll)
        self.x += 1

