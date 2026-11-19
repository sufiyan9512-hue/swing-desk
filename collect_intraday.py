"""Roz ka intraday data jama karo (Nifty, Sensex, BankNifty): 1-min (Yahoo ~8 din) aur 5-min (~60 din).
Har run purane data me naya jod deta hai (dedupe), isliye roz chalane se 2-3 mahine me level/option tests ke liye
lamba intraday data ban jata hai. Output: data/intraday/<NAME>_<1m|5m>.csv.gz  (ts_ist,o,h,l,c,v)

Run: python3 collect_intraday.py     (workflow: intraday.yml roz 16:00 IST)
"""
import datetime
import gzip
import io
import json
import os
import urllib.parse
import urllib.request

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
SYMS = {'NIFTY': '^NSEI', 'SENSEX': '^BSESN', 'BANKNIFTY': '^NSEBANK'}
JOBS = [('1m', '8d'), ('5m', '60d')]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'intraday')


def fetch(sym, itv, rng):
    u = 'https://query2.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=%s' % (urllib.parse.quote(sym), rng, itv)
    res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read().decode())['chart']['result'][0]
    q = res['indicators']['quote'][0]
    rows = {}
    for i, t in enumerate(res['timestamp']):
        if q['close'][i] is None or q['open'][i] is None:
            continue
        ts = datetime.datetime.fromtimestamp(t, IST).strftime('%Y-%m-%d %H:%M')
        rows[ts] = (q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i] or 0)
    return rows


def load(path):
    rows = {}
    if os.path.exists(path):
        with gzip.open(path, 'rt') as h:
            next(h, None)
            for line in h:
                p = line.strip().split(',')
                if len(p) == 6:
                    rows[p[0]] = tuple(float(x) for x in p[1:])
    return rows


def save(path, rows):
    buf = io.StringIO()
    buf.write('ts_ist,o,h,l,c,v\n')
    for ts in sorted(rows):
        o, h, l, c, v = rows[ts]
        buf.write('%s,%.2f,%.2f,%.2f,%.2f,%d\n' % (ts, o, h, l, c, v))
    with gzip.open(path, 'wt') as h:
        h.write(buf.getvalue())


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, sym in SYMS.items():
        for itv, rng in JOBS:
            path = os.path.join(OUT, '%s_%s.csv.gz' % (name, itv))
            try:
                new = fetch(sym, itv, rng)
            except Exception as e:
                print(name, itv, 'FAIL', str(e)[:60])
                continue
            old = load(path)
            before = len(old)
            old.update(new)
            save(path, old)
            days = len({k[:10] for k in old})
            print('%-9s %s: +%d bars (total %d, %d din, %s se %s)' % (name, itv, len(old) - before, len(old), days, min(old)[:10], max(old)[:10]))


if __name__ == '__main__':
    main()
