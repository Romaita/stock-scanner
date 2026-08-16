"""
5-minute stock scanner — pulls real intraday quotes and scores them the
same way as the dashboard's composite score (momentum + relative volume +
RSI sweet-spot + MACD + trend + relative strength + 52-week breakout
proximity), plus supplementary fundamentals/ratings from TradingView.

Requires: pip install yfinance pandas tradingview-screener
Run on a schedule (cron / Task Scheduler) every 5 minutes, e.g.:
    */5 * * * * /usr/bin/python3 /path/to/five_min_scanner.py >> scanner.log 2>&1

Writes results to scanner_output.json each run, which you can point a
real dashboard at (e.g. serve it and fetch() it from a hosted version
of the artifact, or feed it into your own backend).

NOTE on data sources:
  - Price / volume / RSI / MACD / trend now come from 5-minute bars
    (Yahoo only keeps ~60 days of 5m history, and only 5 days per
    single download call, hence period="5d" below).
  - 52-week high/low and the multi-month relative-strength calc still
    need daily history spanning a year, so those two things are pulled
    once from daily bars each run (cheap — 1 extra batch call) rather
    than being derived from the 5-day intraday window.
  - Market cap, P/E, analyst recommendation, and next earnings date come
    from TradingView-Screener (see fetch_tradingview_fields below). If
    that call fails for any reason (network, renamed field, etc.) the
    scanner still runs fine — those four fields just come back as null
    and the dashboard shows "–" for them.
"""

import json
import datetime
import yfinance as yf
import pandas as pd
from tradingview_screener import Query, col

TICKERS = ['AAPL', 'MSFT', 'GOOG', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'BRK.B', 'JPM', 'V', 'MA', 'UNH', 'LLY', 'XOM', 'JNJ', 'PG', 'HD', 'MRK', 'ABBV', 'CVX', 'COST', 'PEP', 'KO', 'ADBE', 'WMT', 'CRM', 'BAC', 'MCD', 'CSCO', 'NFLX', 'TMO', 'ACN', 'ABT', 'LIN', 'DIS', 'AMD', 'DHR', 'WFC', 'TXN', 'PM', 'VZ', 'NEE', 'INTU', 'CMCSA', 'ORCL', 'IBM', 'QCOM', 'AMGN', 'HON', 'UPS', 'CAT', 'LOW', 'SPGI', 'INTC', 'BA', 'GE', 'PLD', 'AMAT', 'UNP', 'SBUX', 'GS', 'RTX', 'BKNG', 'ELV', 'DE', 'MDT', 'BLK', 'ADI', 'ISRG', 'GILD', 'LRCX', 'MMC', 'SYK', 'AXP', 'VRTX', 'CVS', 'C', 'PANW', 'CB', 'REGN', 'MU', 'ADP', 'TJX', 'ETN', 'FI', 'ZTS', 'SLB', 'SO', 'CI', 'BSX', 'MO', 'PYPL', 'SCHW', 'DUK', 'PGR', 'EOG', 'AON', 'CDNS', 'ITW', 'KLAC', 'CL', 'SHW']

# Indicator windows, scaled for 5-minute bars (a trading day is ~78 bars).
RSI_PERIOD = 14        # ~70 min lookback (same bar-count convention as daily RSI-14)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
SMA_SHORT = 20         # ~100 min
SMA_LONG = 50          # ~4 hours

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


def compute_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def compute_macd(closes: pd.Series) -> float:
    ema12 = closes.ewm(span=MACD_FAST).mean()
    ema26 = closes.ewm(span=MACD_SLOW).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=MACD_SIGNAL).mean()
    hist = macd_line - signal
    price = float(closes.iloc[-1])
    return float(hist.iloc[-1] / price * 100)


def compute_weighted_return(closes: pd.Series) -> float:
    def pct_return(period_days):
        if len(closes) <= period_days:
            return 0.0
        return float((closes.iloc[-1] - closes.iloc[-period_days]) / closes.iloc[-period_days])

    r3 = pct_return(63)
    r6 = pct_return(126)
    r9 = pct_return(189)
    r12 = pct_return(252)
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12


def rs_percentile_rank(scores: dict) -> dict:
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    n = len(ranked)
    percentiles = {}
    for i, (ticker, _) in enumerate(ranked):
        pct = round(1 + (i / max(1, n - 1)) * 98)
        percentiles[ticker] = pct
    return percentiles


def compute_52w_range(daily_closes: pd.Series, current_price: float):
    high_52w = float(daily_closes.max())
    low_52w = float(daily_closes.min())
    off_high = round((current_price - high_52w) / high_52w * 100, 1)
    above_low = round((current_price - low_52w) / low_52w * 100, 1)
    return off_high, above_low


def compute_trend(closes: pd.Series) -> str:
    sma20 = closes.rolling(SMA_SHORT).mean().iloc[-1]
    sma50 = closes.rolling(SMA_LONG).mean().iloc[-1] if len(closes) >= SMA_LONG else sma20
    if sma20 > sma50 * 1.005:
        return "up"
    if sma20 < sma50 * 0.995:
        return "down"
    return "flat"


def score(chg, rvol, rsi, macd, trend, rs_pct=50, off_high=None):
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
    macd_fit = max(-2, min(2, macd)) * 6
    trend_fit = {"up": 7, "down": -7, "flat": 0}[trend]
    rs_fit = (rs_pct - 50) * 0.3
    breakout_fit = 0
    if off_high is not None:
        if off_high >= -5:
            breakout_fit = 5
        elif off_high >= -10:
            breakout_fit = 2
    raw = momentum + vol_surge + rsi_fit + macd_fit + trend_fit + rs_fit + breakout_fit
    return round(max(0, min(100, 50 + raw)))


def fetch_tradingview_fields(tickers: list) -> dict:
    """Pull supplementary fundamentals/ratings from TradingView-Screener.
    Never raises — on any failure this just returns {} so the core
    scanner still runs and those fields show as null/'–'."""
    try:
        _, df = (
            Query()
            .select(
                'name',
                'market_cap_basic',
                'price_earnings_ttm',
                'recommendation_mark',
                'earnings_release_next_date',
            )
            .where(col('name').isin(tickers))
            .set_markets('america')
            .get_scanner_data()
        )
    except Exception as e:
        print(f"tradingview-screener fetch failed, skipping extra fields: {e}")
        return {}

    out = {}
    for _, row in df.iterrows():
        out[row['name']] = {
            'marketCap': row.get('market_cap_basic'),
            'pe': row.get('price_earnings_ttm'),
            'analystRec': row.get('recommendation_mark'),
            'nextEarnings': row.get('earnings_release_next_date'),
        }
    return out


def main():
    yf_symbols = [to_yf_symbol(t) for t in TICKERS]
    all_symbols = yf_symbols + ["SPY"]

    print(f"Downloading {len(TICKERS)} tickers + SPY: 5-min bars (5d) for live data...")
    intraday = yf.download(all_symbols, period="5d", interval="5m", group_by="ticker", auto_adjust=True, threads=True, progress=False)

    print(f"Downloading {len(TICKERS)} tickers + SPY: daily bars (1y) for 52wk range / RS...")
    daily = yf.download(all_symbols, period="1y", interval="1d", group_by="ticker", auto_adjust=True, threads=True, progress=False)

    def get_hist(df, yf_symbol):
        try:
            if len(all_symbols) == 1:
                return df
            sub = df[yf_symbol]
            return sub.dropna(how="all")
        except Exception:
            return pd.DataFrame()

    spy_daily = get_hist(daily, "SPY")
    spy_weighted = compute_weighted_return(spy_daily["Close"]) if not spy_daily.empty else 0.0

    raw = []
    rs_diffs = {}

    for ticker, yf_symbol in zip(TICKERS, yf_symbols):
        try:
            hist_5m = get_hist(intraday, yf_symbol)
            hist_1d = get_hist(daily, yf_symbol)
            if hist_5m.empty or len(hist_5m) < SMA_SHORT or hist_1d.empty or len(hist_1d) < 20:
                print(f"skip {ticker}: not enough history")
                continue

            closes_5m = hist_5m["Close"]
            closes_1d = hist_1d["Close"]

            price = float(closes_5m.iloc[-1])
            prev_bar_close = float(closes_5m.iloc[-2])
            chg = round((price - prev_bar_close) / prev_bar_close * 100, 1)

            avg_vol_20 = hist_5m["Volume"].rolling(SMA_SHORT).mean().iloc[-1]
            latest_vol = hist_5m["Volume"].iloc[-1]
            rvol = round(float(latest_vol / avg_vol_20), 1) if avg_vol_20 else 1.0

            rsi = round(compute_rsi(closes_5m))
            macd = round(compute_macd(closes_5m), 1)
            trend = compute_trend(closes_5m)
            off_high, above_low = compute_52w_range(closes_1d, price)

            ticker_weighted = compute_weighted_return(closes_1d)
            rs_diffs[ticker] = ticker_weighted - spy_weighted

            raw.append({
                "t": ticker,
                "sector": SECTOR_MAP.get(ticker, "Other"),
                "price": round(price, 2),
                "chg": chg,
                "vol": round(float(latest_vol) / 1_000_000, 2),
                "rvol": rvol,
                "rsi": rsi,
                "macd": macd,
                "trend": trend,
                "offHigh": off_high,
                "aboveLow": above_low,
            })
        except Exception as e:
            print(f"error on {ticker}: {e}")

    rs_pct_by_ticker = rs_percentile_rank(rs_diffs)

    results = []
    for r in raw:
        rs_pct = rs_pct_by_ticker.get(r["t"], 50)
        s = score(r["chg"], r["rvol"], r["rsi"], r["macd"], r["trend"], rs_pct, r["offHigh"])
        results.append({**r, "rs": rs_pct, "score": s})

    results.sort(key=lambda r: r["score"], reverse=True)

    print(f"Fetching TradingView fields for {len(TICKERS)} tickers...")
    tv_fields = fetch_tradingview_fields(TICKERS)
    for r in results:
        extra = tv_fields.get(r["t"], {})
        r["marketCap"] = extra.get("marketCap")
        r["pe"] = extra.get("pe")
        r["analystRec"] = extra.get("analystRec")
        r["nextEarnings"] = extra.get("nextEarnings")

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "benchmark": "SPY",
        "interval": "5m",
        "stocks": results,
    }

    with open("scanner_output.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(results)} tickers to scanner_output.json at {output['generated_at']}")
    for r in results[:5]:
        print(f"  {r['t']:6s} score={r['score']:3d}  RS={r['rs']:3d}  chg={r['chg']:+.1f}%  rvol={r['rvol']}x  rsi={r['rsi']}")


if __name__ == "__main__":
    main()
