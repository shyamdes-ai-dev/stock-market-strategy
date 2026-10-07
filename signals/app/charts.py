import re

def fname(symbol):
    return re.sub(r"[^A-Za-z0-9_-]", "_", symbol)

def save(df, w, path, period=200, bars=100):
    """Candles + EMA + cross marker + confirmation band for one watchlist stock."""
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = df["Close"].ewm(span=period, adjust=False).mean().iloc[-bars:]
    d = df.iloc[-bars:]; x = np.arange(len(d))
    dates = list(d.index.strftime("%Y-%m-%d")); ci = dates.index(w["cross_date"])
    bg, fg, mu, g, r = "#14161a", "#eee", "#999", "#3ddc84", "#ff6b6b"
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=110, facecolor=bg); ax.set_facecolor(bg)
    for i, (o, h, l, c) in zip(x, d[["Open", "High", "Low", "Close"]].to_numpy()):
        col = g if c >= o else r
        ax.vlines(i, l, h, color=col, lw=1); ax.bar(i, abs(c - o) or .01, bottom=min(o, c), width=.7, color=col)
    ax.plot(x, e.to_numpy(), color="#f5a623", lw=2, label=f"{period} EMA")
    ax.axvspan(ci + .5, len(d) - .5, color="#4da3ff", alpha=.12, label="confirmation so far")
    ax.scatter(ci, d["Close"].iloc[ci], marker="^", s=90, color="#4da3ff", zorder=5)
    ax.annotate(f"EMA cross {w['cross_date']}", (ci, d["Close"].iloc[ci]), xytext=(-8, -26),
                textcoords="offset points", color="#4da3ff", fontsize=8, ha="right")
    when = "TOMORROW" if w["days_left"] == 1 else f"in {w['days_left']} days"
    ax.set_title(f"{w['symbol']}  triggers {when} if low stays above EMA  |  cushion {w['cushion_pct']:+.1f}%",
                 color=fg, fontsize=11, loc="left")
    ax.text(.99, .03, f"close {w['last_close']}   EMA {w['ema']}   as of {w['last_date']}",
            transform=ax.transAxes, ha="right", color=mu, fontsize=8)
    step = max(len(dates) // 6, 1); ax.set_xticks(x[::step]); ax.set_xticklabels(dates[::step], color=mu, fontsize=8)
    ax.tick_params(colors=mu); [s.set_color("#2c2f36") for s in ax.spines.values()]; ax.grid(color="#2c2f36", lw=.5)
    ax.legend(facecolor=bg, edgecolor="#2c2f36", labelcolor=fg, loc="upper left", fontsize=8)
    plt.tight_layout(); plt.savefig(path, facecolor=bg); plt.close(fig)
