"""Roz ka index analysis: Somvar/Mangalvar/Shukravar = NIFTY 50, Budhvar/Guruvar = SENSEX.

Subah (9:00 IST) = aaj ka plan. Shaam (15:45 IST ke baad) = agle trading din ka plan.
Output: docs/index_daily.json (app ka 'Aaj ka index' card) + optional Telegram (--notify).

NOTE: Yeh LEVELS aur description hain. Koi tested entry signal NAHI hai (scalping/ORB/OI studies me
koi rule pass nahi hua). Entry ka rule sirf: 5-min candle CLOSE, stop bhi 5-min close par.
"""
import datetime
import json
import math
import os
import sys
import urllib.parse
import urllib.request

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
# weekday(): Mon=0 ... Sun=6
PLAN = {0: 'NIFTY', 1: 'NIFTY', 2: 'SENSEX', 3: 'SENSEX', 4: 'NIFTY'}
IDX = {
    'NIFTY': dict(sym='^NSEI', name='Nifty 50', step=50, lot=65, expiry_wd=1, expiry_name='Mangalvar',
                  note='Weekly expiry Mangalvar'),
    'SENSEX': dict(sym='^BSESN', name='Sensex', step=100, lot=20, expiry_wd=3, expiry_name='Guruvar',
                   note='Weekly expiry Guruvar'),
}
WD = ['Somvar', 'Mangalvar', 'Budhvar', 'Guruvar', 'Shukravar', 'Shanivar', 'Ravivar']


def fetch(sym, rng='1y', itv='1d'):
    url = 'https://query2.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=%s' % (
        urllib.parse.quote(sym), rng, itv)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())['chart']['result'][0]
    q = res['indicators']['quote'][0]
    out = []
    for i, t in enumerate(res['timestamp']):
        if q['close'][i] is None or q['open'][i] is None:
            continue
        d = datetime.datetime.fromtimestamp(t, IST)
        out.append(dict(dt=d, o=q['open'][i], h=q['high'][i], l=q['low'][i], c=q['close'][i]))
    return out


def next_trading_day(d):
    d += datetime.timedelta(days=1)
    while d.weekday() > 4:
        d += datetime.timedelta(days=1)
    return d


def target_date(now):
    """Market khulne se pehle / ke dauran = aaj; 15:35 ke baad = agla trading din."""
    d = now.date()
    after = now.hour * 60 + now.minute >= 15 * 60 + 35
    if d.weekday() > 4 or after:
        return next_trading_day(d)
    return d


def sma(v, n):
    return sum(v[-n:]) / n if len(v) >= n else None


def analyse(key, now, tgt, vix):
    cfg = IDX[key]
    bars = fetch(cfg['sym'])
    # sirf poore ho chuke din (aaj ka adhura bar hata do)
    live_today = None
    if bars and bars[-1]['dt'].date() == now.date() and now.hour * 60 + now.minute < 15 * 60 + 35:
        live_today = bars[-1]
        bars = bars[:-1]
    if len(bars) < 60:
        raise RuntimeError('data kam')
    ref = bars[-1]
    closes = [b['c'] for b in bars]
    H, L, C = ref['h'], ref['l'], ref['c']
    P = (H + L + C) / 3
    r1, s1 = 2 * P - L, 2 * P - H
    r2, s2 = P + (H - L), P - (H - L)
    trs = []
    for i in range(len(bars) - 14, len(bars)):
        pc = bars[i - 1]['c']
        trs.append(max(bars[i]['h'] - bars[i]['l'], abs(bars[i]['h'] - pc), abs(bars[i]['l'] - pc)))
    atr = sum(trs) / 14
    m20, m50, m200 = sma(closes, 20), sma(closes, 50), sma(closes, 200)
    m20_prev = sum(closes[-25:-5]) / 20
    hi20 = max(b['h'] for b in bars[-20:])
    lo20 = min(b['l'] for b in bars[-20:])
    hi52 = max(b['h'] for b in bars[-250:])
    lo52 = min(b['l'] for b in bars[-250:])
    ret5 = (C / bars[-6]['c'] - 1) * 100
    ret20 = (C / bars[-21]['c'] - 1) * 100
    prev = bars[-2]
    chg1 = (C / prev['c'] - 1) * 100
    # trend ka score (sirf description)
    sc = 0
    sc += 1 if C > m20 else -1
    sc += 1 if m20 > m50 else -1
    sc += 1 if m20 > m20_prev else -1
    sc += 1 if C > P else -1
    if m200:
        sc += 1 if C > m200 else -1
    if sc >= 3:
        trend = 'UPAR (uptrend)'
    elif sc <= -3:
        trend = 'NEECHE (downtrend)'
    else:
        trend = 'SIDEWAYS / mixed'
    em = C * (vix / 100) / math.sqrt(252) if vix else None   # VIX se 1-din ka expected move
    step = cfg['step']
    atm = int(round(C / step) * step)
    days_to_exp = (cfg['expiry_wd'] - tgt.weekday()) % 7
    exp_today = days_to_exp == 0
    out = dict(
        key=key, name=cfg['name'], ref_date=ref['dt'].strftime('%Y-%m-%d'),
        ref=dict(o=round(ref['o'], 1), h=round(H, 1), l=round(L, 1), c=round(C, 1)),
        chg1=round(chg1, 2), ret5=round(ret5, 2), ret20=round(ret20, 2),
        pivot=round(P, 1), r1=round(r1, 1), r2=round(r2, 1), s1=round(s1, 1), s2=round(s2, 1),
        atr14=round(atr, 1), m20=round(m20, 1), m50=round(m50, 1), m200=round(m200, 1) if m200 else None,
        hi20=round(hi20, 1), lo20=round(lo20, 1), hi52=round(hi52, 1), lo52=round(lo52, 1),
        trend=trend, score=sc, atm=atm, step=step, lot=cfg['lot'],
        expiry=cfg['expiry_name'], days_to_expiry=days_to_exp, expiry_day=exp_today,
        exp_move=round(em, 1) if em else None,
        max_prem_loss=round(500.0 / cfg['lot'], 1),   # Rs500 risk / lot size = ek lot me premium ka max nuksaan
    )
    # trigger levels: pichhle din ka high/low (5-min CLOSE chahiye)
    out['ce_trigger'] = round(H, 1)
    out['pe_trigger'] = round(L, 1)
    out['ce_stop'] = round(max(P, H - 0.35 * atr), 1)    # 5-min close is se neeche = CE galat
    out['pe_stop'] = round(min(P, L + 0.35 * atr), 1)
    out['ce_t1'], out['ce_t2'] = round(r1, 1), round(r2, 1)
    out['pe_t1'], out['pe_t2'] = round(s1, 1), round(s2, 1)
    if live_today:
        out['live'] = dict(o=round(live_today['o'], 1), h=round(live_today['h'], 1),
                           l=round(live_today['l'], 1), c=round(live_today['c'], 1),
                           gap=round((live_today['o'] / C - 1) * 100, 2))
    return out


def vix_now():
    try:
        b = fetch('^INDIAVIX', '1mo')
        return round(b[-1]['c'], 2), round((b[-1]['c'] / b[-2]['c'] - 1) * 100, 1)
    except Exception:
        return None, None


def lines_for(m, tgt):
    k = m['name']
    s = []
    s.append('%s %s (%s): pichhla close %.0f (%+.2f%%), trend %s.' % (
        WD[tgt.weekday()], tgt.strftime('%d %b'), k, m['ref']['c'], m['chg1'], m['trend']))
    s.append('Levels: S2 %.0f | S1 %.0f | Pivot %.0f | R1 %.0f | R2 %.0f' % (m['s2'], m['s1'], m['pivot'], m['r1'], m['r2']))
    s.append('CE tab: 5-min close %.0f ke upar (stop close %.0f ke neeche, T1 %.0f). PE tab: 5-min close %.0f ke neeche (stop close %.0f ke upar, T1 %.0f).' % (
        m['ce_trigger'], m['ce_stop'], m['ce_t1'], m['pe_trigger'], m['pe_stop'], m['pe_t1']))
    if m.get('exp_move'):
        s.append('VIX ke hisaab se 1-din ka expected move ~±%.0f points (ATR14 %.0f).' % (m['exp_move'], m['atr14']))
    s.append('1 lot (%d) me Rs500 risk = option premium ka max nuksaan ~Rs%.1f. ATM strike %d.' % (m['lot'], m['max_prem_loss'], m['atm']))
    if m['expiry_day']:
        s.append('AAJ EXPIRY (%s): theta tez, premium jaldi 0 ho sakta hai. Chhota size.' % m['expiry'])
    s.append('Levels hain, tested signal nahi. 9:15-9:30 sirf dekho; 14:45 ke baad naya entry nahi.')
    return s


def main():
    notify = '--notify' in sys.argv
    now = datetime.datetime.now(IST)
    tgt = target_date(now)
    key = PLAN[tgt.weekday()]
    vix, vchg = vix_now()
    res = dict(updated=now.strftime('%Y-%m-%d %H:%M IST'), target_date=tgt.strftime('%Y-%m-%d'),
               weekday=WD[tgt.weekday()], index=key, vix=vix, vix_chg=vchg, errors=[])
    for k in IDX:
        try:
            res['main' if k == key else 'other'] = analyse(k, now, tgt, vix)
        except Exception as e:
            res['errors'].append('%s: %s' % (k, str(e)[:80]))
    if 'main' not in res:
        print('main fail:', res['errors'])
        sys.exit(1)
    res['text'] = lines_for(res['main'], tgt)
    os.makedirs('docs', exist_ok=True)
    with open('docs/index_daily.json', 'w', encoding='utf-8') as h:
        json.dump(res, h, ensure_ascii=False)
    print('\n'.join(res['text']))
    print('VIX', vix, vchg, '| other:', res.get('other', {}).get('name'), res['errors'])
    if notify:
        try:
            import live
            url, pkey = live.page_config()
            txt = 'AAJ KA INDEX: ' + ' '.join(res['text'][:4])
            ok, why = live.notify(url, pkey, txt)
            print('notify', ok, why)
        except Exception as e:
            print('notify fail', str(e)[:80])


if __name__ == '__main__':
    main()
