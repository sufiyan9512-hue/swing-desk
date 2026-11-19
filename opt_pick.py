"""Best option strike chunna (index ka signal 5-min candle se aata hai; option ka entry/exit user 1-min chart se karta hai).

Use:  python3 opt_pick.py NIFTY CE [expiry DD-Mon-YYYY]    # live NSE chain se top-3 strike
Chunne ka tareeka (sirf liquidity/risk filter, koi tested edge NAHI):
  1. Delta 0.50-0.75, target ~0.65 = 1-2 strike ITM (1 saal ke bhavcopy test me ITM ka break-even accuracy sabse kam, OTM sabse zyada)
  2. Bid-ask spread kam (<=1.5% idea; zyada = 1-min me slippage)
  3. Volume + OI zyada (nikalna aasan)
  4. 1 lot ka premium Rs25k se kam (capital Rs50k), aur Rs500 risk ke liye premium-SL = 500/lot
Sensex: NSE chain me nahi hai; ATM ya 1 strike ITM (step 100) Angel me dekho.
"""
import datetime
import math
import sys

LOT = {'NIFTY': 65, 'BANKNIFTY': 30}
RISK = 500.0
MAX_COST = 25000.0
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(spot, k, t, iv, call):
    """r=0 maan kar delta aur theta(per din, premium points)"""
    if t <= 0 or iv <= 0:
        return None, None
    s = iv * math.sqrt(t)
    d1 = (math.log(spot / k) + 0.5 * iv * iv * t) / s
    d2 = d1 - s
    delta = ncdf(d1) if call else ncdf(d1) - 1
    price = spot * ncdf(d1) - k * ncdf(d2) if call else k * ncdf(-d2) - spot * ncdf(-d1)
    t2 = max(t - 1 / 365.0, 0.0001)
    s2 = iv * math.sqrt(t2)
    d1b = (math.log(spot / k) + 0.5 * iv * iv * t2) / s2
    d2b = d1b - s2
    price2 = spot * ncdf(d1b) - k * ncdf(d2b) if call else k * ncdf(-d2b) - spot * ncdf(-d1b)
    return delta, price - price2


def chain(sym, expiry=None):
    import results_study as r
    q = 'https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=%s' % sym
    if not expiry:
        exps = r.nse('https://www.nseindia.com/api/option-chain-contract-info?symbol=%s' % sym)['expiryDates']
        now = datetime.datetime.now(IST)
        for e in exps:   # pehla expiry jo abhi baaki hai (15:30 IST se pehle)
            if datetime.datetime.strptime(e, '%d-%b-%Y').replace(hour=15, minute=30, tzinfo=IST) > now:
                expiry = e
                break
    d = r.nse(q + '&expiry=' + expiry)['records']
    return d['underlyingValue'], expiry, d['data']


def prev_day_premium(sym, expiry, strike, side):
    """Pichhle trading din ka us option ka O/H/L/C (NSE public bhavcopy). Premium ka apna support/resistance."""
    import io
    import urllib.request
    import zipfile
    d = datetime.date.today()
    for _ in range(6):
        d -= datetime.timedelta(days=1)
        if d.weekday() > 4:
            continue
        u = 'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_%s_F_0000.csv.zip' % d.strftime('%Y%m%d')
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
            t = zipfile.ZipFile(io.BytesIO(b)).read(zipfile.ZipFile(io.BytesIO(b)).namelist()[0]).decode().splitlines()
        except Exception:
            continue
        key = datetime.datetime.strptime(expiry, '%d-%b-%Y').strftime('%Y-%m-%d')
        for line in t:
            if ',%s,' % sym in line and ',IDO,' in line and key in line and (',%.2f,%s,' % (strike, side)) in line:
                p = line.split(',')
                return d, float(p[14]), float(p[15]), float(p[16]), float(p[17])
        return None
    return None


def oi_levels(rows, spot):
    """Option chain ke OI se resistance/support (jaankari; 267 din ke test me khaas level nahi nikle)."""
    ce = sorted(((x['CE']['openInterest'], x['strikePrice']) for x in rows if x.get('CE') and x['strikePrice'] > spot), reverse=True)[:2]
    pe = sorted(((x['PE']['openInterest'], x['strikePrice']) for x in rows if x.get('PE') and x['strikePrice'] < spot), reverse=True)[:2]
    return [k for _, k in ce], [k for _, k in pe]


def writer_view(c):
    """Option sellers (writers) kya kar rahe: premium + OI badlav se. Short build-up = sellers likh rahe (premium neeche, OI upar)."""
    d, p = c.get('doi', 0), c.get('pchg', 0)
    if d > 0 and p < 0:
        t = 'SHORT BUILD-UP: sellers likh rahe (premium gir raha, OI badh raha)'
    elif d > 0 and p >= 0:
        t = 'LONG BUILD-UP: buyers bhi/premium badh raha, OI badh raha'
    elif d < 0 and p >= 0:
        t = 'SHORT COVERING: sellers nikal rahe (premium badh raha, OI ghat raha)'
    elif d < 0 and p < 0:
        t = 'LONG UNWINDING: buyers nikal rahe (premium gir raha, OI ghat raha)'
    else:
        t = 'koi saaf badlav nahi'
    return '%s | OI badlav %+d, premium %+.1f%%' % (t, d, p)


def writing_levels(rows, spot):
    """Aaj sabse zyada call/put OI kahan jud raha (sellers ke level): resistance/support ka sanket."""
    ce = sorted(((x['CE'].get('changeinOpenInterest') or 0, x['strikePrice']) for x in rows if x.get('CE') and spot < x['strikePrice'] <= spot * 1.02), reverse=True)[:2]
    pe = sorted(((x['PE'].get('changeinOpenInterest') or 0, x['strikePrice']) for x in rows if x.get('PE') and spot * 0.98 <= x['strikePrice'] < spot), reverse=True)[:2]
    return ce, pe


def pick(sym='NIFTY', side='CE', expiry=None, topn=3):
    lot = LOT.get(sym, 65)
    spot, expiry, rows = chain(sym, expiry)
    exp_dt = datetime.datetime.strptime(expiry, '%d-%b-%Y').replace(hour=15, minute=30, tzinfo=IST)
    now = datetime.datetime.now(IST)
    days = (exp_dt - now).total_seconds() / 86400.0
    t = max(days, 0.02) / 365.0
    call = side == 'CE'
    cand = []
    for x in rows:
        o = x.get(side)
        if not o or not o.get('lastPrice') or not o.get('buyPrice1') or not o.get('sellPrice1'):
            continue
        k = x['strikePrice']
        if abs(k - spot) > spot * 0.015:
            continue
        iv = (o.get('impliedVolatility') or 0) / 100.0
        delta, theta = bs(spot, k, t, iv, call)
        if delta is None:
            continue
        mid = (o['buyPrice1'] + o['sellPrice1']) / 2
        spread = (o['sellPrice1'] - o['buyPrice1']) / mid * 100 if mid else 99
        cand.append(dict(k=k, ltp=o['lastPrice'], bid=o['buyPrice1'], ask=o['sellPrice1'], spread=spread,
                         vol=o.get('totalTradedVolume') or 0, oi=o.get('openInterest') or 0,
                         doi=o.get('changeinOpenInterest') or 0, pchg=o.get('pChange') or 0,
                         bq1=o.get('buyQuantity1') or 0, sq1=o.get('sellQuantity1') or 0,
                         tbq=o.get('totalBuyQuantity') or 0, tsq=o.get('totalSellQuantity') or 0,
                         delta=abs(delta), theta=abs(theta or 0), iv=iv * 100))
    if not cand:
        return spot, expiry, days, []
    mv = max(c['vol'] for c in cand) or 1
    for c in cand:
        c['cost'] = c['ask'] * lot
        ok = 0.50 <= c['delta'] <= 0.75 and c['spread'] <= 2.0 and c['cost'] <= MAX_COST
        liq = 0.6 * c['vol'] / mv + 0.4 * min(c['oi'] / 100000.0, 1)
        c['score'] = (0.45 * liq + 0.30 * max(0, 1 - c['spread'] / 2.0) + 0.25 * max(0, 1 - abs(c['delta'] - 0.65) / 0.25)) if ok else -1
        c['sl_prem'] = round(c['ask'] - RISK / lot, 2)                  # premium-SL: 1 lot me ~Rs500 nuksaan
        c['sl_idx_pts'] = round((RISK / lot) / max(c['delta'], 0.05), 1)  # itna index move ulta = SL
        c['theta_hr'] = round(c['theta'] / 6.25, 2)                     # approx premium points / ghanta
    cand.sort(key=lambda c: -c['score'])
    return spot, expiry, days, [c for c in cand if c['score'] > 0][:topn]


def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 else 'NIFTY').upper()
    side = (sys.argv[2] if len(sys.argv) > 2 else 'CE').upper()
    exp = sys.argv[3] if len(sys.argv) > 3 else None
    spot, expiry, days, top = pick(sym, side, exp)
    print('%s %s spot %.1f expiry %s (%.1f din)' % (sym, side, spot, expiry, days))
    if days < 3:
        print('NOTE: expiry me %.1f din hi bache. Test me 0-2 din ke option me jeetne ke liye 56-69%% sahi direction chahiye (3-7 din me ~49%%). Agla expiry ya chhota size.' % days)
    try:
        _sp, _e, _rows = chain(sym, expiry or None)
        res_, sup_ = oi_levels(_rows, spot)
        wce, wpe = writing_levels(_rows, spot)
        print('SELLERS aaj kahan likh rahe: call writing (resistance) %s | put writing (support) %s  [test me next-day direction nahi bataya: jaankari]' % ([(int(k), int(d)) for d, k in wce], [(int(k), int(d)) for d, k in wpe]))
        print('OI levels (info): resistance (zyada call OI) %s | support (zyada put OI) %s  -- test me ye khaas S/R nahi nikle, index S/R ke saath dekho' % (res_, sup_))
    except Exception:
        pass
    for c in top:
        pv = None
        try:
            pv = prev_day_premium(sym, expiry, c['k'], side)
        except Exception:
            pass
        print('%d %s  LTP %.1f bid/ask %.1f/%.1f spread %.1f%%  delta %.2f  vol %d OI %d  IV %.1f  1lot cost Rs%d  SL premium %.1f (~%s index pts)  theta/hr ~%.1f' % (
            c['k'], side, c['ltp'], c['bid'], c['ask'], c['spread'], c['delta'], c['vol'], c['oi'], c['iv'],
            c['cost'], c['sl_prem'], c['sl_idx_pts'], c['theta_hr']))
        print('   seller view: ' + writer_view(c))
        b1, s1_ = c.get('bq1', 0), c.get('sq1', 0)
        if b1 and s1_:
            print('   buyer/seller: best bid qty %d vs best ask qty %d (%.1fx %s) | total buy %d vs sell %d (%.1fx %s)  [jaankari: test nahi hua; total me door ke lottery orders bhi hote hain]' % (
                b1, s1_, max(b1 / s1_, s1_ / b1), 'BUYER bhaari' if b1 > s1_ else 'SELLER bhaari',
                c.get('tbq', 0), c.get('tsq', 0), max(c.get('tbq', 1) / max(c.get('tsq', 1), 1), c.get('tsq', 1) / max(c.get('tbq', 1), 1)),
                'BUYER' if c.get('tbq', 0) > c.get('tsq', 0) else 'SELLER'))
        if pv:
            print('   premium pichhla din (%s): open %.1f high %.1f low %.1f close %.1f  (premium ka resistance/support)' % (pv[0], pv[1], pv[2], pv[3], pv[4]))
    if not top:
        print('Koi strike filter pass nahi (market band / liquidity kam).')


if __name__ == '__main__':
    main()
