"""Roz 15:20 IST ka ek Telegram message: holdings ka status + kal ke liye naya swing setup hai ya nahi.
Holdings ki list holdings.json me (qty, avg, stop, time_stop) - badlo jab bhi trade ho.
Use: python3 daily_digest.py           # message print
     python3 daily_digest.py --notify  # Telegram par bhi bhejo
Koi order nahi lagta. Sab kuch checklist hai, tested edge sirf DROP8 / OVERSOLD (HANDOFF)."""
import datetime
import json
import sys

import bullbear

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def build():
    today = datetime.datetime.now(IST).date()
    lines = ['DIGEST %s' % today.strftime('%d %b')]
    hold = json.load(open('holdings.json', encoding='utf-8'))
    pnl = 0.0
    lines.append('HOLDINGS:')
    for hd in hold:
        try:
            x = bullbear.check(hd['sym'])
            last = x['last']
        except Exception:
            lines.append(' %s: data nahi mila' % hd['sym'])
            continue
        p = (last - hd['avg']) * hd['qty']
        pnl += p
        act = 'HOLD'
        if last < hd['stop']:
            act = 'STOP TUTA (close %.0f < %.0f): NIKALO' % (last, hd['stop'])
        elif (last - hd['stop']) / last < 0.02:
            act = 'stop se paas (%.0f), dhyan' % hd['stop']
        if hd.get('time_stop') and hd['time_stop'] <= str(today):
            act = 'TIME STOP aaj/beet gaya: NIKALO' if last >= hd['stop'] else act
        lines.append(' %s %.1f P&L %+.0f -> %s' % (hd['sym'], last, p, act))
    lines.append(' Total %+.0f' % pnl)
    syms = [s for s in bullbear.DEFAULT if s not in [h['sym'] for h in hold]]
    cands = []
    for s in syms:
        try:
            x = bullbear.check(s)
            if x and x['tested']:
                cands.append(x)
        except Exception:
            pass
    lines.append('KAL KA NAYA SETUP:')
    if not cands:
        lines.append(' Koi nahi (tested DROP8/OVERSOLD wala stock nahi). Kuch mat lo.')
    for x in cands:
        lines.append(' %s %.1f %s | stop %.1f | qty %d (~Rs%d)' % (x['sym'], x['last'], ','.join(x['tested']), x['stop'], x['qty'], x['cost']))
        lines.append('   BULL: %s' % '; '.join(x['bull'][:3]))
        lines.append('   BEAR: %s' % '; '.join(x['bear'][:3]))
    lines.append('Order nahi lagta. Risk max Rs800/trade.')
    return '\n'.join(lines)


if __name__ == '__main__':
    msg = build()
    print(msg)
    if '--notify' in sys.argv:
        import live
        url, key = live.page_config()
        print(live.notify(url, key, msg))
