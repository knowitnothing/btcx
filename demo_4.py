from __future__ import print_function
print("Loading modules..")
import PyQt4.QtGui as QG

app = QG.QApplication([])
import qt4reactor
qt4reactor.install()

import time
from twisted.internet import reactor, task

# Own modules
import mtgox_tradehist
from candlechart import Candlestick
print("woof!")


class Demo(QG.QMainWindow):

    def __init__(self, db, max_hours_ago='3.5', **kwargs):
        QG.QMainWindow.__init__(self)

        self.db = db
        self.loaded = False
        self.ts = None
        self.last_ts, self.last_tid = None, None
        self.last_candle = []

        self.candle_minute = kwargs.get('candle_minute_duration', 60)
        self.plot_hours = kwargs.get('plot_hours', 24)
        self._load_last = max_hours_ago # x hours to load from database.

        self.candle_duration = 60 * self.candle_minute # 60 * x min = y seconds
        self.plot = Candlestick(self,
                max_candles=int((60 / self.candle_minute) * self.plot_hours),
                ylim_extra=0.02)

        self.setup_gui()
        self._loading = False

    def closeEvent(self, event):
        reactor.stop()
        event.accept()
        print("Now we wait..")

    def setup_gui(self):
        widget = QG.QWidget()

        quit_btn = QG.QPushButton(u'Quit')
        layout = QG.QVBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(quit_btn)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        quit_btn.pressed.connect(self.close)

        self.setWindowTitle(u'MtGox Trades -- 1 candle / %g min -- %g hours'
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
                    print("finished", time.localtime(last_ts), candle)
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
            self.plot.canvas.draw_idle()


def main():
    hours_ago = 48 # 2 days of data
    mtgox_client, tradefetch, db = mtgox_tradehist.setup_client(verbose=0,
            max_hours_ago=hours_ago, dbname='mtgox_trades3.db')
    plot = Demo(db, max_hours_ago=hours_ago,
            candle_minute_duration=30, # 2 candles per hour
            plot_hours=48)             # 2 days, 96 candles

    print('Loading from database..')
    plot.load_from_db()

    print('Setting up MtGox client..')

    def store_new_trade(trade):
        if trade.timestamp is None:
            return
        elif not plot.loaded:
            print("still fetching..")
            return
        print("> trade", trade)
        tradefetch.store_trade(trade)
        task.deferLater(reactor, 0, plot.load_from_db)

    def stop_accepting_trades(client):
        print("no more live trades for you")
        plot.loaded = False

    def start_accepting_trades(client):
        print("what is done is done")
        plot.load_from_db()
        plot.loaded = True

    # During loading from database, we will receive several 'partial_download'
    # events representing that some part of the requested data is already
    # available.
    mtgox_client.evt.listen('partial_download', lambda _: plot.load_from_db())
    # If the database has been loaded, trades from the streaming data will
    # be stored as they come in.
    mtgox_client.evt.listen('trade', store_new_trade)

    # Each time we connect, listen from trades.
    mtgox_client.call('subscribe_type', 'trades', on_event='connected')
    # After database is loaded, start storing new trades.
    mtgox_client.call(start_accepting_trades, on_event='done')
    # When we disconnect, we need to identify that we need to fetch
    # trades again once we reconnect.
    mtgox_client.call(stop_accepting_trades, on_event='disconnected')
    # Note that the object is listening for the 'connected' event
    # such that it will download the trades we missed while
    # disconnected and then emit a 'done' event after it has fetched
    # all such trades.
    #
    # Nice eh ?


    print('Showing GUI..')
    plot.show()
    plot.raise_()

    reactor.addSystemEventTrigger('after', 'shutdown', app.quit)
    reactor.run()


if __name__ == "__main__":
    main()
