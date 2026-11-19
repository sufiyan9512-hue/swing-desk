"""Test: pichhle din ke High/Low ke paar 5-min CLOSE par entry (jo rule abhi alerts me chal raha hai).
Entry = pehla 5-min close level ke paar (9:30-14:25). Stop = 5-min close wapas level ke ander. Exit = stop ya din ka aakhri close (15:25).
Control = wahi procedure NAKLI levels par (asli level se +-0.3% / +-0.6% shift). Asli level me koi khaas baat ho to control se behtar dikhna chahiye.
Data: data/intraday/*_5m.csv.gz (Yahoo ~60 din). Run: python3 level_break_study.py -> out/level_break_study.txt
"""
import collections
import gzip
import math
import os
import statistics as st

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'intraday')


def load(name):
    days = collections.OrderedDict()
    with gzip.open(os.path.join(D, name + '_5m.csv.gz'), 'rt') as h:
        next(h)
        for line in h:
            ts, o, hh, l, c, v = line.strip().split(',')
            d, t = ts.split(' ')
            m = int(t[:2]) * 60 + int(t[3:5])
            days.setdefault(d, []).append((m, float(o), float(hh), float(l), float(c)))
    return days


def run(bars, level, up):
    """up=True: CE (close level ke upar); up=False: PE. Return (ret%, mfe%, stopped) ya None"""
    ent = None
    for i, (m, o, h, l, c) in enumerate(bars):
        if m < 9 * 60 + 30 or m > 14 * 60 + 25:
            continue
        if (c > level) if up else (c < level):
            ent = i
            break
    if ent is None:
        return None
    e = bars[ent][4]
    mfe = 0.0
    for j in range(ent + 1, len(bars)):
        m, o, h, l, c = bars[j]
        fav = (h - e) / e if up else (e - l) / e
        mfe = max(mfe, fav)
        if (c < level) if up else (c > level):     # wapas level ke ander = stop
            ex = c
            return ((ex - e) / e if up else (e - ex) / e) * 100, mfe * 100, True
    ex = bars[-1][4]
    return ((ex - e) / e if up else (e - ex) / e) * 100, mfe * 100, False


def study(names):
    real, ctrl = [], []
    for nm in names:
        days = load(nm)
        ks = list(days)
        for i in range(1, len(ks)):
            pb, b = days[ks[i - 1]], days[ks[i]]
            if len(pb) < 70 or len(b) < 70:
                continue
            H = max(x[2] for x in pb)
            L = min(x[3] for x in pb)
            for up, lv in ((True, H), (False, L)):
                r = run(b, lv, up)
                if r:
                    real.append(r)
                for sh in (-0.006, -0.003, 0.003, 0.006):
                    r2 = run(b, lv * (1 + sh), up)
                    if r2:
                        ctrl.append(r2)
    return real, ctrl


def rep(name, rows):
    n = len(rows)
    ret = [r[0] for r in rows]
    win = sum(1 for x in ret if x > 0) / n
    stp = sum(1 for r in rows if r[2]) / n
    m25 = sum(1 for r in rows if r[1] >= 0.25) / n
    m40 = sum(1 for r in rows if r[1] >= 0.40) / n
    mean = st.mean(ret)
    se = st.pstdev(ret) / math.sqrt(n)
    return '%-34s n=%3d  jeet %.0f%%  avg %+.3f%% (se %.3f)  stop hit %.0f%%  MFE>=0.25%%: %.0f%%  MFE>=0.40%%: %.0f%%' % (name, n, 100 * win, mean, se, 100 * stp, 100 * m25, 100 * m40)


def main():
    out = []
    for label, names in (('NIFTY', ['NIFTY']), ('SENSEX', ['SENSEX']), ('BANKNIFTY', ['BANKNIFTY']), ('SAB (3 index)', ['NIFTY', 'SENSEX', 'BANKNIFTY'])):
        real, ctrl = study(names)
        out.append('== %s' % label)
        out.append(rep('ASLI level (PDH/PDL break)', real))
        out.append(rep('CONTROL (nakli levels)', ctrl))
        d = st.mean(r[0] for r in real) - st.mean(r[0] for r in ctrl)
        se = math.sqrt((st.pstdev([r[0] for r in real]) ** 2) / len(real) + (st.pstdev([r[0] for r in ctrl]) ** 2) / len(ctrl))
        out.append('   faraq (asli - control) avg %+.3f%%, z %+.1f' % (d, d / se))
    txt = '\n'.join(out)
    os.makedirs('out', exist_ok=True)
    open('out/level_break_study.txt', 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
