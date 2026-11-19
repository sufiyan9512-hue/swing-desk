"""Paper record: har alert ka kaun sa strike/entry/stop tha aur baad me kya hua. 3-4 hafte baad asli win-rate dikhega.

  python3 option_paper.py add NIFTY CE 25300 23-Nov-2026 225.0 217.3 25386 25503 25619 25502
        (index side strike expiry entry_prem sl_prem idx_stop idx_t1 idx_t2 idx_at_signal [note, jaise imb=1.8x_BUYER])
  python3 option_paper.py update     # open rows ko 5-min index close + Nifty premium LTP se check karo
  python3 option_paper.py summary    # win/loss, T1/T2/SL, avg points

Status: OPEN -> SL (index 5-min close stop paar / premium SL) | T1 | T2 | EOD (15:25 par band)
Sab kuch paper hai (asli paisa nahi). Result index points me + 1 lot ka approx Rs (delta 0.6 maan kar).
"""
import csv
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'option_paper.csv')
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
COLS = ['ts', 'index', 'side', 'strike', 'expiry', 'entry_prem', 'sl_prem', 'idx_stop', 'idx_t1', 'idx_t2',
        'idx_entry', 'status', 'exit_idx', 'exit_prem', 'idx_pts', 'est_rs_1lot', 'max_prem', 'min_prem', 'closed_at', 'note']
SYM = {'NIFTY': '^NSEI', 'SENSEX': '^BSESN'}
LOT = {'NIFTY': 65, 'SENSEX': 20}


def rd():
    if not os.path.exists(PATH):
        return []
    return list(csv.DictReader(open(PATH, encoding='utf-8')))


def wr(rows):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, 'w', newline='', encoding='utf-8') as h:
        w = csv.DictWriter(h, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in COLS})


def last_close(sym):
    u = 'https://query2.finance.yahoo.com/v8/finance/chart/%s?range=1d&interval=5m' % urllib.parse.quote(SYM[sym])
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())['chart']['result'][0]
    q = res['indicators']['quote'][0]
    c = [(t, x) for t, x in zip(res['timestamp'], q['close']) if x]
    return c[-2][1] if len(c) >= 2 else c[-1][1]       # sirf poora ho chuka 5-min candle


def add(a):
    idx, side, strike, expiry, ep, sl, st_, t1, t2, ie = a[:10]
    note = a[10] if len(a) > 10 else ''
    r = dict(ts=datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M'), index=idx.upper(), side=side.upper(), strike=strike,
             expiry=expiry, entry_prem=ep, sl_prem=sl, idx_stop=st_, idx_t1=t1, idx_t2=t2, idx_entry=ie, status='OPEN',
             max_prem=ep, min_prem=ep, note=note)
    rows = rd()
    rows.append(r)
    wr(rows)
    print('paper row added:', r['ts'], r['index'], r['side'], r['strike'])


def premium(r):
    try:
        import opt_pick
        spot, exp, rows = opt_pick.chain(r['index'], r['expiry'])
        for x in rows:
            if x['strikePrice'] == float(r['strike']):
                o = x.get(r['side'])
                return float(o['lastPrice']) if o and o.get('lastPrice') else None
    except Exception:
        return None


def update():
    rows = rd()
    now = datetime.datetime.now(IST)
    eod = now.hour * 60 + now.minute >= 15 * 60 + 25
    changed = 0
    for r in rows:
        if r['status'] != 'OPEN':
            continue
        if not r['ts'].startswith(now.strftime('%Y-%m-%d')) and not eod:
            r['status'] = 'EOD'; changed += 1; continue      # purani row jo band na hui
        try:
            c = last_close(r['index'])
        except Exception:
            continue
        up = r['side'] == 'CE'
        stop, t1, t2, ie = (float(r[k]) for k in ('idx_stop', 'idx_t1', 'idx_t2', 'idx_entry'))
        p = premium(r) if r['index'] == 'NIFTY' else None
        if p:
            r['max_prem'] = str(max(float(r['max_prem'] or p), p)); r['min_prem'] = str(min(float(r['min_prem'] or p), p))
        st = None
        if (c < stop) if up else (c > stop):
            st = 'SL'
        elif p and r['sl_prem'] and p <= float(r['sl_prem']):
            st = 'SL'
        elif (c >= t2) if up else (c <= t2):
            st = 'T2'
        elif (c >= t1) if up else (c <= t1):
            st = 'T1'
        elif eod:
            st = 'EOD'
        if st:
            r['status'] = st; r['exit_idx'] = '%.1f' % c; r['closed_at'] = now.strftime('%H:%M')
            if p:
                r['exit_prem'] = '%.1f' % p
            pts = (c - ie) if up else (ie - c)
            r['idx_pts'] = '%.1f' % pts
            r['est_rs_1lot'] = '%.0f' % (pts * 0.6 * LOT.get(r['index'], 65))
            changed += 1
    wr(rows)
    print('update: %d row badli' % changed)


def summary():
    rows = [r for r in rd() if r['status'] != 'OPEN']
    if not rows:
        print('Abhi koi band paper trade nahi.')
        return
    n = len(rows)
    win = [r for r in rows if r['status'] in ('T1', 'T2') or (r['status'] == 'EOD' and float(r['idx_pts'] or 0) > 0)]
    sl = [r for r in rows if r['status'] == 'SL']
    pts = [float(r['idx_pts'] or 0) for r in rows]
    rs = [float(r['est_rs_1lot'] or 0) for r in rows]
    print('paper trades %d | jeete %d (%.0f%%) | SL %d | avg index pts %+.1f | approx 1-lot Rs total %+.0f' % (
        n, len(win), 100.0 * len(win) / n, len(sl), sum(pts) / n, sum(rs)))
    for r in rows[-10:]:
        print(' ', r['ts'], r['index'], r['side'], r['strike'], r['status'], r['idx_pts'], 'pts', r['est_rs_1lot'], 'Rs')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'summary'
    {'add': lambda: add(sys.argv[2:]), 'update': update, 'summary': summary}[cmd]()
