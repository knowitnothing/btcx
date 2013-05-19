import numpy
import pylab

class SimplePlot(object):

    def __init__(self, figure,canvas,lineconfig,ax_bbox,navbar=True,**kwargs):
        #
        # lineconfig is expected to be an ordered sequence of (key, value):
        #       key: plot name
        #       value: a dict with the mandatory keys:
        #                 title: plot title
        #                 ylabel: plot ylabel
        #                 numpoints: number of points to store
        #                 line: a sequence of (name, label, color,, kwargs)
        #              optional keys:
        #                 grid
        #                 legend
        #
        #       The pair key (plot name) and name (line name) must be unique.
        #
        self.fig = figure
        self.canvas = canvas

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

        self.setup_plot()

        self.need_replot = False


    def setup_plot(self):
        self.ax = {}
        ax_cfg = iter(self.ax_bbox)
        for name, _ in self.lineconfig:
            self.ax[name] = self.fig.add_axes(next(ax_cfg))

        self.line = {}
        self.ylim = {}
        self.ylim_extra = {}
        for name, value in self.lineconfig:
            ax = self.ax[name]
            ax.set_title(value['title'])
            ax.set_ylabel(value['ylabel'])
            self.ylim[name] = {}
            self.line[name] = {}
            for lname, llbl, lcolor, kwargs in value['line']:
                line = ax.plot([], [], lcolor, label=llbl, **kwargs)[0]
                self.line[name][lname] = line
                self.ylim[name][lname] = [float('inf'), float('-inf')]

            ax.set_xlim(0, value['numpoints'] - 1)
            pylab.setp(ax.get_xticklabels(), visible=False)
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
        line = self.line[plotname][linename]
        ydata = self.ydata[plotname, linename]
        xdata = self.xdata[plotname, linename]
        ylim = self.ylim[plotname][linename]
        i = self.last_xi[plotname, linename]

        if i:
            line.set_data(xdata[:i], ydata[:i])
            ylim[0] = ydata[:i].min()
            ylim[1] = ydata[:i].max()

        yl = [float('inf'), float('-inf')]
        for yli in self.ylim[plotname].itervalues():
            yl[0] = min(yl[0], yli[0])
            yl[1] = max(yl[1], yli[1])

        self.ax[plotname].set_ylim(
                yl[0] - self.ylim_extra[plotname],
                yl[1] + self.ylim_extra[plotname])
        self.need_replot = True


    def replot(self):
        if not self.need_replot:
            return

        self.canvas.draw_idle()
        self.need_replot = False

