import os, requests

def _load_env():
    """Looks for .env in the current folder, in signals/, and in the repo root above it."""
    from pathlib import Path
    here = Path(__file__).resolve().parents[1]          # the signals/ folder
    for p in (Path.cwd() / ".env", here / ".env", here.parent / ".env"):
        if p.is_file():
            for line in open(p, encoding="utf-8-sig"):
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.removeprefix("export ").split("=", 1)
                    if not os.environ.get(k.strip()):
                        os.environ[k.strip()] = v.strip().strip("\"'")
_load_env()

def send(text):
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        print("[telegram not configured - see README]\n" + text); return
    for i in range(0, len(text), 4000):
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": text[i:i+4000]}, timeout=20)
        if not r.ok: print("Telegram error:", r.text)

def send_photo(path, caption=""):
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        print("[telegram not configured] photo", path); return
    with open(path, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendPhoto", data={"chat_id": chat, "caption": caption[:1000]},
                          files={"photo": f}, timeout=60)
    if not r.ok: print("Telegram error:", r.text)

def test():
    tok = os.getenv("TELEGRAM_TOKEN")
    if not tok:
        print("Put TELEGRAM_TOKEN in .env first (create a bot with @BotFather)."); return
    if not os.getenv("TELEGRAM_CHAT_ID"):
        me = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=20).json()
        if not me.get("ok"):
            print("Token rejected by Telegram:", me.get("description"), "- re-copy it from BotFather."); return
        print("Bot found: @" + me["result"]["username"] + "  (message THIS bot, then run again)")
        res = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=20).json()
        if not res.get("ok"):
            print("Telegram error:", res.get("description"))
            if res.get("error_code") == 409: print("A webhook is set; open https://api.telegram.org/bot<TOKEN>/deleteWebhook once, then retry.")
            return
        ids = {(m.get("message") or m.get("channel_post") or {}).get("chat", {}).get("id") for m in res["result"]} - {None}
        print(f"Your chat id: {', '.join(map(str, ids))}  -> put it in .env as TELEGRAM_CHAT_ID" if ids
              else "No messages found yet. Open @" + me["result"]["username"] + " in Telegram, tap Start / send 'hi', then run again.")
        return
    send("✅ Telegram connected. Signals will arrive here.")

def fmt(ev, t):
    if ev == "new" and t["status"] == "open":
        return f"🟢 BUY {t['symbol']} @ {t['entry_price']:.2f} (signal {t['signal_date']}, EMA cross {t['cross_date']})"
    return (f"🔴 EXIT {t['symbol']} @ {t['exit_price']:.2f} on {t['exit_date']} "
            f"[{t['exit_reason']}] return {t['ret_pct']}%")
