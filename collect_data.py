"""
ggold - 금 선물 관련 지표 수집 스크립트
GitHub Actions에서 15분마다 자동 실행
- data/market.json          : 전 종목 현재가 (매번 덮어쓰기)
- data/history/XXX_15m.json : 차트용 15분봉 누적 (최근 60일)
"""

import json
import os
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

# 차트용 히스토리 수집 종목
CHART_KEYS = ["gold", "dxy", "tnx", "vix", "sp500", "wti", "usdkrw"]

KEEP_DAYS = 60   # 보관 기간 (yfinance 15분봉 최대 60일)
INIT_DAYS = 60   # 최초 수집 기간


# ────────────────────────────────────────────
def fix_columns(df):
    """yfinance MultiIndex 컬럼 처리"""
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_current(sym):
    """현재가 · 등락률"""
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


def fetch_15m(sym, days):
    """15분봉 수집 (최대 60일)"""
    try:
        df = yf.download(sym, period=f"{days}d", interval="15m",
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
        print(f"  [{sym}] 15m fetch error: {e}")
        return []


def update_history(key, sym):
    """
    히스토리 파일 누적 업데이트
    - 파일 없음 → INIT_DAYS일치 전체 수집 (최초 1회)
    - 파일 있음 → 최근 1일치 받아서 새 봉만 추가
    """
    path = f"data/history/{key}_15m.json"
    os.makedirs("data/history", exist_ok=True)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)

        # 최근 1일치만 새로 받아서 없는 타임스탬프만 추가
        new_bars = fetch_15m(sym, days=1)
        existing_ts = {r["t"] for r in existing}
        added = [b for b in new_bars if b["t"] not in existing_ts]
        merged = existing + added
        print(f"  [{key}] 기존 {len(existing)}개 + 신규 {len(added)}개")
    else:
        # 최초 실행: 60일치 전체 수집
        print(f"  [{key}] 최초 수집 중 ({INIT_DAYS}일치 15분봉)...")
        merged = fetch_15m(sym, days=INIT_DAYS)
        print(f"  [{key}] {len(merged)}개 수집")

    # 정렬 + 오래된 데이터 제거
    merged.sort(key=lambda x: x["t"])
    cutoff = (datetime.datetime.utcnow()
              - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    merged = [r for r in merged if r["t"] >= cutoff]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)

    print(f"  [{key}] 저장: {len(merged)}개 ({path})")
    return len(merged)


# ────────────────────────────────────────────
def main():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] 수집 시작")

    os.makedirs("data", exist_ok=True)

    # 1. 전 종목 현재가
    current = {}
    for key, sym in TICKERS.items():
        price, chg, chg_p = fetch_current(sym)
        current[key] = {
            "symbol":     sym,
            "price":      price,
            "change":     chg,
            "change_pct": chg_p,
        }

    with open("data/market.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now, "current": current},
                  f, ensure_ascii=False, indent=2)
    print("현재가 저장 → data/market.json")

    # 2. 15분봉 히스토리 누적
    print("\n히스토리 업데이트...")
    for key in CHART_KEYS:
        update_history(key, TICKERS[key])

    # 요약 출력
    print(f"\n{'종목':10s} {'현재가':>12}  등락률")
    print("-" * 36)
    for key, v in current.items():
        p = v["price"]
        c = v["change_pct"]
        mark = "▲" if (c is not None and c > 0) else \
               ("▼" if (c is not None and c < 0) else "-")
        p_str = f"{p:.4f}" if p is not None else "N/A"
        c_str = f"{c}%"    if c is not None else "N/A"
        print(f"  {key:10s} {p_str:>12}  {mark} {c_str}")

    print(f"\n[{now}] 완료")


if __name__ == "__main__":
    main()
