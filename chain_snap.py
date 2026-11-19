"""Nifty option chain ka snapshot (ATM +-6 strike, CE+PE): bhav, bid/ask, buyer/seller quantity, OI, volume.
Har 5 min chalao (market ke time). data/chain/<date>.csv me jud jata hai.
Maksad: baad me test karna ki buyer>seller (depth imbalance) se agle 5-15 min me premium sach me badhta hai ya nahi.
Run: python3 chain_snap.py
"""
import csv
import datetime
import os

import opt_pick

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'chain')
COLS = ['ts', 'spot', 'expiry', 'strike', 'type', 'ltp', 'bid', 'ask', 'bq1', 'sq1', 'tbq', 'tsq', 'oi', 'doi', 'vol', 'iv']


def main(sym='NIFTY'):
    spot, expiry, rows = opt_pick.chain(sym, None)
    now = datetime.datetime.now(IST)
    atm = round(spot / 50) * 50
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, now.strftime('%Y-%m-%d') + '.csv')
    new = not os.path.exists(path)
    n = 0
    with open(path, 'a', newline='') as h:
        w = csv.writer(h)
        if new:
            w.writerow(COLS)
        for x in rows:
            if abs(x['strikePrice'] - atm) > 300:
                continue
            for t in ('CE', 'PE'):
                o = x.get(t)
                if not o:
                    continue
                w.writerow([now.strftime('%H:%M:%S'), spot, expiry, int(x['strikePrice']), t, o.get('lastPrice'), o.get('buyPrice1'),
                            o.get('sellPrice1'), o.get('buyQuantity1'), o.get('sellQuantity1'), o.get('totalBuyQuantity'),
                            o.get('totalSellQuantity'), o.get('openInterest'), o.get('changeinOpenInterest'),
                            o.get('totalTradedVolume'), o.get('impliedVolatility')])
                n += 1
    print('chain snapshot %s: %d rows -> %s' % (now.strftime('%H:%M'), n, path))


if __name__ == '__main__':
    main()
