from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

import time
import calendar
from decimal import Decimal
from twisted.internet import reactor, task

# Own modules
import mtgox_tradehist
from btcx import mtgox
from candlechart import Candlestick
print("woof!")


class Demo(QG.QMainWindow):

    def __init__(self, db):
        QG.QMainWindow.__init__(self)

        self.db = db
        self.ts = None
        self.last_ts, self.last_tid = None, None
        self.last_candle = []

        self.candle_minute = 5
        self.plot_hours = 3
        self._load_last = '3.5' # x hours to load from database.

        self.candle_duration = 60 * self.candle_minute # 60 * x min = y seconds
        self.plot = Candlestick(self,
                max_candles=int((60 / self.candle_minute) * self.plot_hours),
                ylim_extra=0.02)

        self.setup_gui()
        self._loading = False

    def setup_gui(self):
        widget = QG.QWidget()

        quit_btn = QG.QPushButton(u'Quit')
        layout = QG.QVBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(quit_btn)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        quit_btn.pressed.connect(self.close)

        self.setWindowTitle(u'MtGox Trades -- 1 candle / %d min -- %d hours'
                % (self.candle_minute, self.plot_hours))
        self.plot.ax.set_ylabel(u'USD/BTC')
        self.plot.ax_vol.set_ylabel(u'Traded BTC')


    def load_from_db(self):
        if self._loading:
            return
        self._loading = True
        last_tid = self.last_tid
        if last_tid is None:
            result, self.ts = mtgox_tradehist.trades_from_db(self.db,
                    self._load_last)
        else:
            result, _ = mtgox_tradehist.trades_from_db(self.db,
                    raw_tid=last_tid)
        self._adjust_candles(result)
        self._loading = False

    def _adjust_candles(self, result):
        candle = self.last_candle
        last_ts = self.last_ts
        last_tid = self.last_tid

        new_trade = False
        for trade in result:
            new_trade = True
            self.last_tid, timestamp, usdprice, volume = trade
            usdprice = float(usdprice)
            volume = float(volume)
            if last_ts is None or timestamp - last_ts >= self.candle_duration:
                # Starting a new candle.
                self.last_ts = last_ts = self.ts

                if candle:
                    # Update the last candle added.
                    self.plot.update_right_candle(*candle, redraw=False)

                o, h, l, c = usdprice, usdprice, usdprice, usdprice
                v = volume
                candle[:] = [o, h, l, c, v]

                self.plot.append_candle(*candle, redraw=False)

                self.ts += self.candle_duration
            else:
                # Update the data of the last created candle.
                h, l = max(candle[1], usdprice), min(candle[2], usdprice)
                v = candle[-1] + volume
                candle[1:] = [h, l, usdprice, v]

        if new_trade:
            # Update last non-finished candle.
            self.plot.update_right_candle(*candle, redraw=False)
            # Redraw plot.
            self.plot.canvas.draw()



def main():
    mtgox_client, tradefetch, db = mtgox_tradehist.setup_client(verbose=0)
    plot = Demo(db)

    print('Loading from database..')
    plot.load_from_db()

    print('Setting up MtGox client..')
    mtgox_client.evt.listen('partial_download', lambda _: plot.load_from_db())
    mtgox_client.evt.listen('done', lambda _: plot.load_from_db())
    mtgox_client.evt.listen('done', lambda _:
            task.deferLater(reactor, 1, tradefetch.load_from_last_stored))
    mtgox.start(mtgox_client)

    print('Showing GUI..')
    plot.show()
    plot.raise_()

    def finish():
        print("Finishing..")
        if mtgox_client.connected:
            mtgox_client.sendClose()
        if reactor.running:
            reactor.stop()
            print("Reactor stopped")

    reactor.runReturn()
    app.lastWindowClosed.connect(finish)
    app.exec_()


if __name__ == "__main__":
    main()