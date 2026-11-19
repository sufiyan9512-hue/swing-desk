"""docs/index.html me 'Aaj ka index' card jodta hai (ek baar; dobara chalane par kuch nahi karta)."""
p = 'docs/index.html'
s = open(p, encoding='utf-8').read()
if 'function idxCard' in s:
    print('already patched'); raise SystemExit
CARD = '/* Roz ka index analysis: Som/Mangal/Shukra Nifty, Budh/Guru Sensex (index_daily.py -> index_daily.json). Levels hain, tested signal nahi. */\nfunction idxCard(){var d=IXD;if(!d||!d.main)return \'\';var m=d.main,r=m.ref,n=function(v){return v==null?\'-\':Math.round(v).toLocaleString(\'en-IN\')};\nvar tr=m.score>=3?\'pg\':m.score<=-3?\'pr\':\'py\';\nvar h=\'<div class="card"><h2>\'+d.weekday+\' (\'+d.target_date.slice(8)+\'/\'+d.target_date.slice(5,7)+\') &ndash; \'+m.name+\'</h2>\';\nh+=\'<div>Pichhla close <b>\'+n(r.c)+\'</b> (\'+(m.chg1>=0?\'+\':\'\')+m.chg1+\'%) &middot; trend <span class="\'+tr+\'">\'+m.trend+\'</span>\'+(d.vix?\' &middot; VIX \'+d.vix:\'\')+\'</div>\';\nh+=\'<table style="width:100%;margin-top:6px;font-size:13px"><tr><th>S2</th><th>S1</th><th>Pivot</th><th>R1</th><th>R2</th></tr><tr style="text-align:center"><td>\'+n(m.s2)+\'</td><td>\'+n(m.s1)+\'</td><td><b>\'+n(m.pivot)+\'</b></td><td>\'+n(m.r1)+\'</td><td>\'+n(m.r2)+\'</td></tr></table>\';\nh+=\'<div style="margin-top:6px"><b>CE:</b> 5-min close <b>\'+n(m.ce_trigger)+\'</b> ke upar &middot; stop close \'+n(m.ce_stop)+\' ke neeche &middot; T1 \'+n(m.ce_t1)+\'<br><b>PE:</b> 5-min close <b>\'+n(m.pe_trigger)+\'</b> ke neeche &middot; stop close \'+n(m.pe_stop)+\' ke upar &middot; T1 \'+n(m.pe_t1)+\'</div>\';\nh+=\'<div style="margin-top:6px;font-size:12px;opacity:.85">ATR14 \'+n(m.atr14)+(m.exp_move?\' &middot; VIX ka 1-din move &plusmn;\'+n(m.exp_move):\'\')+\' &middot; 20DMA \'+n(m.m20)+\' &middot; ATM \'+n(m.atm)+\'<br>1 lot (\'+m.lot+\') me &#8377;500 risk = premium ka max nuksaan ~&#8377;\'+m.max_prem_loss+\' (lot size confirm karo)</div>\';\nif(m.expiry_day)h+=\'<div class="r" style="margin-top:6px"><b>Aaj \'+m.name+\' expiry (\'+m.expiry+\')</b>: theta tez, chhota size.</div>\';\nh+=\'<div style="margin-top:6px;font-size:12px;opacity:.7">Levels hain, tested signal nahi. 9:15-9:30 sirf dekho, 14:45 ke baad naya entry nahi. \'+d.updated+\'</div></div>\';return h}\n'
def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)
rep("get('regime_today.json',1)]).then(function(a){", "get('regime_today.json',1),get('index_daily.json',1)]).then(function(a){IXD=a[18]||null;")
rep("RG=null,RT=null,DPM={}", "RG=null,RT=null,IXD=null,DPM={}")
rep("else if(k=='mkt'){h+=mktCard()+", "else if(k=='mkt'){h+=idxCard()+mktCard()+")
rep("function mktCard(){", CARD + "function mktCard(){")
open(p, 'w', encoding='utf-8').write(s)
print('patched')
