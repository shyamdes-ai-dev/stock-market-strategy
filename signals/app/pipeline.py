import io, os, re, time, requests, pandas as pd, yfinance as yf
from pathlib import Path
from . import db, notify, charts
from .strategies import REGISTRY

NSE_CSV = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
BASE = Path(__file__).resolve().parents[1]

def _norm(d):
    return {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in d.items()}

def _nse():
    r = requests.get(NSE_CSV, headers={"User-Agent": "Mozilla/5.0"}, timeout=30); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text)); df.columns = df.columns.str.strip()
    df = df[df["SERIES"].str.strip() == "EQ"]
    isin = set(df["ISIN NUMBER"].str.strip()) if "ISIN NUMBER" in df else set()
    return {s.strip() + ".NS": s.strip() for s in df["SYMBOL"]}, isin

def _bse_rows():
    try:
        r = requests.get(BSE_API, timeout=40, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/"})
        r.raise_for_status(); data = r.json()
        if isinstance(data, dict): data = next((v for v in data.values() if isinstance(v, list)), [])
        if data: return data
    except Exception as ex:
        print("BSE list download failed:", ex)
    f = BASE / "bse_scrips.csv"                  # manual fallback: BSE website -> List of Scrips -> Equity -> download
    if f.exists(): return pd.read_csv(f, dtype=str).fillna("").to_dict("records")
    print("No BSE list available. Download it from bseindia.com (List of Scrips) and save as", f); return []

def universe():
    """{yahoo ticker: display symbol}. UNIVERSE=nse,bse (default). BSE: only stocks NOT also listed on NSE."""
    kinds = os.getenv("UNIVERSE", "nse,bse").lower()
    nse, isin = _nse()
    names = dict(nse) if "nse" in kinds else {}
    if "bse" in kinds:
        groups = {g.strip().upper() for g in os.getenv("BSE_GROUPS", "A,B").split(",")}
        for row in map(_norm, _bse_rows()):
            code = str(row.get("securitycode") or row.get("scripcd") or "").strip()
            sid = str(row.get("securityid") or row.get("scripid") or code).strip()
            grp = str(row.get("group") or "").strip().upper()
            ok = str(row.get("status") or "Active").strip().lower() == "active"
            i = str(row.get("isinno") or row.get("isinnumber") or "").strip()
            if code.isdigit() and ok and grp in groups and i not in isin:
                names[f"{code}.BO"] = f"{sid}.BO"
    print(f"universe: {len(names)} stocks ({sum(v.endswith('.BO') for v in names.values())} BSE-only)")
    return names

OUT = Path(__file__).resolve().parents[1] / "docs"

def candles(symbols, min_bars, period="6y", batch=100):
    for i in range(0, len(symbols), batch):
        b, d = symbols[i:i+batch], None
        for attempt in range(3):             # Yahoo sometimes throttles shared IPs: retry
            try:
                d = yf.download(b, period=period, group_by="ticker", threads=True, progress=False, auto_adjust=True); break
            except Exception as ex:
                print("batch failed, retrying:", ex); time.sleep(5 * (attempt + 1))
        if d is None: continue
        for s in b:
            try: x = d[s].dropna()
            except KeyError: continue
            if len(x) > min_bars: yield s, x   # recent listings are fine once they have enough candles
        print(f"  scanned {min(i+batch, len(symbols))}/{len(symbols)}")

def _charts(strat, watch, frames):
    import shutil
    d = OUT / "charts"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True, exist_ok=True)
    for w in watch:
        try: charts.save(frames[w["symbol"]], w, str(d / f"{charts.fname(w['symbol'])}.png"), getattr(strat, "period", 200))
        except Exception as ex: print("chart failed", w["symbol"], ex)

def report(name, watch, alerts, full=True):
    if not full:
        notify.send(f"{name}\n" + "\n".join(alerts)); return
    asof = max((w["last_date"] for w in watch), default="")
    soon = sorted((w for w in watch if w["days_left"] == 1), key=lambda w: -w["cushion_pct"])
    later = sorted((w for w in watch if w["days_left"] > 1), key=lambda w: (w["days_left"], -w["cushion_pct"]))
    L = [f"📊 {name} daily report" + (f" (data as of {asof})" if asof else "")]
    if alerts: L += ["", f"Trades ({len(alerts)}):"] + alerts[:25]
    L += ["", f"👀 Triggers on next candle ({len(soon)}) - its LOW must stay above the EMA:"]
    L += [f"• {w['symbol']}  close {w['last_close']}  EMA {w['ema']}  cushion +{w['cushion_pct']}%" for w in soon] or ["none today"]
    if later: L += ["", f"⏳ Still forming ({len(later)}): " + ", ".join(f"{w['symbol']} ({w['days_left']}d)" for w in later)]
    if os.getenv("DASHBOARD_URL"): L += ["", "Dashboard: " + os.environ["DASHBOARD_URL"]]
    notify.send("\n".join(L))
    for w in (soon + later)[: int(os.getenv("REPORT_MAX_CHARTS", 15))]:
        img = OUT / "charts" / f"{charts.fname(w['symbol'])}.png"
        if img.exists():
            when = "TOMORROW" if w["days_left"] == 1 else f"in {w['days_left']} days"
            notify.send_photo(str(img), f"{w['symbol']}: triggers {when} - cushion +{w['cushion_pct']}%, close {w['last_close']}, EMA {w['ema']}")
            time.sleep(1.2)                  # Telegram allows ~1 message/second per chat

def run(name, notify_on=True):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    strat, alerts, watch, frames, latest = REGISTRY[name](), [], [], {}, ""
    backfill = db.count(name) == 0          # first run = history, don't spam alerts
    names = universe()
    for sym, df in candles(list(names), strat.warmup + 10):
        nm = names[sym]
        db.upsert_stock(nm, str(df.index[0].date()), str(df.index[strat.warmup].date()), len(df))
        for t in strat.trades(df):
            t.update(strategy=name, symbol=nm)
            ev = db.upsert(t)
            # only alert on recent events, so adding stocks/history never floods Telegram
            if ev and (t["exit_date"] or t["signal_date"]) >= str(df.index[-5].date()): alerts.append(notify.fmt(ev, t))
        latest = max(latest, str(df.index[-1].date()))
        f = strat.forming(df)
        if f:
            watch.append({**f, "strategy": name, "symbol": nm, "last_date": str(df.index[-1].date())})
            frames[nm] = df
    db.replace_watch(name, watch)
    _charts(strat, watch, frames)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    full = latest >= today or bool(os.getenv("FORCE_REPORT"))   # no new candle today = market holiday
    if notify_on and (full or (alerts and not backfill)):
        report(name, watch, [] if backfill else alerts, full)
    elif notify_on:
        print(f"Latest candle is {latest}, not {today} (holiday?). Report skipped. Set FORCE_REPORT=1 to send anyway.")
    return alerts
