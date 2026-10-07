import argparse, csv, sys
from app import db, pipeline, notify
from app.strategies import REGISTRY

p = argparse.ArgumentParser()
p.add_argument("cmd", choices=["backtest", "scan", "serve", "telegram-test", "export"])
p.add_argument("--strategy", default="ema200_breakout", choices=list(REGISTRY))
a = p.parse_args()
if a.cmd == "telegram-test":
    notify.test()
elif a.cmd == "export":
    from app import export; export.export()
elif a.cmd == "serve":
    import uvicorn; uvicorn.run("app.api:app", host="127.0.0.1", port=8000)
else:
    pipeline.run(a.strategy, notify_on=(a.cmd == "scan"))
    print(db.summary(a.strategy))
    rows = db.rows(a.strategy)
    with open(f"{a.strategy}_trades.csv", "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys() if rows else db.COLS); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} trades -> {a.strategy}_trades.csv")
