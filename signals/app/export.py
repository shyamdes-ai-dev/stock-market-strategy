import json
from pathlib import Path
from . import db, charts
from .strategies import REGISTRY

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "docs"

def export():
    """Writes a static copy of the dashboard (docs/) that GitHub Pages can host."""
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    with db.conn() as c:
        stocks = [dict(r) for r in c.execute("SELECT * FROM stocks")]
    watch = []
    for s in REGISTRY: watch += db.watch_rows(s)
    for w in watch:
        f = f"charts/{charts.fname(w['symbol'])}.png"
        w["chart"] = f if (OUT / f).exists() else None
    data = dict(strategies=list(REGISTRY), trades=db.rows(), stocks=stocks, watch=watch)
    (OUT / "data" / "data.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    html = (BASE / "web" / "index.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(html.replace("</head>", "<script>window.STATIC=true</script></head>", 1), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"exported {len(data['trades'])} trades, {len(watch)} watchlist stocks -> {OUT}")
