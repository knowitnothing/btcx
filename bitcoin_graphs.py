import treq
import pylab
import sqlite3
import calendar
from matplotlib import dates
from datetime import date, datetime, timedelta
from twisted.internet import reactor

from candlechart_noqt import Candlestick

SECURE = True
SOURCEFORGE_STATS = "sourceforge.net/projects/bitcoin/files"


def year_month_day(date):
    return '%d-%02d-%02d' % (date.year, date.month, date.day)

pending_calls = [0]
def sf_stats(start_date, end_date):
    protocol = 'https' if SECURE else 'http'

    while start_date < end_date:
        pending_calls[0] += 1
        # Daily stats
        start = year_month_day(start_date)
        end = year_month_day(start_date)
        start_date += timedelta(days=1)

        d = treq.get('%s://%s/stats/json?start_date=%s&end_date=%s' % (protocol,
            SOURCEFORGE_STATS, start, end))
        d.addCallback(lambda response:
                treq.json_content(response).addCallback(sf_stats_json))

sf_daily_stats = {}
def sf_stats_json(data):
    pending_calls[0] -= 1
    print pending_calls[0]
    date = map(int, data['start_date'].split(' ')[0].split('-'))
    dtime = datetime(year=date[0], month=date[1], day=date[2])

    sf_daily_stats[dtime] = {'total': data['total']}

    for country, dlcount in data['countries']:
        name = country.lower()
        if name in (u'china', u'united states'):
            sf_daily_stats[dtime][name] = dlcount


    if not pending_calls[0]:
        reactor.stop()


def ohlc_stats(start_date, end_date, dbname='mtgox_trades.db'):
    db = sqlite3.connect(dbname)
    table = 'btcusd'
    query = """SELECT price FROM [%s]
        WHERE timestamp >= ? AND timestamp < ?
        ORDER BY timestamp ASC""" % table

    while start_date < end_date:
        # Daily stats
        start = calendar.timegm(start_date.utctimetuple())
        start_date += timedelta(days=1)
        end = calendar.timegm(start_date.utctimetuple())

        result = db.execute(query, (start, end))
        first = float(result.fetchone()[0])
        o, h, l, c = first, first, first, first
        for trade in result:
            price = float(trade[0])
            c = price
            h = max(h, price)
            l = min(l, price)

        print start_date
        yield o, h, l, c



def do_the_plot(candle):
    fig = pylab.figure()
    ax = fig.add_subplot(111)

    dl_factor = 100 # Download counts will be divided by this amount
    plot_sf_stats(ax, fig, factor=dl_factor)
    plot_candles(ax, candle)
    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0] - 1, xlim[1] + 1)

    ax.grid()

    fig.suptitle(
            u'Bitcoin-QT download stats (%g x) mixed with MtGox USD price' %
            dl_factor)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.85, box.height])
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))

    pylab.show()


def plot_candles(ax, candle):
    cs = Candlestick(ax)
    for o, h, l, c in candle:
        cs.append_candle(o, h, l, c)

def plot_sf_stats(ax, fig, factor):
    factor = float(factor)

    x = []
    total = []
    china = []
    us = []
    for key in sorted(sf_daily_stats):
        val = sf_daily_stats[key]
        x.append(key)
        total.append(val['total'] / factor)
        china.append(val['china'] / factor)
        us.append(val['united states'] / factor)

    ax.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
    # Labels on mondays.
    ax.xaxis.set_major_locator(dates.WeekdayLocator(byweekday=dates.MO))

    #ax.set_ylabel(u'Download count (%g x)' % factor)

    ax.plot(x, total, label=u'Total DL')
    ax.plot(x, china, label=u'China DL')
    ax.plot(x, us, label=u'US DL')

    fig.autofmt_xdate()


if __name__ == "__main__":
    start_date = datetime(year=2013, month=2, day=1)
    end_date = datetime.fromordinal(date.today().toordinal())

    sf_stats(start_date, end_date)
    reactor.run()

    candle = ohlc_stats(start_date, end_date)

    # You might want to save sf_daily_stats
    print sf_daily_stats
    do_the_plot(candle)
