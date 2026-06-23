"""
ggold - 금 선물 관련 지표 수집 스크립트
GitHub Actions에서 15분마다 자동 실행

저장 파일:
  data/market.json              전 종목 현재가 (매번 덮어쓰기)
  data/history/XXX_15m.json     15분봉 최근 5일 (매번 덮어쓰기)
  data/history/XXX_1d.json      일봉 1년 (매번 덮어쓰기)
"""

import json
import os
import datetime
import yfinance as yf

TICKERS = {
    # 현물 금/은 (CFD 기준)
    "xauusd":   "XAUUSD=X",   # 금 현물 XAU/USD
    "xagusd":   "XAGUSD=X",   # 은 현물 XAG/USD
    # 금/은 선물
    "gold":     "GC=F",       # 금 선물
    "silver":   "SI=F",       # 은 선물
    "platinum": "PL=F",       # 플래티넘
    # 달러
    "dxy":      "DX-Y.NYB",   # 달러 인덱스
    # 환율
    "usdkrw":   "KRW=X",
    "usdjpy":   "JPY=X",
    "eurusd":   "EURUSD=X",
    # 미국채
    "tnx":      "^TNX",       # 10년물
    "irx":      "^IRX",       # 2년물
    # 에너지
    "wti":      "CL=F",
    # 증시/변동성
    "sp500":    "^GSPC",
    "nasdaq":   "^IXIC",
    "vix":      "^VIX",
    # 원자재
    "copper":   "HG=F",
}

# 차트용 히스토리 수집 종목 (xauusd 메인)
CHART_KEYS = ["xauusd", "xagusd", "dxy", "tnx", "vix", "sp500", "wti"]


def fix_columns(df):
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_ohlc(sym, period, interval):
    try:
        df = yf.download(sym, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return []
        df = fix_columns(df)
        records = []
        for ts, row in df.iterrows():
            records.append({
                "t": ts.isoformat(),
                "o": round(float(row["Open"]),  4),
                "h": round(float(row["High"]),  4),
                "l": round(float(row["Low"]),   4),
                "c": round(float(row["Close"]), 4),
            })
        return records
    except Exception as e:
        print(f"  [{sym}] {interval} error: {e}")
        return []


def fetch_current(sym):
    try:
        df = yf.download(sym, period="2d", interval="1m",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None, None, None
        df = fix_columns(df)
        close = df["Close"].dropna()
        if len(close) < 2:
            return None, None, None
        price = float(close.iloc[-1])
        prev  = float(close.iloc[-2])
        chg   = round(price - prev, 4)
        chg_p = round((chg / prev) * 100, 3) if prev else 0.0
        return round(price, 4), chg, chg_p
    except Exception as e:
        print(f"  [{sym}] current error: {e}")
        return None, None, None


def main():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] 수집 시작")
    os.makedirs("data/history", exist_ok=True)

    # 1. 전 종목 현재가
    current = {}
    for key, sym in TICKERS.items():
        price, chg, chg_p = fetch_current(sym)
        current[key] = {"symbol": sym, "price": price,
                        "change": chg, "change_pct": chg_p}

    with open("data/market.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now, "current": current},
                  f, ensure_ascii=False, indent=2)
    print("현재가 저장 -> data/market.json")

    # 2. 15분봉 5일
    print("\n15분봉 수집 (5일)...")
    for key in CHART_KEYS:
        sym = TICKERS[key]
        bars = fetch_ohlc(sym, period="5d", interval="15m")
        path = f"data/history/{key}_15m.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(bars, f, ensure_ascii=False)
        print(f"  [{key}] {len(bars)}개 -> {path}")

    # 3. 일봉 1년
    print("\n일봉 수집 (1년)...")
    for key in CHART_KEYS:
        sym = TICKERS[key]
        bars = fetch_ohlc(sym, period="1y", interval="1d")
        path = f"data/history/{key}_1d.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(bars, f, ensure_ascii=False)
        print(f"  [{key}] {len(bars)}개 -> {path}")

    # 요약
    print(f"\n{'종목':12s} {'현재가':>12}  등락률")
    print("-" * 38)
    for key, v in current.items():
        p = v["price"]
        c = v["change_pct"]
        mark  = "▲" if (c is not None and c > 0) else \
                ("▼" if (c is not None and c < 0) else "-")
        p_str = f"{p:.4f}" if p is not None else "N/A"
        c_str = f"{c}%"    if c is not None else "N/A"
        print(f"  {key:12s} {p_str:>12}  {mark} {c_str}")

    print(f"\n[{now}] 완료")


if __name__ == "__main__":
    main()
