from .base import Strategy

class Ema200Breakout(Strategy):
    name = "ema200_breakout"

    def __init__(self, period=200, hold=5, sl_days=5):
        self.period, self.hold, self.sl_days = period, hold, sl_days
        self.warmup = period

    def trades(self, df):
        e = df["Close"].ewm(span=self.period, adjust=False).mean().to_numpy()
        o, h, l, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        d = [str(x.date()) for x in df.index]
        n, H, out, i = len(df), self.hold, [], self.period
        while i < n - H:
            # 1) close crosses EMA from below, 2) next H candles' LOW stays above EMA
            if c[i-1] < e[i-1] and c[i] > e[i] and (l[i+1:i+1+H] > e[i+1:i+1+H]).all():
                j = i + H
                t = dict(cross_date=d[i], signal_date=d[j], entry_price=float(c[j]),
                         exit_date=None, exit_price=None, exit_reason=None, status="open")
                below, k = 0, j + 1
                while k < n:
                    below = below + 1 if h[k] < e[k] else 0
                    if l[k] <= e[k]:                       # exit: low touches EMA
                        px, why = min(o[k], e[k]), "EMA touch"
                    elif below >= self.sl_days:            # stoploss: N candles high < EMA
                        px, why = c[k], "Stoploss"
                    else:
                        k += 1; continue
                    t.update(exit_date=d[k], exit_price=float(px), exit_reason=why, status="closed")
                    break
                # peak = highest HIGH after entry; the exit candle is excluded (intraday order unknown)
                end = k if t["status"] == "closed" else n
                pk = dict(peak_price=None, peak_pct=None, peak_date=None, days_to_peak=None)
                if end > j + 1:
                    p = j + 1 + int(h[j+1:end].argmax())
                    pk = dict(peak_price=float(h[p]), peak_pct=round((h[p] / c[j] - 1) * 100, 2),
                              peak_date=d[p], days_to_peak=p - j)
                t.update(pk)
                last = t["exit_price"] if t["status"] == "closed" else float(c[-1])
                t["ret_pct"] = round((last / t["entry_price"] - 1) * 100, 2)
                t["days_held"] = min(k, n - 1) - j
                out.append(t)
                i = k + 1 if t["status"] == "closed" else n
            else:
                i += 1
        return out

    def forming(self, df):
        """Crossed above EMA k candles ago (k=1..hold-1), all k lows above EMA so far."""
        e = df["Close"].ewm(span=self.period, adjust=False).mean().to_numpy()
        l, c = df["Low"].to_numpy(), df["Close"].to_numpy()
        n = len(df)
        for k in range(1, self.hold):
            i = n - 1 - k
            if i >= self.period and c[i-1] < e[i-1] and c[i] > e[i] and (l[i+1:] > e[i+1:]).all():
                return dict(cross_date=str(df.index[i].date()), days_confirmed=k, days_left=self.hold - k,
                            last_close=round(float(c[-1]), 2), ema=round(float(e[-1]), 2),
                            cushion_pct=round((c[-1] / e[-1] - 1) * 100, 2))
