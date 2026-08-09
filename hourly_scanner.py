"""
Hourly stock scanner — pulls real quotes and scores them the same way
as the dashboard's composite score (momentum + relative volume + RSI
sweet-spot + MACD + trend).

Requires: pip install yfinance pandas
Run on a schedule (cron / Task Scheduler) at your desired interval, e.g.:
    0 * * * * /usr/bin/python3 /path/to/hourly_scanner.py >> scanner.log 2>&1

Writes results to scanner_output.json each run, which you can point a
real dashboard at (e.g. serve it and fetch() it from a hosted version
of the artifact, or feed it into your own backend).
"""

import json
import datetime
import yfinance as yf
import pandas as pd

TICKERS = ['AAPL', 'MSFT', 'GOOG', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'BRK.B', 'JPM', 'V', 'MA', 'UNH', 'LLY', 'XOM', 'JNJ', 'PG', 'HD', 'MRK', 'ABBV', 'CVX', 'COST', 'PEP', 'KO', 'ADBE', 'WMT', 'CRM', 'BAC', 'MCD', 'CSCO', 'NFLX', 'TMO', 'ACN', 'ABT', 'LIN', 'DIS', 'AMD', 'DHR', 'WFC', 'TXN', 'PM', 'VZ', 'NEE', 'INTU', 'CMCSA', 'ORCL', 'IBM', 'QCOM', 'AMGN', 'HON', 'UPS', 'CAT', 'LOW', 'SPGI', 'INTC', 'BA', 'GE', 'PLD', 'AMAT', 'UNP', 'SBUX', 'GS', 'RTX', 'BKNG', 'ELV', 'DE', 'MDT', 'BLK', 'ADI', 'ISRG', 'GILD', 'LRCX', 'MMC', 'SYK', 'AXP', 'VRTX', 'CVS', 'C', 'PANW', 'CB', 'REGN', 'MU', 'ADP', 'TJX', 'ETN', 'FI', 'ZTS', 'SLB', 'SO', 'CI', 'BSX', 'MO', 'PYPL', 'SCHW', 'DUK', 'PGR', 'EOG', 'AON', 'CDNS', 'ITW', 'KLAC', 'CL', 'SHW']

def to_yf_symbol(ticker: str) -> str:
    """Yahoo Finance uses a dash where the official ticker has a dot, e.g. BRK.B -> BRK-B."""
    return ticker.replace(".", "-")

SECTOR_MAP = {
    "NVDA": "Semis", "SMCI": "Semis", "AMD": "Semis", "AVGO": "Semis",
    "MRVL": "Semis", "ARM": "Semis", "IONQ": "Semis",
    "TSLA": "Auto", "RIVN": "Auto",
    "PLTR": "Software", "SNOW": "Software", "NET": "Software", "SHOP": "Software",
    "COIN": "Fintech", "MSTR": "Fintech", "SOFI": "Fintech", "UPST": "Fintech", "HOOD": "Fintech",
    "DKNG": "Consumer",
    "ENPH": "Energy",
}


def compute_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def compute_macd(closes: pd.Series) -> float:
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    hist = macd_line - signal
    price = float(closes.iloc[-1])
    # normalize to % of price so a $400 stock and a $15 stock are comparable
    return float(hist.iloc[-1] / price * 100)


def compute_weighted_return(closes: pd.Series) -> float:
    """Weighted price performance, more weight on the recent quarter —
    approximates the IBD RS methodology (not their exact proprietary formula)."""
    def pct_return(period_days):
        if len(closes) <= period_days:
            return 0.0
        return float((closes.iloc[-1] - closes.iloc[-period_days]) / closes.iloc[-period_days])

    r3 = pct_return(63)   # ~3 months of trading days
    r6 = pct_return(126)  # ~6 months
    r9 = pct_return(189)  # ~9 months
    r12 = pct_return(252) # ~12 months
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12


def rs_percentile_rank(scores: dict) -> dict:
    """Rank each ticker's relative-strength score against the rest of the
    universe, 1-99, like IBD's RS Rating scale."""
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    n = len(ranked)
    percentiles = {}
    for i, (ticker, _) in enumerate(ranked):
        pct = round(1 + (i / max(1, n - 1)) * 98)
        percentiles[ticker] = pct
    return percentiles


def compute_trend(closes: pd.Series) -> str:
    sma20 = closes.rolling(20).mean().iloc[-1]
    sma50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else sma20
    if sma20 > sma50 * 1.005:
        return "up"
    if sma20 < sma50 * 0.995:
        return "down"
    return "flat"


def score(chg, rvol, rsi, macd, trend, rs_pct=50):
    momentum = max(-10, min(10, chg)) * 2.0
    vol_surge = min(rvol, 4) * 6
    if 55 <= rsi <= 72:
        rsi_fit = 9
    elif rsi > 72:
        rsi_fit = 9 - (rsi - 72) * 1.2
    elif rsi > 45:
        rsi_fit = 3
    else:
        rsi_fit = -7
    # macd is now normalized as % of price, so clamp/weight is smaller than before
    macd_fit = max(-2, min(2, macd)) * 6
    trend_fit = {"up": 7, "down": -7, "flat": 0}[trend]
    # relative strength vs benchmark, percentile 1-99 -> centered contribution
    rs_fit = (rs_pct - 50) * 0.3
    raw = momentum + vol_surge + rsi_fit + macd_fit + trend_fit + rs_fit
    return round(max(0, min(100, 50 + raw)))


def main():
    print(f"Batch downloading {len(TICKERS)} tickers + SPY (this can take a couple minutes)...")
    yf_symbols = [to_yf_symbol(t) for t in TICKERS]
    all_symbols = yf_symbols + ["SPY"]

    data = yf.download(all_symbols, period="1y", interval="1d", group_by="ticker", auto_adjust=True, threads=True, progress=False)

    def get_hist(yf_symbol):
        try:
            if len(all_symbols) == 1:
                return data
            sub = data[yf_symbol]
            return sub.dropna(how="all")
        except Exception:
            return pd.DataFrame()

    spy_hist = get_hist("SPY")
    spy_weighted = compute_weighted_return(spy_hist["Close"]) if not spy_hist.empty else 0.0

    raw = []  # first pass: gather everything except the final score (needs RS percentile)
    rs_diffs = {}

    for ticker, yf_symbol in zip(TICKERS, yf_symbols):
        try:
            hist = get_hist(yf_symbol)
            if hist.empty or len(hist) < 20:
                print(f"skip {ticker}: not enough history")
                continue

            closes = hist["Close"]
            price = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2])
            chg = round((price - prev_close) / prev_close * 100, 1)

            avg_vol_20 = hist["Volume"].rolling(20).mean().iloc[-1]
            today_vol = hist["Volume"].iloc[-1]
            rvol = round(float(today_vol / avg_vol_20), 1) if avg_vol_20 else 1.0

            rsi = round(compute_rsi(closes))
            macd = round(compute_macd(closes), 1)
            trend = compute_trend(closes)

            # relative strength vs SPY: weighted multi-period return, stock minus benchmark
            ticker_weighted = compute_weighted_return(closes)
            rs_diffs[ticker] = ticker_weighted - spy_weighted

            raw.append({
                "t": ticker,
                "sector": SECTOR_MAP.get(ticker, "Other"),
                "price": round(price, 2),
                "chg": chg,
                "vol": round(float(today_vol) / 1_000_000, 1),
                "rvol": rvol,
                "rsi": rsi,
                "macd": macd,
                "trend": trend,
            })
        except Exception as e:
            print(f"error on {ticker}: {e}")

    rs_pct_by_ticker = rs_percentile_rank(rs_diffs)

    results = []
    for r in raw:
        rs_pct = rs_pct_by_ticker.get(r["t"], 50)
        s = score(r["chg"], r["rvol"], r["rsi"], r["macd"], r["trend"], rs_pct)
        results.append({**r, "rs": rs_pct, "score": s})

    results.sort(key=lambda r: r["score"], reverse=True)

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "benchmark": "SPY",
        "stocks": results,
    }

    with open("scanner_output.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(results)} tickers to scanner_output.json at {output['generated_at']}")
    for r in results[:5]:
        print(f"  {r['t']:6s} score={r['score']:3d}  RS={r['rs']:3d}  chg={r['chg']:+.1f}%  rvol={r['rvol']}x  rsi={r['rsi']}")


if __name__ == "__main__":
    main()
