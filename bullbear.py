"""Bull vs Bear checklist + swing scanner (roz 15:15 ke baad chalao, agle din ke liye).

Use:  python3 bullbear.py                 # default liquid list + holdings
      python3 bullbear.py TATASTEEL SOBHA # sirf yeh stock
Output: har stock ke BULL points, BEAR points, tested-setup flag, stop (2 ATR), 1 trade ka qty (risk Rs800).

Tested (HANDOFF): DROP8 (3 din me >=8% gira) +0.057R, 4/4 saal; Oversold(RSI<=30) VWEAK me +0.26R.
Baaki sab (bull/bear points) sirf CHECKLIST hai, tested edge NAHI. Koi order nahi lagta.
"""
import json
import sys
import urllib.parse
import urllib.request

import pandas as pd

RISK = 800.0       # ek trade me max nuksaan (Rs)
CAP = 50000.0
DEFAULT = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'SBIN', 'AXISBANK', 'KOTAKBANK', 'LT', 'ITC',
           'BHARTIARTL', 'MARUTI', 'SUNPHARMA', 'BAJFINANCE', 'NTPC', 'ONGC', 'COALINDIA', 'ADANIENT',
           'TATASTEEL', 'TATAMOTORS', 'M&M', 'HCLTECH', 'WIPRO', 'TECHM', 'ASIANPAINT', 'TITAN', 'ULTRACEMCO',
           'POWERGRID', 'JSWSTEEL', 'HINDALCO', 'CIPLA', 'DRREDDY', 'EICHERMOT', 'BAJAJFINSV', 'BRITANNIA',
           'GRASIM', 'INDUSINDBK', 'BPCL', 'SOBHA', 'SHRINGARMS']


def fetch(sym):
    u = 'https://query2.finance.yahoo.com/v8/finance/chart/%s.NS?range=1y&interval=1d' % urllib.parse.quote(sym)
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())['chart']['result'][0]
    q = r['indicators']['quote'][0]
    df = pd.DataFrame({'o': q['open'], 'h': q['high'], 'l': q['low'], 'c': q['close'], 'v': q['volume']},
                      index=pd.to_datetime(r['timestamp'], unit='s')).dropna()
    return df


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1.0 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def check(sym):
    df = fetch(sym)
    if len(df) < 60:
        return None
    c, h, l, v = df['c'], df['h'], df['l'], df['v']
    e20, e50 = c.ewm(span=20, adjust=False).mean(), c.ewm(span=50, adjust=False).mean()
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    r = rsi(c).iloc[-1]
    last = c.iloc[-1]
    d3 = (last / c.iloc[-4] - 1) * 100
    d20 = (last / c.iloc[-21] - 1) * 100
    hi52 = h.iloc[-250:].max()
    rv = v.iloc[-1] / v.iloc[-21:-1].mean() if v.iloc[-21:-1].mean() else 1
    bull, bear = [], []
    (bull if last > e20.iloc[-1] else bear).append('close EMA20 %s' % ('upar' if last > e20.iloc[-1] else 'neeche'))
    (bull if e20.iloc[-1] > e50.iloc[-1] else bear).append('EMA20 %s EMA50' % ('>' if e20.iloc[-1] > e50.iloc[-1] else '<'))
    (bull if d20 > 0 else bear).append('20 din %+.1f%%' % d20)
    if last >= 0.95 * hi52:
        bull.append('52w high ke paas (%.1f%%)' % ((last / hi52 - 1) * 100))
    if last < 0.8 * hi52:
        bear.append('52w high se %.0f%% neeche' % ((1 - last / hi52) * 100))
    if r >= 75:
        bear.append('RSI %.0f overbought' % r)
    elif r <= 30:
        bull.append('RSI %.0f oversold (bounce)' % r)
    if rv > 1.5 and last > pc.iloc[-1]:
        bull.append('volume %.1fx + up din' % rv)
    if rv > 1.5 and last < pc.iloc[-1]:
        bear.append('volume %.1fx + down din' % rv)
    tested = []
    if d3 <= -8:
        tested.append('DROP8 (3d %.1f%%)' % d3)
    if r <= 30:
        tested.append('OVERSOLD RSI %.0f' % r)
    stop_pts = 2 * atr
    qty = int(RISK // stop_pts) if stop_pts else 0
    cost = qty * last
    return dict(sym=sym, last=round(last, 2), d3=round(d3, 1), rsi=round(r, 0), bull=bull, bear=bear, tested=tested,
                stop=round(last - stop_pts, 2), qty=qty, cost=round(cost), fits=cost <= CAP * 0.5, score=len(bull) - len(bear))


def main():
    syms = [s.upper() for s in sys.argv[1:]] or DEFAULT
    rows = []
    for s in syms:
        try:
            x = check(s)
            if x:
                rows.append(x)
        except Exception as e:
            print('skip %s: %s' % (s, str(e)[:50]))
    rows.sort(key=lambda x: (-len(x['tested']), -x['score']))
    print('%-11s %9s %6s %4s  %-24s bull/bear  stop(2ATR)  qty(Rs%d risk)' % ('stock', 'close', '3d%', 'RSI', 'tested setup', RISK))
    for x in rows:
        print('%-11s %9.2f %6.1f %4.0f  %-24s %d/%d       %9.2f   %d (~Rs%d)' % (
            x['sym'], x['last'], x['d3'], x['rsi'], ', '.join(x['tested']) or '-', len(x['bull']), len(x['bear']),
            x['stop'], x['qty'], x['cost']))
    flagged = [x for x in rows if x['tested']]
    print('\nTESTED setup wale: %d | sab %d stock' % (len(flagged), len(rows)))
    for x in flagged:
        print('  %s: BULL %s | BEAR %s' % (x['sym'], '; '.join(x['bull']) or '-', '; '.join(x['bear']) or '-'))
    json.dump(rows, open('out/bullbear.json', 'w'), ensure_ascii=False, default=str)


if __name__ == '__main__':
    main()
