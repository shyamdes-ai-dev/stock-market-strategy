import sqlite3, os
PATH = os.getenv("DB_PATH") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "signals.db")
COLS = ["strategy","symbol","cross_date","signal_date","entry_price","exit_date",
        "exit_price","exit_reason","ret_pct","days_held","status",
        "peak_price","peak_pct","peak_date","days_to_peak"]

def conn():
    c = sqlite3.connect(PATH); c.row_factory = sqlite3.Row
    c.execute(f"""CREATE TABLE IF NOT EXISTS trades({','.join(COLS)},
                  PRIMARY KEY(strategy,symbol,signal_date))""")
    have = {r[1] for r in c.execute("PRAGMA table_info(trades)")}
    for k in COLS:                       # migrate older databases
        if k not in have: c.execute(f"ALTER TABLE trades ADD COLUMN {k}")
    c.execute("""CREATE TABLE IF NOT EXISTS stocks(symbol PRIMARY KEY, first_date, eligible_from, bars)""")
    c.execute("""CREATE TABLE IF NOT EXISTS watch(strategy,symbol,cross_date,days_confirmed,days_left,
                 last_close,ema,cushion_pct,last_date, PRIMARY KEY(strategy,symbol))""")
    return c

def watch_rows(strategy):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM watch WHERE strategy=? ORDER BY days_left, cushion_pct DESC", (strategy,))]

def replace_watch(strategy, items):
    cols = ["strategy","symbol","cross_date","days_confirmed","days_left","last_close","ema","cushion_pct","last_date"]
    with conn() as c:
        c.execute("DELETE FROM watch WHERE strategy=?", (strategy,))
        c.executemany(f"INSERT INTO watch VALUES({','.join('?'*len(cols))})", [[i[k] for k in cols] for i in items])

def upsert_stock(symbol, first_date, eligible_from, bars):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO stocks VALUES(?,?,?,?)", (symbol, first_date, eligible_from, bars))

def count(strategy):
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM trades WHERE strategy=?", (strategy,)).fetchone()[0]

def upsert(t):
    """Returns 'new', 'closed' or None (no change)."""
    with conn() as c:
        r = c.execute("SELECT status FROM trades WHERE strategy=? AND symbol=? AND signal_date=?",
                      (t["strategy"], t["symbol"], t["signal_date"])).fetchone()
        c.execute(f"INSERT OR REPLACE INTO trades({','.join(COLS)}) VALUES({','.join('?'*len(COLS))})",
                  [t.get(k) for k in COLS])
    if r is None: return "new"
    if r["status"] == "open" and t["status"] == "closed": return "closed"

def rows(strategy=None, status=None, since=None, until=None):
    q, a = "SELECT * FROM trades WHERE 1=1", []
    for sql, v in (("strategy=?", strategy), ("status=?", status),
                   ("signal_date>=?", since), ("signal_date<=?", until)):
        if v: q += " AND " + sql; a.append(v)
    with conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY signal_date DESC", a)]

def summary(strategy, since=None, until=None):
    from statistics import median
    cl = rows(strategy, "closed", since, until)
    op = rows(strategy, "open", since, until)
    r = [x["ret_pct"] for x in cl]
    pk = [x["peak_pct"] for x in cl if x["peak_pct"] is not None]
    n = len(r)
    return {"closed": n, "open": len(op),
            "win_rate": round(100*sum(x > 0 for x in r)/n, 1) if n else 0,
            "total_ret_pct": round(sum(r), 2),
            "avg_ret_pct": round(sum(r)/n, 2) if n else 0,
            "median_ret_pct": round(median(r), 2) if n else 0,
            "avg_peak_pct": round(sum(pk)/len(pk), 2) if pk else 0,
            "median_peak_pct": round(median(pk), 2) if pk else 0,
            "pct_peak_10": round(100*sum(x >= 10 for x in pk)/len(pk), 1) if pk else 0,
            "best": max(r, default=0), "worst": min(r, default=0),
            "avg_days": round(sum(x["days_held"] for x in cl)/n) if n else 0}

def stock_stats(strategy, since=None, until=None):
    on, a = "t.symbol=s.symbol AND t.strategy=?", [strategy]
    if since: on += " AND t.signal_date>=?"; a.append(since)
    if until: on += " AND t.signal_date<=?"; a.append(until)
    q = f"""SELECT s.symbol, COUNT(t.symbol) patterns,
        SUM(t.status='closed') closed, SUM(t.status='open') open,
        SUM(t.status='closed' AND t.ret_pct>0) wins,
        ROUND(AVG(CASE WHEN t.status='closed' THEN t.ret_pct END),2) avg_ret_pct,
        ROUND(SUM(CASE WHEN t.status='closed' THEN t.ret_pct END),2) total_ret_pct,
        ROUND(AVG(t.peak_pct),2) avg_peak_pct, MAX(t.peak_pct) best_peak_pct,
        s.first_date data_from, s.eligible_from signals_from
        FROM stocks s LEFT JOIN trades t ON {on} GROUP BY s.symbol"""
    with conn() as c:
        out = []
        for r in c.execute(q, a):
            d = dict(r)
            for k in ("closed", "open", "wins"): d[k] = d[k] or 0
            d["success_pct"] = round(100 * d["wins"] / d["closed"], 1) if d["closed"] else None
            out.append(d)
        return out
