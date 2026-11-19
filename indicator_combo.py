"""2-3 indicator ka mel (combo) agle din ka open->close direction behtar batata hai ya nahi?

Overfit se bachne ke liye:
  * Train = pehle 60% din, Test = baaki 40% (combo train par chuno, test par ek baar check karo)
  * Jitne zyada combo, utna kismat ka chance: isliye 'top-25 train combo ka test accuracy' dekhte hain,
    aur wahi procedure SHUFFLED (nakli) target par bhi chalate hain = chance ka benchmark.
  * Alag se walk-forward ML (logistic, tree, forest): har saal tak ke data par train, agle saal par test.
Run: python3 indicator_combo.py  -> out/indicator_combo.txt
"""
import itertools
import math
import os

import numpy as np
import pandas as pd

import indicator_study as ist

MIN_N = 80


def rules(n):
    S = ist.signals(n)
    keep = {k: v.reindex(n.index).fillna(0).values for k, v in S.items()
            if not k.startswith('ALWAYS') and 'always' not in k}
    return keep


def combos(keep, k):
    """k rules ek hi direction batayein (sab +1 ya sab -1)"""
    names = list(keep)
    M = np.vstack([keep[x] for x in names])
    for idx in itertools.combinations(range(len(names)), k):
        sub = M[list(idx)]
        up = (sub == 1).all(0)
        dn = (sub == -1).all(0)
        s = np.where(up, 1, np.where(dn, -1, 0))
        yield [names[i] for i in idx], s


def score(s, oc, lo, hi):
    m = (s[lo:hi] != 0)
    k = int(m.sum())
    if k < MIN_N:
        return None
    r = oc[lo:hi][m] * s[lo:hi][m]
    acc = float((r > 0).mean())
    return k, acc, float(r.mean() * 100)


def procedure(keep, oc, cut, k, topn=25):
    res = []
    for nm, s in combos(keep, k):
        tr = score(s, oc, 0, cut)
        if tr:
            res.append((tr[1], tr[0], nm, s))
    res.sort(key=lambda x: -x[0])
    out = []
    for acc, kk, nm, s in res[:topn]:
        te = score(s, oc, cut, len(oc))
        out.append((nm, acc, kk, te))
    return out, len(res)


def main():
    n = ist.build().iloc[220:]
    keep = rules(n)
    oc = (n['c'] / n['o'] - 1).values
    cut = int(len(n) * 0.6)
    lines = ['Nifty %s -> %s | train %d din (%s tak), test %d din' % (n.index[0].date(), n.index[-1].date(), cut, n.index[cut - 1].date(), len(n) - cut)]
    rng = np.random.default_rng(7)
    for k in (2, 3):
        out, tot = procedure(keep, oc, cut, k)
        tested = [o for o in out if o[3]]
        tr = np.mean([o[1] for o in tested]) if tested else float('nan')
        te = np.mean([o[3][1] for o in tested]) if tested else float('nan')
        # chance benchmark: target shuffle (din ka order tod do) 5 baar
        nulls = []
        for _ in range(5):
            o2, _t = procedure(keep, rng.permutation(oc), cut, k)
            t2 = [x for x in o2 if x[3]]
            if t2:
                nulls.append((np.mean([x[1] for x in t2]), np.mean([x[3][1] for x in t2])))
        lines.append('\n=== %d-indicator combo (sab ek direction): %d combo me se train par top-25 ===' % (k, tot))
        lines.append('ASLI   : train acc %.1f%% -> TEST acc %.1f%%' % (100 * tr, 100 * te))
        if nulls:
            lines.append('NAKLI(shuffle): train acc %.1f%% -> test acc %.1f%%  (yeh chance ka benchmark hai)' % (
                100 * np.mean([a for a, b in nulls]), 100 * np.mean([b for a, b in nulls])))
        lines.append('%-86s %5s %6s | %5s %6s %7s' % ('combo', 'n_tr', 'acc_tr', 'n_te', 'acc_te', 'mean%te'))
        for nm, acc, kk, te_ in out[:10]:
            lines.append('%-86s %5d %5.1f%% | %5s %5s %7s' % (' + '.join(x[:26] for x in nm), kk, 100 * acc,
                         te_[0] if te_ else '-', '%.1f%%' % (100 * te_[1]) if te_ else '-', '%+.3f' % te_[2] if te_ else '-'))
    # ---- walk-forward ML
    lines.append('\n=== Walk-forward ML (har saal tak ke data par train, agle saal par test) ===')
    X = pd.DataFrame({k: v for k, v in keep.items()}, index=n.index)
    extra = pd.DataFrame({'gap': n['o'] / n['c'].shift(1) - 1, 'ret1': n['c'].pct_change().shift(1),
                          'rsi': ist.rsi(n['c']).shift(1), 'vix': n['vix'].shift(1), 'sp': n['sp']}, index=n.index)
    X = pd.concat([X, extra], axis=1).fillna(0)
    y = (oc > 0).astype(int)
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.pipeline import make_pipeline
    models = {'Logistic': lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=500)),
              'Tree(depth3)': lambda: DecisionTreeClassifier(max_depth=3, min_samples_leaf=60, random_state=1),
              'Forest': lambda: RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=40, random_state=1, n_jobs=2)}
    yrs = sorted(set(n.index.year))
    for nm, mk in models.items():
        hit = tot = 0
        rets = []
        for yr in yrs:
            if yr < 2021:
                continue
            tr = n.index.year < yr
            te = n.index.year == yr
            if te.sum() < 20:
                continue
            m = mk().fit(X[tr], y[tr])
            p = m.predict_proba(X[te])[:, 1]
            sig = np.where(p > 0.55, 1, np.where(p < 0.45, -1, 0))      # sirf confident din
            sel = sig != 0
            r = oc[te][sel] * sig[sel]
            hit += int((r > 0).sum()); tot += int(sel.sum()); rets += list(r)
        if tot:
            acc = hit / tot
            lines.append('%-14s test 2021-26: %d trades (confident), accuracy %.1f%%, mean %+.3f%%/trade, z %+.1f' % (
                nm, tot, 100 * acc, 100 * np.mean(rets), (acc - 0.5) / math.sqrt(0.25 / tot)))
    txt = '\n'.join(lines)
    os.makedirs('out', exist_ok=True)
    open('out/indicator_combo.txt', 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
