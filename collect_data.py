"""
ggold - 금 선물 관련 지표 수집 스크립트
GitHub Actions에서 15분마다 자동 실행
"""

import json
import datetime
import yfinance as yf

# 수집할 티커 목록
TICKERS = {
    # 귀금속
    "gold":     "GC=F",     # 금 선물
    "silver":   "SI=F",     # 은 선물
    "platinum": "PL=F",     # 플래티넘

    # 달러
    "dxy":      "DX-Y.NYB", # 달러 인덱스

    # 환율
    "usdkrw":   "KRW=X",    # 달러/원
    "usdjpy":   "JPY=X",    # 달러/엔
    "eurusd":   "EURUSD=X", # 유로/달러

    # 미국채 금리
    "tnx":      "^TNX",     # 10년물 수익률
    "irx":      "^IRX",     # 2년물 수익률

    # 에너지
    "wti":      "CL=F",     # WTI 원유

    # 증시 / 변동성
    "sp500":    "^GSPC",    # S&P 500
    "nasdaq":   "^IXIC",    # 나스닥
    "vix":      "^VIX",     # VIX 공포지수

    # 원자재 (경기선행)
    "copper":   "HG=F",     # 구리
}

def fetch_current(ticker_map):
    """현재가 + 전일비 수집"""
    result = {}
    symbols = list(ticker_map.values())
    
    try:
        data = yf.download(
            tickers=symbols,
            period="2d",
            interval="1m",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True
        )
    except Exception as e:
        print(f"Download error: {e}")
        return result

    for key, sym in ticker_map.items():
        try:
            if len(symbols) == 1:
                df = data
            else:
                df = data[sym] if sym in data.columns.get_level_values(0) else None

            if df is None or df.empty:
                result[key] = {"symbol": sym, "price": None, "change": None, "change_pct": None}
                continue

            close = df["Close"].dropna()
            if len(close) < 2:
                result[key] = {"symbol": sym, "price": None, "change": None, "change_pct": None}
                continue

            price = float(close.iloc[-1])
            prev  = float(close.iloc[-2])
            chg   = round(price - prev, 4)
            chg_p = round((chg / prev) * 100, 3) if prev else 0

            result[key] = {
                "symbol":     sym,
                "price":      round(price, 4),
                "change":     chg,
                "change_pct": chg_p,
            }
        except Exception as e:
            print(f"  [{sym}] error: {e}")
            result[key] = {"symbol": sym, "price": None, "change": None, "change_pct": None}

    return result

def fetch_history(ticker_map, days=7):
    """최근 N일 1시간봉 히스토리 (차트용)"""
    result = {}
    # 차트는 주요 지표만
    chart_keys = ["gold", "dxy", "tnx", "vix", "sp500"]

    for key in chart_keys:
        sym = ticker_map.get(key)
        if not sym:
            continue
        try:
            df = yf.download(
                tickers=sym,
                period=f"{days}d",
                interval="1h",
                auto_adjust=True,
                progress=False
            )
            if df.empty:
                continue

            records = []
            for ts, row in df.iterrows():
                records.append({
                    "t": ts.isoformat(),
                    "o": round(float(row["Open"]),  4),
                    "h": round(float(row["High"]),  4),
                    "l": round(float(row["Low"]),   4),
                    "c": round(float(row["Close"]), 4),
                })
            result[key] = records
        except Exception as e:
            print(f"  [{sym}] history error: {e}")

    return result

def main():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] 데이터 수집 시작...")

    current = fetch_current(TICKERS)
    history = fetch_history(TICKERS, days=7)

    output = {
        "updated_at": now,
        "current":    current,
        "history":    history,
    }

    with open("data/market.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[{now}] 저장 완료 → data/market.json")

    # 수집 결과 요약 출력
    for key, v in current.items():
        p = v.get("price")
        c = v.get("change_pct")
        mark = "▲" if c and c > 0 else ("▼" if c and c < 0 else "-")
        print(f"  {key:10s} {p:>10} {mark} {c}%")

if __name__ == "__main__":
    main()
