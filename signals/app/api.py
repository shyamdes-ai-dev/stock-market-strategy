import csv, io, os
from datetime import date, timedelta
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from . import db
from .strategies import REGISTRY

app = FastAPI()
STOCK_COLS = ["symbol","patterns","closed","open","wins","success_pct","avg_ret_pct","total_ret_pct","avg_peak_pct","best_peak_pct","data_from","signals_from"]

def _range(years, since, until):
    if years: since = str(date.today() - timedelta(days=round(365.25 * years)))
    return since or None, until or None

def _csv(rows, cols, name):
    buf = io.StringIO(); w = csv.DictWriter(buf, cols); w.writeheader(); w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={name}.csv"})

@app.get("/api/strategies")
def strategies(): return list(REGISTRY)

@app.get("/api/trades")
def trades(strategy: str = None, status: str = None, years: float = None, since: str = None, until: str = None):
    return db.rows(strategy, status, *_range(years, since, until))

@app.get("/api/trades.csv")
def trades_csv(strategy: str = None, status: str = None, years: float = None, since: str = None, until: str = None):
    return _csv(db.rows(strategy, status, *_range(years, since, until)), db.COLS, f"{strategy}_trades")

@app.get("/api/stocks")
def stocks(strategy: str, years: float = None, since: str = None, until: str = None):
    return db.stock_stats(strategy, *_range(years, since, until))

@app.get("/api/stocks.csv")
def stocks_csv(strategy: str, years: float = None, since: str = None, until: str = None):
    return _csv(db.stock_stats(strategy, *_range(years, since, until)), STOCK_COLS, f"{strategy}_by_stock")

WATCH_COLS = ["symbol","days_left","days_confirmed","cross_date","last_close","ema","cushion_pct","last_date"]

@app.get("/api/watch")
def watch(strategy: str): return db.watch_rows(strategy)

@app.get("/api/watch.csv")
def watch_csv(strategy: str): return _csv(db.watch_rows(strategy), WATCH_COLS, f"{strategy}_watchlist")

@app.get("/api/summary")
def summary(strategy: str, years: float = None, since: str = None, until: str = None):
    return db.summary(strategy, *_range(years, since, until))

@app.get("/")
def index(): return FileResponse(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html"))
