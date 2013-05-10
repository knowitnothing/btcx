from __future__ import print_function
print("Loading modules..")
import sys
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

from twisted.internet import reactor

# Own modules
from btcx import mtgox, cfgmanager
from depthplot import PlotDepth
print("woof!")


class Demo(object):
    def __init__(self, plot, currency=u'USD'):
        self.plot = plot
        self.currency = currency.upper()

        plot.ax.set_xlabel(self.currency)
        plot.ax.set_ylabel(u'BTC')

        self.own_order = {}
        self.ask, self.bid = None, None

    def userorder(self, order):
        oid, price = order.id, order.price
        if order.status == "removed":
            if oid in self.own_order:
                print('removing line at', price)
                data = self.own_order.pop(oid)
                data[1].remove()
        else:
            print(order)
            currency = order.pair[0]
            if currency == self.currency and oid not in self.own_order:
                print('adding line at', price)
                line = self.plot.ax.axvline(x=float(price), color='b')
                self.own_order[oid] = (price, line)

    def depth_fetch(self, depth):
        if depth.type is None:
            # Fetch finished.
            self.plot.replot_after = 30
            print("There you go")
        else:
            self.plot.replot_after = 1000
            self.plot.new_data(depth.type, depth.price, depth.volume)

    def depth_live(self, depth):
        print(depth)
        self.plot.new_data(depth.type, depth.price, depth.volume)


def main(key, secret):
    # List of the currency symbols available in MtGox:
    # USD, AUD, CAD, CHF, CNY, DKK, EUR, GBP, HKD, JPY, NZD, PLN, RUB, SEK,
    # SGD, THB, NOK, CZK
    currency = 'USD'

    main = QG.QMainWindow()
    w = QG.QWidget()
    plot = PlotDepth(axconf=[0.1, 0.15, 0.87, 0.81])
    l = QG.QVBoxLayout()
    l.addWidget(plot)
    w.setLayout(l)
    main.setWindowTitle(u'MtGox Depth Market')
    main.setCentralWidget(w)
    def finish(event):
        reactor.stop()
        event.accept()
    main.closeEvent = finish

    demo = Demo(plot, currency)

    cli = mtgox.create_client(key, secret, currency)
    mtgox.start(cli)

    cli.evt.listen('depth_fetch', demo.depth_fetch)
    cli.evt.listen('depth', demo.depth_live)
    cli.evt.listen('userorder', demo.userorder)

    cli.call('subscribe_type', 'depth') # Default event: connected.
    cli.call('order_list')
    # If you do not wish to pre-load depth data, comment the following line.
    cli.call('depth_fetch', once=True)

    main.show()
    main.raise_()

    reactor.addSystemEventTrigger('after', 'shutdown', app.quit)
    reactor.run()


if __name__ == "__main__":
    key, secret = cfgmanager.obtain_key_secret(sys.argv[1:])
    main(key or '', secret or '')
