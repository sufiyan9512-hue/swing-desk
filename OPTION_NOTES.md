# Option trading notes (13-19 Nov 2026) - Sufiyan, capital Rs50k, risk Rs500-1000/trade

## Tested results (all honest, with costs; mostly NEGATIVE)
- VIX/vega reel rule: FAIL. Option buyers overpay on average (straddle ratio 0.82).
- Strike choice (1 year bhavcopy): ITM has lowest break-even accuracy. 0-2 DTE is far worse; 3-7 DTE best.
- Indicators: 54 single rules + 2-3 combos + ML (logistic/tree/forest) = no robust edge. Walk-forward ~52%. Combos overfit.
- Morning/crude/global cues/gap: predict the GAP only, NOT open->close direction.
- OI max-strike S/R is not special. Writer/PCR signals not predictive.
- PDH/PDL 5-min close break: ~30% win, 63% stop, z +0.8 vs random levels (not different from random).
- Strike filter (delta .5-.75, spread<=2%, cost<=25k, OI/vol) is a liquidity/risk filter, NOT an edge.

## Paper record (out/option_paper.csv)
- 18 Nov: Nifty PE #1 SL, PE #2 SL. 19 Nov: Nifty PE 25200 SL (premium 190 -> 159, SL was 182.3). Total 3 SL, 0 wins.
- Real loss 18 Nov ~Rs5,000; user said "option band", later asked to be told of setups only.

## Rules used in alerts
- Alert only 5-min close beyond previous-day high/low, 9:30-14:45, max 2/day, no chase (>40 pts past trigger = late).
- Premium SL = ask - 500/lot (Nifty lot 65, Sensex 20). Broker SL-L immediately. Entry from 1-min option chart.
- Never place option orders via Kite unless user asks.

## Sources / tools
- Kite MCP (live, no lag): token 256265 NIFTY 50, 265 SENSEX. Yahoo ^BSESN lags ~15 min.
- NSE option-chain-v3 (results_study.nse), bhavcopy F&O archive, Tapetide, NSE live connectors.
- Kite alerts: CE alerts set (Nifty >=25391, Sensex >=82579, 19 Nov). PE alerts failed ("condition already met" bug on index '<' alerts).
- Scripts: opt_pick.py, option_paper.py, chain_snap.py, collect_intraday.py, indicator_study.py, indicator_combo.py, level_break_study.py, index_daily.py.

## Stocks (separate)
- Holdings 19 Nov: SHRINGARMS 47 @248.10 (stop 230.6 daily close, 5-day max), TATASTEEL 50 (exit <170 close), SOBHA 20 @1294.97 (exit <1250 close).
