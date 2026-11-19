"""Nifty ke liye indicator study: kaun sa indicator/rule agle din ka open->close direction sabse sahi batata hai?

Option buyer ka sawal: subah open par CE ya PE? Isliye target = agle din ka open->close.
Har rule sirf pichhle din tak ka data + aaj ka open use karta hai (koi aage ki jhalak nahi).
~55 rules test hote hain, to Bonferroni (p < 0.05/55) lagta hai, aur dono aadhe saal me tikna chahiye.

Run: python3 indicator_study.py   -> out/indicator_study.txt
"""
import datetime
import json
import math
import os
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def yahoo(sym, rng='10y'):
    u = 'https://query2.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d' % (urllib.parse.quote(sym), rng)
    res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read().decode())['chart']['result'][0]
    q = res['indicators']['quote'][0]
    idx = [datetime.datetime.fromtimestamp(t, IST).date() for t in res['timestamp']]
    return pd.DataFrame({'o': q['open'], 'h': q['high'], 'l': q['low'], 'c': q['close']}, index=pd.to_datetime(idx)).dropna()


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def build():
    n = yahoo('^NSEI')
    v = yahoo('^INDIAVIX')['c'].rename('vix')
    s = yahoo('^GSPC')['c']
    n = n.join(v, how='left')
    n['vix'] = n['vix'].ffill()
    # S&P ka pichhla US session = raat ka move (Nifty din D se pehle)
    sr = s.pct_change()
    n['sp'] = [sr[sr.index < d].iloc[-1] if (sr.index < d).any() else np.nan for d in n.index]
    return n


def signals(n):
    """Har rule: Series of +1 (CE), -1 (PE), 0 (no trade) jo din D ke liye hai, sirf D-1 tak ka data + D ka open."""
    c, h, l, o = n['c'], n['h'], n['l'], n['o']
    P = {}                                   # pichhle din ki cheezein (shift(1)), 'open' aaj ka
    sma = lambda k: c.rolling(k).mean()
    ema = lambda k: c.ewm(span=k, adjust=False).mean()
    pc = c.shift(1)
    rs = rsi(c)
    macd = ema(12) - ema(26)
    mh = macd - macd.ewm(span=9, adjust=False).mean()
    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    stoch = 100 * (c - ll) / (hh - ll)
    bb_m, bb_s = c.rolling(20).mean(), c.rolling(20).std()
    pb = (c - (bb_m - 2 * bb_s)) / (4 * bb_s)
    roc5 = c.pct_change(5)
    ret1 = c.pct_change()
    gap = o / pc - 1
    rng = (h - l)
    pos = (c - l) / rng.replace(0, np.nan)                 # pichhle din close range me kahan
    piv = (h + l + c) / 3
    r1, s1 = 2 * piv - l, 2 * piv - h
    don_hi, don_lo = h.rolling(20).max(), l.rolling(20).min()
    nr7 = rng == rng.rolling(7).min()
    vix, vch = n['vix'], n['vix'].pct_change()
    vhi = vix > vix.rolling(250).quantile(0.8)
    sp = n['sp']
    inside = (h < h.shift(1)) & (l > l.shift(1))
    bull_eng = (c > o) & (c.shift(1) < o.shift(1)) & (c > o.shift(1)) & (o < c.shift(1))
    bear_eng = (c < o) & (c.shift(1) > o.shift(1)) & (c < o.shift(1)) & (o > c.shift(1))
    d3dn = (ret1 < 0) & (ret1.shift(1) < 0) & (ret1.shift(2) < 0)
    d3up = (ret1 > 0) & (ret1.shift(1) > 0) & (ret1.shift(2) > 0)
    cross_up = (mh > 0) & (mh.shift(1) <= 0)
    cross_dn = (mh < 0) & (mh.shift(1) >= 0)
    S = {}

    def sgn(cond_long, cond_short=None):
        out = pd.Series(0, index=n.index)
        out[cond_long.fillna(False).astype(bool)] = 1
        if cond_short is not None:
            out[cond_short.fillna(False).astype(bool)] = -1
        return out
    # --- trend
    S['C>SMA20 (long) / C<SMA20 (short)'] = sgn(c > sma(20), c < sma(20)).shift(1)
    S['C>SMA50'] = sgn(c > sma(50), c < sma(50)).shift(1)
    S['C>SMA200'] = sgn(c > sma(200), c < sma(200)).shift(1)
    S['SMA20>SMA50'] = sgn(sma(20) > sma(50), sma(20) < sma(50)).shift(1)
    S['EMA9>EMA21'] = sgn(ema(9) > ema(21), ema(9) < ema(21)).shift(1)
    # --- momentum
    S['RSI14>50 trend'] = sgn(rs > 50, rs < 50).shift(1)
    S['RSI14<30 long (bounce)'] = sgn(rs < 30).shift(1)
    S['RSI14>70 short (fade)'] = sgn(rs > 70 * 0 + 9999, rs > 70).shift(1)
    S['RSI14<30 short (trend)'] = sgn(rs > 9999, rs < 30).shift(1)
    S['RSI14>70 long (trend)'] = sgn(rs > 70).shift(1)
    S['MACD hist>0 trend'] = sgn(mh > 0, mh < 0).shift(1)
    S['MACD cross up long / down short'] = sgn(cross_up, cross_dn).shift(1)
    S['Stoch<20 long / >80 short (fade)'] = sgn(stoch < 20, stoch > 80).shift(1)
    S['ROC5>0 momentum'] = sgn(roc5 > 0, roc5 < 0).shift(1)
    S['ROC5 contrarian'] = sgn(roc5 < 0, roc5 > 0).shift(1)
    S['prev day up -> long (continue)'] = sgn(ret1 > 0, ret1 < 0).shift(1)
    S['prev day up -> short (reverse)'] = sgn(ret1 < 0, ret1 > 0).shift(1)
    S['3 down days long / 3 up days short'] = sgn(d3dn, d3up).shift(1)
    # --- volatility
    S['Bollinger %B<0 long / >1 short (fade)'] = sgn(pb < 0, pb > 1).shift(1)
    S['Bollinger breakout trend'] = sgn(pb > 1, pb < 0).shift(1)
    S['VIX jumped >5% -> long (rebound)'] = sgn(vch > 0.05).shift(1)
    S['VIX jumped >5% -> short'] = sgn(vch > 9, vch > 0.05).shift(1)
    S['VIX high (top20%) -> long'] = sgn(vhi).shift(1)
    S['NR7 day: follow gap'] = sgn(nr7.shift(1) & (gap > 0), nr7.shift(1) & (gap < 0))
    # --- gap / open
    S['gap>0.3% follow, <-0.3% follow'] = sgn(gap > 0.003, gap < -0.003)
    S['gap>0.3% fade, <-0.3% fade'] = sgn(gap < -0.003, gap > 0.003)
    S['open>prev high -> long'] = sgn(o > h.shift(1))
    S['open>prev high -> short (fade)'] = sgn(o < l.shift(1), o > h.shift(1))
    S['open<prev low -> short'] = sgn(o > 9e9, o < l.shift(1))
    S['open>pivot long / <pivot short'] = sgn(o > piv.shift(1), o < piv.shift(1))
    S['open>R1 fade short / <S1 fade long'] = sgn(o < s1.shift(1), o > r1.shift(1))
    S['open>R1 trend long / <S1 trend short'] = sgn(o > r1.shift(1), o < s1.shift(1))
    # --- candle
    S['prev close top25% -> long'] = sgn(pos.shift(1) > 0.75)
    S['prev close top25% -> short (fade)'] = sgn(pos.shift(1) < -9, pos.shift(1) > 0.75)
    S['prev close bottom25% -> short'] = sgn(pos.shift(1) < -9, pos.shift(1) < 0.25)
    S['prev close bottom25% -> long (fade)'] = sgn(pos.shift(1) < 0.25)
    S['bull engulf long / bear engulf short'] = sgn(bull_eng.shift(1), bear_eng.shift(1))
    S['inside day: follow gap'] = sgn(inside.shift(1) & (gap > 0), inside.shift(1) & (gap < 0))
    # --- breakout
    S['close>20d high long / <20d low short'] = sgn(c >= don_hi, c <= don_lo).shift(1)
    S['20d breakout fade'] = sgn(c <= don_lo, c >= don_hi).shift(1)
    # --- global
    S['S&P>+0.5% long / < -0.5% short'] = sgn(sp > 0.005, sp < -0.005)
    S['S&P>+0.5% short / < -0.5% long (fade)'] = sgn(sp < -0.005, sp > 0.005)
    S['S&P>+1% long'] = sgn(sp > 0.01)
    S['S&P<-1% short'] = sgn(sp > 9, sp < -0.01)
    # --- calendar
    wd = pd.Series(n.index.weekday, index=n.index)
    for k, nm in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri']):
        S['%s always long' % nm] = sgn(wd == k)
        S['%s always short' % nm] = sgn(wd > 9, wd == k)
    S['ALWAYS long (open buy)'] = sgn(pd.Series(True, index=n.index))
    S['ALWAYS short (open PE)'] = sgn(pd.Series(False, index=n.index), pd.Series(True, index=n.index))
    return S


def evaluate(S, n, lo=None, hi=None):
    oc = (n['c'] / n['o'] - 1)
    rows = []
    for nm, sig in S.items():
        s = sig.reindex(n.index).fillna(0)
        m = (s != 0) & oc.notna()
        if lo is not None:
            m &= n.index >= lo
        if hi is not None:
            m &= n.index < hi
        k = int(m.sum())
        if k < 40:
            continue
        r = (oc[m] * s[m])
        acc = float((r > 0).mean())
        z = (acc - 0.5) / math.sqrt(0.25 / k)
        rows.append(dict(rule=nm, n=k, acc=acc, mean=float(r.mean() * 100), t=float(r.mean() / (r.std() / math.sqrt(k))), z=z))
    return pd.DataFrame(rows)


def main():
    n = build()
    n = n.iloc[220:]
    S = signals(n)
    mid = n.index[len(n) // 2]
    full = evaluate(S, n)
    a, b = evaluate(S, n, hi=mid).set_index('rule'), evaluate(S, n, lo=mid).set_index('rule')
    full = full.set_index('rule').join(a[['n', 'acc']].add_suffix('_h1')).join(b[['n', 'acc']].add_suffix('_h2'))
    M = len(full)
    thr = 3.3
    full = full.sort_values('acc', ascending=False)
    out = []
    out.append('Nifty %s se %s (%d din), %d rules, open->close, entry open par' % (n.index[0].date(), n.index[-1].date(), len(n), M))
    out.append('Bonferroni z-threshold ~%.1f (p<0.05/%d). 50%% = sikka, option break-even ~51-56%% (pehle wale test se)' % (thr, M))
    out.append('%-44s %5s %6s %7s %6s %5s   %6s %6s' % ('rule', 'n', 'acc%', 'mean%', 't', 'z', 'acc h1', 'acc h2'))
    for nm, r in full.iterrows():
        flag = ' <== PASS' if (abs(r['z']) >= thr and r['acc_h1'] > 0.5 and r['acc_h2'] > 0.5 and r['acc'] > 0.5) else ''
        out.append('%-44s %5d %5.1f %+6.3f %+5.1f %+5.1f   %5.1f %5.1f%s' % (nm, r['n'], 100 * r['acc'], r['mean'], r['t'], r['z'], 100 * r['acc_h1'], 100 * r['acc_h2'], flag))
    txt = '\n'.join(out)
    os.makedirs('out', exist_ok=True)
    open('out/indicator_study.txt', 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
