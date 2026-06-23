"""
ggold - 금 선물 관련 지표 수집 스크립트
GitHub Actions에서 15분마다 자동 실행
"""

import json
import datetime
import yfinance as yf

TICKERS = {
    "gold":     "GC=F",
    "silver":   "SI=F",
    "platinum": "PL=F",
    "dxy":      "DX-Y.NYB",
    "usdkrw":   "KRW=X",
    "usdjpy":   "JPY=X",
    "eurusd":   "EURUSD=X",
    "tnx":      "^TNX",
    "irx":      "^IRX",
    "wti":      "CL=F",
    "sp500":    "^GSPC",
    "nasdaq":   "^IXIC",
    "vix":      "^VIX",
    "copper":   "HG=F",
}

CHART_KEYS = ["gold", "dxy", "tnx", "vix", "sp500"]

def fetch_one(sym):
    """티커 1개씩 개별 수집 — 멀티 다운로드 구조 문제 우회"""
    try:
        df = yf.download(
            tickers=sym,
            period="2d",
            interval="1m",
            auto_adjust=True,
            progress=False,
        )
        if df is None or df.empty:
            return None, None, None

        # yfinance 최신 버전: 컬럼이 MultiIndex일 수 있음
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        close = df["Close"].dropna()
        if len(close) < 2:
            return None, None, None

        price = float(close.iloc[-1])
        prev  = float(close.iloc[-2])
        chg   = round(price - prev, 4)
        chg_p = round((chg / prev) * 100, 3) if prev else 0.0
        return round(price, 4), chg, chg_p

    except Exception as e:
        print(f"  [{sym}] fetch error: {e}")
        return None, None, None


def fetch_history_one(sym, days=7):
    """1시간봉 히스토리 (차트용)"""
    try:
        df = yf.download(
            tickers=sym,
            period=f"{days}d",
            interval="1h",
            auto_adjust=True,
            progress=False,
        )
        if df is None or df.empty:
            return []

        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

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
        print(f"  [{sym}] history error: {e}")
        return []


def main():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] 데이터 수집 시작...")

    current = {}
    for key, sym in TICKERS.items():
        price, chg, chg_p = fetch_one(sym)
        current[key] = {
            "symbol":     sym,
            "price":      price,
            "change":     chg,
            "change_pct": chg_p,
        }

    history = {}
    for key in CHART_KEYS:
        sym = TICKERS[key]
        history[key] = fetch_history_one(sym, days=7)

    output = {
        "updated_at": now,
        "current":    current,
        "history":    history,
    }

    with open("data/market.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[{now}] 저장 완료 -> data/market.json")

    # 수집 결과 요약 (None 안전 처리)
    for key, v in current.items():
        p = v.get("price")
        c = v.get("change_pct")
        mark = "▲" if (c is not None and c > 0) else ("▼" if (c is not None and c < 0) else "-")
        p_str = f"{p:.4f}" if p is not None else "N/A"
        c_str = f"{c}%" if c is not None else "N/A"
        print(f"  {key:10s} {p_str:>12}  {mark} {c_str}")


if __name__ == "__main__":
    main()
