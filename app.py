# -*- coding: utf-8 -*-
"""
LVBXNT Crypto Bot - V25 HEDGE AI PRO PACK
Advanced AI scoring + hedge shield + smart execution + Contabo-ready 24/7 structure.
Local-first. Contabo VPS ready. Oracle/Render removed.
APIs gratuites : Binance + CoinGecko + DexScreener.
"""

import os, time, sqlite3, threading
from datetime import datetime
from typing import Dict, List, Optional
import requests
try:
    import ccxt
except Exception:
    ccxt = None
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE":
    raise ValueError("BOT_TOKEN missing - mets ton token Telegram dans .env")

RUN_MODE = os.getenv("RUN_MODE", "polling").strip().lower()
PORT = int(os.getenv("PORT", "5000"))
DB_PATH = os.getenv("DB_PATH", "crypto_bot.db")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "90"))
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))
ENABLE_AUTOSCAN_THREAD = os.getenv("ENABLE_AUTOSCAN_THREAD", "1") == "1"
EXTERNAL_BASE_URL = os.getenv("EXTERNAL_BASE_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change_me_for_future_contabo")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change_me")

ENABLE_LIVE_TRADING = os.getenv("ENABLE_LIVE_TRADING", "0") == "1"
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY", "").strip()
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET", "").strip()
ACCOUNT_EQUITY_USD = float(os.getenv("ACCOUNT_EQUITY_USD", "1000"))
MAX_TRADE_QUOTE_USD = float(os.getenv("MAX_TRADE_QUOTE_USD", "100"))
MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "2"))
SAFE_MODE = os.getenv("SAFE_MODE", "1") == "1"
MIN_TRADE_SCORE = int(os.getenv("MIN_TRADE_SCORE", "80"))
MIN_SNIPER_SCORE = int(os.getenv("MIN_SNIPER_SCORE", "85"))
MIN_AUTOTRADE_SCORE = int(os.getenv("MIN_AUTOTRADE_SCORE", "90"))
DAILY_MAX_LOSSES = int(os.getenv("DAILY_MAX_LOSSES", "2"))
AUTO_TRADE_RISK_PERCENT = float(os.getenv("AUTO_TRADE_RISK_PERCENT", "1"))
ENABLE_BREAK_EVEN = os.getenv("ENABLE_BREAK_EVEN", "1") == "1"
ENABLE_TRAILING_STOP = os.getenv("ENABLE_TRAILING_STOP", "1") == "1"
AUTO_SCAN_FULL_AUTO = os.getenv("AUTO_SCAN_FULL_AUTO", "1") == "1"
DYNAMIC_SCORING = os.getenv("DYNAMIC_SCORING", "1") == "1"
NEWS_VOLATILITY_FILTER = os.getenv("NEWS_VOLATILITY_FILTER", "1") == "1"
MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "3"))
MIN_VOLUME_RATIO = float(os.getenv("MIN_VOLUME_RATIO", "1.20"))
MIN_RR = float(os.getenv("MIN_RR", "1.50"))
MAX_BTC_1H_MOVE_PERCENT = float(os.getenv("MAX_BTC_1H_MOVE_PERCENT", "3.5"))
PARTIAL_TP1_PERCENT = float(os.getenv("PARTIAL_TP1_PERCENT", "50"))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "2"))
ELITE_MODE = os.getenv("ELITE_MODE", "1") == "1"
AI_SCORING = os.getenv("AI_SCORING", "1") == "1"
AI_MIN_CLOSED_TRADES = int(os.getenv("AI_MIN_CLOSED_TRADES", "8"))
AI_MAX_SCORE_ADJUST = int(os.getenv("AI_MAX_SCORE_ADJUST", "10"))
AI_ADAPTIVE_RISK = os.getenv("AI_ADAPTIVE_RISK", "1") == "1"
AI_RISK_MIN = float(os.getenv("AI_RISK_MIN", "0.5"))
AI_RISK_MAX = float(os.getenv("AI_RISK_MAX", "1.5"))
AI_BACKTEST_MIN_WINRATE = float(os.getenv("AI_BACKTEST_MIN_WINRATE", "55"))
AI_BACKTEST_MIN_TRADES = int(os.getenv("AI_BACKTEST_MIN_TRADES", "5"))

# V23 Institutional Pack
INSTITUTIONAL_MODE = os.getenv("INSTITUTIONAL_MODE", "1") == "1"
PRICE_CONSENSUS_FILTER = os.getenv("PRICE_CONSENSUS_FILTER", "1") == "1"
MAX_EXCHANGE_SPREAD_PERCENT = float(os.getenv("MAX_EXCHANGE_SPREAD_PERCENT", "0.85"))
ARBITRAGE_ALERT_PERCENT = float(os.getenv("ARBITRAGE_ALERT_PERCENT", "0.75"))
SNIPER_MAX_SECONDS = int(os.getenv("SNIPER_MAX_SECONDS", "18"))
SNIPER_WORKERS = int(os.getenv("SNIPER_WORKERS", "24"))
INSTITUTIONAL_MIN_SCORE = int(os.getenv("INSTITUTIONAL_MIN_SCORE", "88"))
INSTITUTIONAL_MIN_RR = float(os.getenv("INSTITUTIONAL_MIN_RR", "1.70"))
INSTITUTIONAL_MIN_VOLUME_RATIO = float(os.getenv("INSTITUTIONAL_MIN_VOLUME_RATIO", "1.25"))
AUTO_SCAN_ONLY_BEST = os.getenv("AUTO_SCAN_ONLY_BEST", "1") == "1"
AUTO_SCAN_COOLDOWN_HOURS = int(os.getenv("AUTO_SCAN_COOLDOWN_HOURS", "8"))
EXTREME_VOL_BLOCK_PERCENT = float(os.getenv("EXTREME_VOL_BLOCK_PERCENT", "4.5"))

BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com").rstrip("/")
COINGECKO_BASE_URL = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3").rstrip("/")
DEXSCREENER_BASE_URL = os.getenv("DEXSCREENER_BASE_URL", "https://api.dexscreener.com").rstrip("/")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)
CACHE = {}

WALLETS: Dict[str, List[str]] = {
    "Kraken": ["BTC", "ETH", "SOL", "LINK", "AVAX", "AAVE", "NEAR", "ADA", "DOT", "ATOM"],
    "Exodus": ["XRP", "XLM", "TRX", "HBAR", "ALGO", "ICP", "FIL", "INJ", "SUI", "LTC"],
    "Trust Wallet": ["ONDO", "ARB", "SEI", "JASMY", "POL", "OP", "ENA", "IMX", "RENDER", "TON"],
}
SYMBOL_ALIASES = {"RENDER": ["RENDERUSDT", "RNDRUSDT"], "POL": ["POLUSDT", "MATICUSDT"]}
COIN_EMOJI = {"BTC":"₿","ETH":"♦️","SOL":"☀️","XRP":"💧","ADA":"🔵","LINK":"🔗","AVAX":"🏔️","DOT":"⚫","ATOM":"⚛️","LTC":"Ł","TON":"💎","SUI":"🌊"}
MODES = {
    "Prudent": {"min_score": 78, "rsi_buy_max": 64, "rsi_sell_min": 36, "atr_mult_sl": 1.8, "rr1": 1.7, "rr2": 2.7},
    "Normal": {"min_score": 70, "rsi_buy_max": 68, "rsi_sell_min": 32, "atr_mult_sl": 1.6, "rr1": 1.5, "rr2": 2.3},
    "Agressif": {"min_score": 62, "rsi_buy_max": 72, "rsi_sell_min": 28, "atr_mult_sl": 1.35, "rr1": 1.3, "rr2": 2.0},
}
STATE = {"mode": "Normal", "auto_scan": False, "last_update_id": 0, "last_scan_chat_id": None, "pending_trade": {}, "risk_choice": {}, "analysis_by_coin": {}}

# ================= DB =================
def db_conn(): return sqlite3.connect(DB_PATH)

def init_db():
    with db_conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS analyses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, chat_id INTEGER NOT NULL,
            wallet TEXT, coin TEXT NOT NULL, symbol TEXT NOT NULL, signal TEXT NOT NULL,
            price REAL NOT NULL, entry_low REAL NOT NULL, entry_high REAL NOT NULL,
            sl REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL,
            score INTEGER NOT NULL, risk TEXT NOT NULL, mode TEXT NOT NULL, source TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS sent_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            score INTEGER NOT NULL,
            source TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS open_trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, chat_id INTEGER NOT NULL,
            coin TEXT NOT NULL, pair TEXT NOT NULL, side TEXT NOT NULL, amount REAL NOT NULL,
            entry REAL NOT NULL, sl REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL,
            risk_percent REAL NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', order_id TEXT,
            exit_price REAL DEFAULT 0, pnl_percent REAL DEFAULT 0, closed_ts INTEGER DEFAULT 0, note TEXT DEFAULT '',
            tp1_taken INTEGER DEFAULT 0, highest_price REAL DEFAULT 0, lowest_price REAL DEFAULT 0,
            strategy_snapshot TEXT DEFAULT ''
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS ai_memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            coin TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            note TEXT DEFAULT ''
        )""")
        
        cols=[r[1] for r in con.execute("PRAGMA table_info(open_trades)").fetchall()]
        for col,typ,default in [("exit_price","REAL","0"),("pnl_percent","REAL","0"),("closed_ts","INTEGER","0"),("note","TEXT","''"),
                                ("tp1_taken","INTEGER","0"),("highest_price","REAL","0"),("lowest_price","REAL","0"),
                                ("strategy_snapshot","TEXT","''")]:
            if col not in cols:
                con.execute(f"ALTER TABLE open_trades ADD COLUMN {col} {typ} DEFAULT {default}")
        con.commit()

# ================= TELEGRAM =================
def tg_send(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if keyboard: payload["reply_markup"] = keyboard
    try: requests.post(f"{TG_API}/sendMessage", json=payload, timeout=REQUEST_TIMEOUT)
    except Exception as e: print("tg_send error:", e)

def reply_keyboard(rows): return {"keyboard": [[{"text": x} for x in row] for row in rows], "resize_keyboard": True}

def main_menu_keyboard():
    return reply_keyboard([
        ["📊 Analyse Premium"],
        ["⚙️ Réglages Pro", "📈 Dashboard"],
        ["🎯 Sniper"],
        ["🧪 Backtest", "🔔 Auto Scan"],
        ["💼 Watchlist"],
    ])

def wallet_keyboard(back="🏠 Menu"):
    return reply_keyboard([["🏦 Kraken", "🦊 Exodus", "🛡️ Trust Wallet"], [back]])

def coins_keyboard(wallet, back_label="💼 Wallets"):
    coins = WALLETS.get(wallet, []); rows=[]
    for i in range(0, len(coins), 3): rows.append([f"{coin_emoji(c)} {c}" for c in coins[i:i+3]])
    rows.append([back_label, "🏠 Menu"]); return reply_keyboard(rows)

def settings_keyboard(): return reply_keyboard([["🛡️ Prudent", "⚖️ Normal", "🚀 Agressif"], ["🔐 Test Kraken", "🧹 Reset Paper Trades"], ["🏠 Menu"]])
def risk_keyboard():
    return reply_keyboard([["1%", "2%", "3%"], ["🏠 Menu"]])

def trade_inline_keyboard(coin=""):
    # Étape 1 : seulement les risques. Après clic, on remplace par Trade/Annuler.
    suffix = f":{coin}" if coin else ""
    return {"inline_keyboard": [[
        {"text": "1%", "callback_data": f"risk:1{suffix}"},
        {"text": "2%", "callback_data": f"risk:2{suffix}"},
        {"text": "3%", "callback_data": f"risk:3{suffix}"},
    ]]}

def confirm_trade_inline_keyboard(coin=""):
    suffix = f":{coin}" if coin else ""
    return {"inline_keyboard": [[
        {"text": "🚀 Trade", "callback_data": f"trade{suffix}"},
        {"text": "❌ Annuler", "callback_data": "cancel"},
    ]]}

def tg_edit_markup(chat_id, message_id, markup):
    try:
        requests.post(f"{TG_API}/editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": message_id, "reply_markup": markup}, timeout=REQUEST_TIMEOUT)
    except Exception as e:
        print("tg_edit_markup error:", e)

def tg_answer_callback(callback_id, text=""):
    try:
        requests.post(f"{TG_API}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text, "show_alert": False}, timeout=REQUEST_TIMEOUT)
    except Exception as e:
        print("tg_answer_callback error:", e)

def coin_emoji(coin): return COIN_EMOJI.get(coin, "🪙")

# ================= API + INDICATORS =================
def cached(key, ttl, fn):
    now=time.time(); item=CACHE.get(key)
    if item and now-item[0] < ttl: return item[1]
    val=fn(); CACHE[key]=(now,val); return val

def http_get(url, params=None):
    r=requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent":"LVBXNT-Crypto-Bot/1.0"})
    r.raise_for_status(); return r.json()

def resolve_binance_symbol(coin):
    for sym in SYMBOL_ALIASES.get(coin, [f"{coin}USDT"]):
        try:
            if http_get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", {"symbol":sym}).get("price"): return sym
        except Exception: pass
    return None

def get_klines(symbol, interval="1h", limit=240):
    def _fetch():
        data=http_get(f"{BINANCE_BASE_URL}/api/v3/klines", {"symbol":symbol,"interval":interval,"limit":limit})
        return [{"time":int(x[0]),"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4]),"volume":float(x[5])} for x in data]
    return cached(f"klines:{symbol}:{interval}:{limit}", CACHE_TTL_SECONDS, _fetch)

def get_market_context():
    def _fetch():
        try:
            d=http_get(f"{COINGECKO_BASE_URL}/global").get("data",{})
            return {"mcap_change":float(d.get("market_cap_change_percentage_24h_usd") or 0), "btc_dom":float(d.get("market_cap_percentage",{}).get("btc") or 0)}
        except Exception: return {"mcap_change":0,"btc_dom":0}
    return cached("coingecko:global", 180, _fetch)

def btc_volatility_guard():
    """Filtre volatilité/news: bloque les nouvelles entrées si BTC bouge trop fort en 1H."""
    if not NEWS_VOLATILITY_FILTER:
        return {"ok": True, "reason": "OFF", "btc_move": 0.0}
    try:
        rows = get_klines("BTCUSDT", "1h", 6)
        prev, last = rows[-2]["close"], rows[-1]["close"]
        move = abs((last - prev) / prev * 100) if prev else 0.0
        if move >= MAX_BTC_1H_MOVE_PERCENT:
            return {"ok": False, "reason": f"BTC trop volatile en 1H ({move:.2f}%)", "btc_move": move}
        return {"ok": True, "reason": "volatilité OK", "btc_move": move}
    except Exception:
        return {"ok": True, "reason": "guard indisponible", "btc_move": 0.0}

def market_regime(rows1, rows4, ctx):
    """Détecte Trend / Range / RiskOff pour pondérer le score."""
    try:
        t1 = trend(rows1); t4 = trend(rows4)
        closes = [r["close"] for r in rows1]
        aa = atr(rows1, 14) or closes[-1] * 0.015
        atr_pct = aa / closes[-1] * 100 if closes[-1] else 0
        if ctx.get("mcap_change", 0) < -3.0:
            return {"name": "RiskOff", "score_adjust": -10, "min_score_adjust": 8, "note": "marché global risqué"}
        if (t1["bullish"] and t4["bullish"]) or (t1["bearish"] and t4["bearish"]):
            return {"name": "Trend", "score_adjust": 5, "min_score_adjust": -2, "note": "marché directionnel"}
        if atr_pct < 1.2:
            return {"name": "Range", "score_adjust": -2, "min_score_adjust": 3, "note": "marché range / calme"}
        return {"name": "Mixed", "score_adjust": 0, "min_score_adjust": 0, "note": "marché mixte"}
    except Exception:
        return {"name": "Unknown", "score_adjust": 0, "min_score_adjust": 0, "note": "régime inconnu"}

def get_dex_info(coin):
    def _fetch():
        try:
            data=http_get(f"{DEXSCREENER_BASE_URL}/latest/dex/search", {"q":coin})
            pairs=data.get("pairs") or []
            filt=[p for p in pairs if p.get("baseToken",{}).get("symbol","").upper()==coin.upper()] or pairs[:5]
            best=None
            for p in filt:
                liq=float((p.get("liquidity") or {}).get("usd") or 0); vol=float((p.get("volume") or {}).get("h24") or 0)
                score=liq+vol*0.5
                if best is None or score>best[0]: best=(score,p)
            if not best: return {"liquidity":0,"volume24h":0,"dex":"N/A"}
            p=best[1]
            return {"liquidity":float((p.get("liquidity") or {}).get("usd") or 0), "volume24h":float((p.get("volume") or {}).get("h24") or 0), "dex":p.get("dexId","DEX")}
        except Exception: return {"liquidity":0,"volume24h":0,"dex":"N/A"}
    return cached(f"dex:{coin}", 180, _fetch)

def ema(vals, period):
    if len(vals)<period: return None
    k=2/(period+1); e=sum(vals[:period])/period
    for v in vals[period:]: e=v*k+e*(1-k)
    return e

def rsi(vals, period=14):
    if len(vals)<=period: return None
    gains=[]; losses=[]
    for i in range(1,len(vals)):
        d=vals[i]-vals[i-1]; gains.append(max(d,0)); losses.append(abs(min(d,0)))
    ag=sum(gains[-period:])/period; al=sum(losses[-period:])/period
    if al==0: return 100.0
    rs=ag/al; return 100-(100/(1+rs))

def atr(rows, period=14):
    if len(rows)<=period: return None
    trs=[]
    for i in range(1,len(rows)):
        trs.append(max(rows[i]["high"]-rows[i]["low"], abs(rows[i]["high"]-rows[i-1]["close"]), abs(rows[i]["low"]-rows[i-1]["close"])))
    return sum(trs[-period:])/period

def fmt_price(x):
    if x>=1000: return f"${x:,.0f}"
    if x>=1: return f"${x:,.3f}"
    return f"${x:.6f}"

def fmt_money(x):
    if x>=1_000_000: return f"${x/1_000_000:.1f}M"
    if x>=1_000: return f"${x/1_000:.1f}K"
    return f"${x:.0f}"

# ================= PRO ENGINE =================
def trend(rows):
    closes=[r["close"] for r in rows]; price=closes[-1]
    e20,e50,e200=ema(closes,20),ema(closes,50),ema(closes,200); rr=rsi(closes,14)
    bull=bool(e20 and e50 and e200 and e20>e50>e200 and price>e20)
    bear=bool(e20 and e50 and e200 and e20<e50<e200 and price<e20)
    return {"price":price,"ema20":e20,"ema50":e50,"ema200":e200,"rsi":rr,"bullish":bull,"bearish":bear,"direction":"Bullish" if bull else "Bearish" if bear else "Neutre"}


def detect_smc_ict(rows):
    if len(rows) < 80:
        return {"bias":"Neutre","score":0,"tags":[],"pd":"N/A"}
    last=rows[-1]
    highs=[r["high"] for r in rows[-30:-1]]; lows=[r["low"] for r in rows[-30:-1]]
    swing_high=max(highs); swing_low=min(lows); mid=(swing_high+swing_low)/2; price=last["close"]
    score=0; tags=[]; bias="Neutre"
    if price > swing_high:
        bias="Bullish"; score+=18; tags.append("BOS bullish")
    elif price < swing_low:
        bias="Bearish"; score+=18; tags.append("BOS bearish")
    if last["low"] < swing_low and price > swing_low:
        bias="Bullish"; score+=20; tags.append("liquidity sweep bas")
    if last["high"] > swing_high and price < swing_high:
        bias="Bearish"; score+=20; tags.append("liquidity sweep haut")
    fvg=False; fvg_low=None; fvg_high=None; fvg_type=None
    for i in range(len(rows)-18, len(rows)-2):
        a,c=rows[i],rows[i+2]
        if c["low"] > a["high"]:
            fvg=True; fvg_low=a["high"]; fvg_high=c["low"]; fvg_type="bullish"
        if c["high"] < a["low"]:
            fvg=True; fvg_low=c["high"]; fvg_high=a["low"]; fvg_type="bearish"
    if fvg:
        score+=12; tags.append("FVG")
    pd="Discount" if price < mid else "Premium"
    if bias=="Bullish" and pd=="Discount":
        score+=10; tags.append("discount")
    if bias=="Bearish" and pd=="Premium":
        score+=10; tags.append("premium")
    return {"bias":bias,"score":min(score,60),"tags":tags[:5],"pd":pd,"swing_high":swing_high,"swing_low":swing_low,"fvg_low":fvg_low,"fvg_high":fvg_high,"fvg_type":fvg_type}

def get_trade_status(symbol, signal, sl, tp1):
    if signal=="WAIT": return "⚪"
    try:
        px=float(http_get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", {"symbol":symbol}).get("price"))
        if signal=="BUY":
            if px>=tp1: return "✅"
            if px<=sl: return "❌"
        if signal=="SELL":
            if px<=tp1: return "✅"
            if px>=sl: return "❌"
        return "⏳"
    except Exception: return "⏳"

def trade_result_details(symbol, signal, entry, sl, tp1):
    """Statut + PnL estimé depuis le prix d'analyse."""
    if signal == "WAIT":
        return {"status": "⚪", "pnl": 0.0}
    try:
        px = float(http_get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", {"symbol": symbol}).get("price"))
        if signal == "BUY":
            live = (px - entry) / entry * 100 if entry else 0.0
            if px >= tp1: return {"status": "✅", "pnl": abs((tp1-entry)/entry*100)}
            if px <= sl: return {"status": "❌", "pnl": -abs((entry-sl)/entry*100)}
            return {"status": "⏳", "pnl": live}
        if signal == "SELL":
            live = (entry - px) / entry * 100 if entry else 0.0
            if px <= tp1: return {"status": "✅", "pnl": abs((entry-tp1)/entry*100)}
            if px >= sl: return {"status": "❌", "pnl": -abs((sl-entry)/entry*100)}
            return {"status": "⏳", "pnl": live}
    except Exception:
        pass
    return {"status": "⏳", "pnl": 0.0}

def was_recently_alerted(chat_id, symbol, signal, hours=6):
    try:
        since = int(time.time()) - hours * 3600
        with db_conn() as con:
            row = con.execute("SELECT id FROM sent_alerts WHERE chat_id=? AND symbol=? AND signal=? AND ts>=? ORDER BY ts DESC LIMIT 1", (chat_id, symbol, signal, since)).fetchone()
        return row is not None
    except Exception:
        return False

def mark_alert_sent(chat_id, a):
    try:
        with db_conn() as con:
            con.execute("INSERT INTO sent_alerts (ts,chat_id,symbol,signal,score,source) VALUES (?,?,?,?,?,?)", (int(time.time()), chat_id, a["symbol"], a["signal"], a["score"], a.get("source","auto")))
            con.commit()
    except Exception as e:
        print("mark_alert_sent error:", e)

def count_open_trades(chat_id):
    """Compte les vrais trades ouverts dans open_trades."""
    try:
        with db_conn() as con:
            row = con.execute("SELECT COUNT(*) FROM open_trades WHERE chat_id=? AND status='OPEN'", (chat_id,)).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0

def consecutive_loss_count(chat_id):
    try:
        with db_conn() as con:
            rows = con.execute("SELECT status FROM open_trades WHERE chat_id=? AND status IN ('SL','TP2','MANUAL_CLOSE') ORDER BY closed_ts DESC LIMIT 10", (chat_id,)).fetchall()
        losses = 0
        for (st,) in rows:
            if st == 'SL': losses += 1
            else: break
        return losses
    except Exception:
        return 0

def ai_strategy_profile(chat_id, coin=None):
    """IA locale: apprend depuis les trades fermés du journal.
    Pas de cloud, pas d'API payante. Ajuste score + risque selon performances réelles.
    """
    base = {"closed": 0, "wins": 0, "losses": 0, "winrate": None, "avg_pnl": 0.0,
            "score_adjust": 0, "min_score_adjust": 0, "risk_mult": 1.0, "note": "IA en apprentissage"}
    if not AI_SCORING or not chat_id:
        base["note"] = "IA OFF"
        return base
    try:
        with db_conn() as con:
            if coin:
                rows = con.execute("""SELECT status,pnl_percent FROM open_trades
                                      WHERE chat_id=? AND coin=? AND status IN ('SL','TP2','MANUAL_CLOSE')
                                      ORDER BY closed_ts DESC LIMIT 120""", (chat_id, coin)).fetchall()
            else:
                rows = con.execute("""SELECT status,pnl_percent FROM open_trades
                                      WHERE chat_id=? AND status IN ('SL','TP2','MANUAL_CLOSE')
                                      ORDER BY closed_ts DESC LIMIT 200""", (chat_id,)).fetchall()
        closed = len(rows)
        if closed == 0:
            return base
        wins = sum(1 for st,p in rows if st == 'TP2' or float(p or 0) > 0)
        losses = sum(1 for st,p in rows if st == 'SL' or float(p or 0) < 0)
        avg = sum(float(p or 0) for st,p in rows) / closed
        wr = (wins / closed * 100) if closed else None
        base.update({"closed": closed, "wins": wins, "losses": losses, "winrate": wr, "avg_pnl": avg})
        if closed < AI_MIN_CLOSED_TRADES:
            base["note"] = f"IA collecte données ({closed}/{AI_MIN_CLOSED_TRADES})"
            return base
        if wr >= 65 and avg > 0:
            base["score_adjust"] = min(AI_MAX_SCORE_ADJUST, 8)
            base["min_score_adjust"] = -3
            base["risk_mult"] = min(AI_RISK_MAX, 1.25)
            base["note"] = "IA positive"
        elif wr >= 55 and avg >= 0:
            base["score_adjust"] = 3
            base["risk_mult"] = 1.0
            base["note"] = "IA stable"
        elif wr <= 45 or avg < 0:
            base["score_adjust"] = -min(AI_MAX_SCORE_ADJUST, 10)
            base["min_score_adjust"] = 6
            base["risk_mult"] = max(AI_RISK_MIN, 0.5)
            base["note"] = "IA défensive"
        return base
    except Exception as e:
        print("ai_strategy_profile error:", e)
        return base

def adaptive_risk_percent(chat_id, requested_risk, coin=None):
    """Ajuste le risque automatiquement selon les stats réelles."""
    if not AI_ADAPTIVE_RISK:
        return float(requested_risk), "risque fixe"
    ai = ai_strategy_profile(chat_id, coin)
    adjusted = float(requested_risk) * float(ai.get("risk_mult", 1.0))
    adjusted = max(AI_RISK_MIN, min(AI_RISK_MAX, adjusted))
    return adjusted, ai.get("note", "IA")

def ai_dashboard_block(chat_id):
    ai = ai_strategy_profile(chat_id)
    wr = "N/A" if ai.get("winrate") is None else f"{ai['winrate']:.0f}%"
    return ("\n🧠 <b>IA BOT</b>\n"
            f"• État : <b>{ai.get('note')}</b>\n"
            f"• Trades appris : <b>{ai.get('closed',0)}</b>\n"
            f"• Winrate appris : <b>{wr}</b>\n"
            f"• Avg PnL : <b>{ai.get('avg_pnl',0):+.2f}%</b>\n"
            f"• Ajustement score : <b>{ai.get('score_adjust',0):+d}</b>\n")

def learning_stats(chat_id, coin):
    if not chat_id: return {"trades":0,"wins":0,"losses":0,"winrate":None,"adjust":0}
    try:
        with db_conn() as con:
            rows=con.execute("SELECT symbol,signal,sl,tp1 FROM analyses WHERE chat_id=? AND coin=? AND signal IN ('BUY','SELL') ORDER BY ts DESC LIMIT 40",(chat_id,coin)).fetchall()
        wins=losses=0
        for sym,sig,sl,tp1 in rows:
            st=get_trade_status(sym,sig,sl,tp1)
            if st=="✅": wins+=1
            elif st=="❌": losses+=1
        total=wins+losses
        if total<3: return {"trades":total,"wins":wins,"losses":losses,"winrate":None,"adjust":0}
        wr=wins/total*100; adj=5 if wr>=65 else -7 if wr<=40 else 0
        return {"trades":total,"wins":wins,"losses":losses,"winrate":wr,"adjust":adj}
    except Exception: return {"trades":0,"wins":0,"losses":0,"winrate":None,"adjust":0}

def backtest_symbol(symbol, mode="Normal", limit=500):
    def _run():
        try:
            rows=get_klines(symbol,"1h",limit)
            if len(rows)<260: return {"trades":0,"wins":0,"losses":0,"winrate":None}
            cfg=MODES.get(mode,MODES["Normal"]); wins=losses=trades=0
            for i in range(220,len(rows)-18):
                past=rows[:i]; closes=[r["close"] for r in past]; price=closes[-1]
                e20,e50,e200=ema(closes,20),ema(closes,50),ema(closes,200); rr=rsi(closes,14); aa=atr(past,14) or price*0.015
                vols=[r["volume"] for r in past]; avg=sum(vols[-20:])/20 if len(vols)>=20 else vols[-1]; vr=vols[-1]/avg if avg else 1
                buy=e20 and e50 and e200 and e20>e50>e200 and price>e20 and rr and 45<=rr<=cfg["rsi_buy_max"] and vr>=0.85
                sell=e20 and e50 and e200 and e20<e50<e200 and price<e20 and rr and cfg["rsi_sell_min"]<=rr<=55 and vr>=0.85
                if not (buy or sell): continue
                sig="BUY" if buy else "SELL"; sl=price-aa*cfg["atr_mult_sl"] if sig=="BUY" else price+aa*cfg["atr_mult_sl"]
                risk=abs(price-sl); tp1=price+risk*cfg["rr1"] if sig=="BUY" else price-risk*cfg["rr1"]
                out=None
                for f in rows[i:i+18]:
                    if sig=="BUY":
                        if f["low"]<=sl: out="loss"; break
                        if f["high"]>=tp1: out="win"; break
                    else:
                        if f["high"]>=sl: out="loss"; break
                        if f["low"]<=tp1: out="win"; break
                if out: trades+=1; wins += 1 if out=="win" else 0; losses += 1 if out=="loss" else 0
            return {"trades":trades,"wins":wins,"losses":losses,"winrate":wins/trades*100 if trades else None}
        except Exception: return {"trades":0,"wins":0,"losses":0,"winrate":None}
    return cached(f"backtest:{symbol}:{mode}:{limit}",900,_run)

def precise_entry_zone(price, aa, signal, smc):
    """Entrée plus précise: priorité FVG proche, sinon prix actuel avec micro-zone ATR."""
    buffer=max(aa*0.08, price*0.0008)
    entry=price
    reason="prix actuel"
    fl,fh=smc.get("fvg_low"),smc.get("fvg_high")
    ft=smc.get("fvg_type")
    if fl and fh and signal in ["BUY","SELL"]:
        mid=(float(fl)+float(fh))/2
        if abs(mid-price) <= aa*1.2:
            if signal=="BUY" and ft=="bullish":
                entry=mid; reason="FVG bullish proche"
            elif signal=="SELL" and ft=="bearish":
                entry=mid; reason="FVG bearish proche"
    return entry-buffer, entry+buffer, entry, reason

def analyze_coin(coin, wallet="", source="manual", chat_id=None):
    symbol=resolve_binance_symbol(coin)
    if not symbol: return {"ok":False,"coin":coin,"error":f"{coin}/USDT non disponible sur Binance"}
    rows1=get_klines(symbol,"1h",240); rows4=get_klines(symbol,"4h",220)
    if len(rows1)<200 or len(rows4)<200: return {"ok":False,"coin":coin,"error":"Pas assez de données marché"}
    t1,t4=trend(rows1),trend(rows4); closes=[r["close"] for r in rows1]; vols=[r["volume"] for r in rows1]
    price=closes[-1]; aa=atr(rows1,14) or price*0.015; vr=vols[-1]/(sum(vols[-20:])/20) if len(vols)>=20 and sum(vols[-20:]) else 1
    ctx=get_market_context(); dex=get_dex_info(coin); cfg=MODES[STATE["mode"]]; learn=learning_stats(chat_id,coin); bt=backtest_symbol(symbol,STATE["mode"]); smc1=detect_smc_ict(rows1); smc4=detect_smc_ict(rows4); regime=market_regime(rows1, rows4, ctx); vol_guard=btc_volatility_guard(); ai=ai_strategy_profile(chat_id, coin)
    mtf_buy=t1["bullish"] and t4["bullish"]; mtf_sell=t1["bearish"] and t4["bearish"]; mtf=mtf_buy or mtf_sell
    mom_buy=t1["rsi"] is not None and 45<=t1["rsi"]<=cfg["rsi_buy_max"]; mom_sell=t1["rsi"] is not None and cfg["rsi_sell_min"]<=t1["rsi"]<=55
    liq_ok=dex["liquidity"]>=50000 or coin in ["BTC","ETH","SOL","XRP","ADA","AVAX","LINK","LTC","TON"]
    smc_buy = smc1["bias"]=="Bullish" and smc4["bias"] in ["Bullish","Neutre"]
    smc_sell = smc1["bias"]=="Bearish" and smc4["bias"] in ["Bearish","Neutre"]
    score=0; reasons=[]
    if t1["bullish"] or t1["bearish"]: score+=25; reasons.append("tendance 1H propre")
    elif t1["ema20"] and t1["ema50"] and ((t1["ema20"]>t1["ema50"] and price>t1["ema50"]) or (t1["ema20"]<t1["ema50"] and price<t1["ema50"])): score+=15; reasons.append("tendance 1H moyenne")
    if mtf: score+=20; reasons.append("confirmation 1H + 4H")
    if mom_buy or mom_sell: score+=15; reasons.append("RSI exploitable")
    if vr>=0.85: score+=10; reasons.append("volume correct")
    if ctx["mcap_change"]>-2.5: score+=8; reasons.append("marché global OK")
    if liq_ok: score+=8; reasons.append("liquidité OK")
    if smc1["score"]>=25: score+=min(18, smc1["score"]//2); reasons.append("SMC/ICT validé")
    if smc_buy or smc_sell: score+=8; reasons.append("bias SMC aligné")
    if vr>=1.4: score+=4; reasons.append("volume spike")
    if bt["winrate"] is not None and bt["winrate"]>=60 and bt["trades"]>=5: score+=5; reasons.append("backtest positif")
    ai_note="IA neutre"
    ai_min_score=cfg["min_score"]
    if learn["adjust"]>0:
        score+=learn["adjust"]; ai_min_score=max(62,ai_min_score-3); ai_note="IA positive : coin souvent gagnant"; reasons.append("IA : coin performant")
    elif learn["adjust"]<0:
        score+=learn["adjust"]; ai_min_score+=5; ai_note="IA prudente : coin souvent perdant"; reasons.append("IA : prudence renforcée")
    if DYNAMIC_SCORING:
        score += regime.get("score_adjust", 0)
        ai_min_score += regime.get("min_score_adjust", 0)
        reasons.append("Régime : " + regime.get("note", "N/A"))
    if AI_SCORING:
        score += ai.get("score_adjust", 0)
        ai_min_score += ai.get("min_score_adjust", 0)
        reasons.append("IA : " + ai.get("note", "apprentissage"))
    if not vol_guard.get("ok", True):
        score -= 12
        ai_min_score += 10
        reasons.append("Volatilité/news : " + vol_guard.get("reason", "risque élevé"))
    if bt["winrate"] is not None and bt["trades"]>=8:
        if bt["winrate"]>=65: ai_min_score=max(60,ai_min_score-2); reasons.append("IA : backtest solide")
        elif bt["winrate"]<45: ai_min_score+=5; reasons.append("IA : backtest faible")
    score=max(0,min(100,int(score)))
    signal="WAIT"; direction="Neutre"; bt_ok=bt["winrate"] is None or bt["trades"] < AI_BACKTEST_MIN_TRADES or bt["winrate"]>=AI_BACKTEST_MIN_WINRATE
    if mtf_buy and mom_buy and (smc_buy or smc1["score"]>=30) and score>=ai_min_score and bt_ok: signal="BUY"; direction="Bullish"
    elif mtf_sell and mom_sell and (smc_sell or smc1["score"]>=30) and score>=ai_min_score and bt_ok: signal="SELL"; direction="Bearish"
    entry_low, entry_high, entry_mid, entry_reason = precise_entry_zone(price, aa, signal, smc1)
    if signal=="BUY": sl=entry_mid-aa*cfg["atr_mult_sl"]; risk=entry_mid-sl; tp1=entry_mid+risk*cfg["rr1"]; tp2=entry_mid+risk*cfg["rr2"]
    elif signal=="SELL": sl=entry_mid+aa*cfg["atr_mult_sl"]; risk=sl-entry_mid; tp1=entry_mid-risk*cfg["rr1"]; tp2=entry_mid-risk*cfg["rr2"]
    else: sl=price-aa*1.4; tp1=price+aa*1.8; tp2=price+aa*2.8; entry_mid=price; entry_reason="attente"
    rr_value = abs((tp1-entry_mid)/(entry_mid-sl)) if (entry_mid-sl) else 0
    risk_txt="Faible" if score>=82 else "Moyen" if score>=70 else "Élevé"
    profitable=signal in ["BUY","SELL"] and score>=70 and risk_txt in ["Faible","Moyen"] and mtf and rr_value>=MIN_RR and vr>=MIN_VOLUME_RATIO and vol_guard.get("ok", True)
    if signal in ["BUY","SELL"] and not profitable:
        signal="WAIT"; direction="Neutre"; reasons.append("filtre rentable : setup rejeté")
    return {"ok":True,"wallet":wallet,"coin":coin,"symbol":symbol,"pair":f"{coin}/USDT","price":price,"ema20":t1["ema20"],"ema50":t1["ema50"],"ema200":t1["ema200"],"rsi":t1["rsi"],"atr":aa,"vol_ratio":vr,"dex":dex,"context":ctx,"score":score,"signal":signal,"direction":direction,"entry_low":entry_low,"entry_high":entry_high,"entry":entry_mid,"entry_reason":entry_reason,"sl":sl,"tp1":tp1,"tp2":tp2,"risk":risk_txt,"mode":STATE["mode"],"reasons":reasons,"source":source,"mtf":{"confirm":mtf,"direction_1h":t1["direction"],"direction_4h":t4["direction"],"rsi_4h":t4["rsi"]},"learning":learn,"backtest":bt,"ai_profile":ai,"ai_note":ai_note,"ai_min_score":ai_min_score,"profitable_ok":profitable,"smc":smc1,"smc4":smc4,"regime":regime,"vol_guard":vol_guard,"rr":rr_value,"chat_id":chat_id}

def is_clean_trade(a, min_score=70):
    if not a.get("ok") or a.get("signal") not in ["BUY", "SELL"]:
        return False
    smc = a.get("smc", {})
    tags = " ".join(smc.get("tags", [])).lower()
    elite_smc_ok = (("bos" in tags) and ("liquidity" in tags or "sweep" in tags) and ("fvg" in tags)) or smc.get("score", 0) >= 42
    basic_ok = a.get("score", 0) >= min_score and a.get("risk") in ["Faible", "Moyen"] and a.get("mtf", {}).get("confirm")
    quality_ok = a.get("rr", 0) >= MIN_RR and a.get("vol_ratio", 0) >= MIN_VOLUME_RATIO and a.get("vol_guard", {}).get("ok", True)
    if ELITE_MODE:
        return bool(basic_ok and quality_ok and elite_smc_ok)
    return bool(basic_ok and quality_ok)

def signal_message(a):
    if not a.get("ok"):
        return f"⚠️ <b>Analyse impossible</b>\n\n🪙 {a.get('coin','')}\n❌ {a.get('error','Erreur inconnue')}"
    sig_emoji="🟢" if a["signal"]=="BUY" else "🔴" if a["signal"]=="SELL" else "⚪"
    verdict="✅ TRADE" if a["signal"] in ["BUY","SELL"] and a.get("profitable_ok") else "⚪ ATTENDRE"
    mtf=a.get("mtf",{}); smc=a.get("smc",{})
    rr=a.get("rr") or (abs((a["tp1"]-a.get("entry",a["price"]))/(a.get("entry",a["price"])-a["sl"])) if (a.get("entry",a["price"])-a["sl"]) else 0)
    setup=[]
    if mtf.get("confirm"): setup.append("MTF 1H+4H")
    setup += smc.get("tags",[])[:3]
    if a.get("vol_ratio",0)>=1: setup.append("Volume OK")
    setup_txt=" • ".join(setup[:5]) or "Setup pas assez propre"
    remember_pending_trade(a.get("chat_id"), a)
    extra=""
    return f"""💎 <b>LVBXNT SIGNAL</b>
━━━━━━━━━━━━━━━━━━━━
🪙 <b>{a['pair']}</b> | {sig_emoji} <b>{a['signal']}</b>
🏁 Verdict : <b>{verdict}</b>

💰 Prix : <b>{fmt_price(a['price'])}</b>
🎯 Entrée limit : <b>{fmt_price(a.get('entry', a['price']))}</b>
🛑 SL : <b>{fmt_price(a['sl'])}</b>
🥇 TP1 : <b>{fmt_price(a['tp1'])}</b>
🥈 TP2 : <b>{fmt_price(a['tp2'])}</b>

🧠 Score : <b>{a['score']}%</b>
⚠️ Risque setup : <b>{a['risk']}</b>
📐 R/R : <b>{rr:.2f}</b>
📊 RSI : <b>{a['rsi']:.1f}</b> | Vol : <b>{a['vol_ratio']:.2f}x</b>
🏦 SMC/ICT : <b>{smc.get('bias','N/A')}</b> • {smc.get('pd','N/A')}
🌍 Régime : <b>{a.get('regime',{}).get('name','N/A')}</b>
🧠 IA : <b>{a.get('ai_profile',{}).get('note','apprentissage')}</b>

✅ <b>Pourquoi ?</b>
{setup_txt}

📍 Précision entrée : <b>{a.get('entry_reason','prix actuel')}</b>{extra}"""

def kraken_status_message():
    live = "ON" if ENABLE_LIVE_TRADING else "OFF / PAPER"
    keys = "OK" if KRAKEN_API_KEY and KRAKEN_API_SECRET else "MANQUANTES"
    return f"🤖 <b>Kraken Pro</b>\n━━━━━━━━━━━━━━━━━━━━\n🔐 Clés API : <b>{keys}</b>\n💸 Live trading : <b>{live}</b>\n📊 Capital calcul : <b>${ACCOUNT_EQUITY_USD:.2f}</b>\n🧱 Max/trade : <b>${MAX_TRADE_QUOTE_USD:.2f}</b>"

def remember_pending_trade(chat_id, a):
    if not chat_id or not a:
        return
    coin = a.get("coin")
    if coin:
        STATE.setdefault("analysis_by_coin", {}).setdefault(chat_id, {})[coin] = a
    if a.get("signal") in ["BUY","SELL"]:
        STATE["pending_trade"][chat_id]=a

def today_loss_count(chat_id):
    try:
        start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        with db_conn() as con:
            row = con.execute("SELECT COUNT(*) FROM open_trades WHERE chat_id=? AND status='SL' AND closed_ts>=?", (chat_id, start)).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0

def today_pnl_percent(chat_id):
    try:
        start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        with db_conn() as con:
            row = con.execute("SELECT COALESCE(SUM(pnl_percent),0) FROM open_trades WHERE chat_id=? AND closed_ts>=?", (chat_id, start)).fetchone()
        return float(row[0] or 0)
    except Exception:
        return 0.0

def reset_paper_trades(chat_id):
    try:
        now=int(time.time())
        with db_conn() as con:
            cur=con.execute("""UPDATE open_trades SET status='MANUAL_CLOSE', exit_price=entry, pnl_percent=0, closed_ts=?, note='RESET_PAPER'
                              WHERE chat_id=? AND status='OPEN' AND (order_id='PAPER' OR order_id LIKE 'PAPER%')""", (now, chat_id))
            con.commit()
        return f"🧹 Paper trades reset : <b>{cur.rowcount}</b> trade(s) fermé(s)."
    except Exception as e:
        return f"❌ Reset impossible : <code>{str(e)[:300]}</code>"

def test_kraken_connection():
    if ccxt is None:
        return "❌ ccxt non installé. Lance : <code>pip install ccxt</code>"
    if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
        return "❌ Clés Kraken manquantes dans .env"
    try:
        ex=ccxt.kraken({"apiKey":KRAKEN_API_KEY,"secret":KRAKEN_API_SECRET,"enableRateLimit":True})
        ex.load_markets()
        bal=ex.fetch_balance()
        usdt=float((bal.get('USDT') or {}).get('free') or 0)
        usd=float((bal.get('USD') or {}).get('free') or 0)
        return f"✅ Kraken connecté.\n💵 USD dispo : <b>{usd:.2f}</b>\n💵 USDT dispo : <b>{usdt:.2f}</b>\n🤖 Live trading : <b>{'ON' if ENABLE_LIVE_TRADING else 'OFF / PAPER'}</b>"
    except Exception as e:
        return f"❌ Connexion Kraken échouée : <code>{str(e)[:500]}</code>"

def account_safety_ok(chat_id, a=None):
    if not SAFE_MODE:
        return True, "OK"
    if count_open_trades(chat_id) >= MAX_OPEN_TRADES:
        return False, f"⛔ Safe Mode : max {MAX_OPEN_TRADES} trades ouverts atteint."
    if today_loss_count(chat_id) >= DAILY_MAX_LOSSES:
        return False, f"⛔ Safe Mode : {DAILY_MAX_LOSSES} pertes aujourd’hui. Bot stoppé pour protéger le capital."
    if consecutive_loss_count(chat_id) >= MAX_CONSECUTIVE_LOSSES:
        return False, f"⛔ Safe Mode : {MAX_CONSECUTIVE_LOSSES} pertes consécutives. Pause obligatoire."
    if today_pnl_percent(chat_id) <= -abs(MAX_DAILY_LOSS_PERCENT):
        return False, f"⛔ Safe Mode : perte journalière max atteinte ({today_pnl_percent(chat_id):+.2f}%)."
    if a and a.get("score",0) < MIN_TRADE_SCORE:
        return False, f"⛔ Safe Mode : score {a.get('score',0)}% inférieur au minimum {MIN_TRADE_SCORE}%."
    if a and a.get("vol_ratio", 1) < MIN_VOLUME_RATIO:
        return False, f"⛔ Safe Mode : volume trop faible ({a.get('vol_ratio',0):.2f}x)."
    if a and a.get("rr", 0) < MIN_RR:
        return False, f"⛔ Safe Mode : R/R trop faible ({a.get('rr',0):.2f})."
    if a and ELITE_MODE and not is_clean_trade(a, MIN_TRADE_SCORE):
        return False, "⛔ Elite Mode : setup pas assez propre (SMC/MTF/volume/RR)."
    guard = btc_volatility_guard()
    if a and not guard.get("ok", True):
        return False, f"⛔ Filtre volatilité/news : {guard.get('reason')}."
    return True, "OK"

def get_account_equity_usd():
    if not ENABLE_LIVE_TRADING or ccxt is None or not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
        return ACCOUNT_EQUITY_USD
    try:
        ex = ccxt.kraken({"apiKey": KRAKEN_API_KEY, "secret": KRAKEN_API_SECRET, "enableRateLimit": True})
        bal = ex.fetch_balance()
        usd = float((bal.get('USD') or {}).get('free') or 0)
        usdt = float((bal.get('USDT') or {}).get('free') or 0)
        return max(usd + usdt, ACCOUNT_EQUITY_USD)
    except Exception:
        return ACCOUNT_EQUITY_USD

def calculate_position(a, risk_percent):
    entry=float(a.get("entry", a["price"])); sl=float(a["sl"]); stop=abs(entry-sl)
    if stop <= 0: raise ValueError("SL invalide")
    equity=get_account_equity_usd(); risk_usd=equity*(risk_percent/100); amount=risk_usd/stop; quote=amount*entry
    if quote > MAX_TRADE_QUOTE_USD:
        quote=MAX_TRADE_QUOTE_USD; amount=quote/entry
    return {"amount":amount,"quote":quote}

def record_open_trade(chat_id, a, side, amount, risk_percent, order_id="PAPER"):
    try:
        entry = float(a.get("entry", a["price"]))
        snapshot = ", ".join(a.get("reasons", [])[:6])
        with db_conn() as con:
            con.execute("""INSERT INTO open_trades
                (ts,chat_id,coin,pair,side,amount,entry,sl,tp1,tp2,risk_percent,status,order_id,highest_price,lowest_price,strategy_snapshot)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(time.time()), chat_id, a["coin"], f"{a['coin']}/USDT", side, float(amount), entry,
                 float(a["sl"]), float(a["tp1"]), float(a["tp2"]), float(risk_percent), "OPEN", str(order_id),
                 entry, entry, snapshot))
            con.commit()
    except Exception as e:
        print("record_open_trade error:", e)

def execute_kraken_trade(chat_id, risk_percent):
    a=STATE.get("pending_trade",{}).get(chat_id)
    if not a: return "⚠️ Aucun trade valide en attente. Analyse Premium ou Sniper doit trouver BUY ou SELL avant d.exécuter."
    ok, reason = account_safety_ok(chat_id, a)
    if not ok: return reason
    risk_percent, risk_note = adaptive_risk_percent(chat_id, risk_percent, a.get("coin"))
    side="buy" if a["signal"]=="BUY" else "sell"; pair=f"{a['coin']}/USDT"; pos=calculate_position(a,risk_percent)
    if side=="sell" and os.getenv("ALLOW_SPOT_SELL","0")!="1":
        return "⛔ SELL auto bloqué en spot. Active ALLOW_SPOT_SELL=1 seulement si tu possèdes déjà le coin."
    msg=f"🤖 <b>Trade Kraken</b>\n━━━━━━━━━━━━━━━━━━━━\n🪙 {pair} • <b>{a['signal']}</b>\n⚠️ Risque : <b>{risk_percent:.0f}%</b>\n💵 Montant : <b>${pos['quote']:.2f}</b>\n📦 Quantité : <b>{pos['amount']:.8f}</b>\n🎯 Entrée : <b>{fmt_price(a.get('entry', a['price']))}</b>\n🛑 SL : <b>{fmt_price(a['sl'])}</b>\n🥇 TP1 : <b>{fmt_price(a['tp1'])}</b>\n🥈 TP2 : <b>{fmt_price(a['tp2'])}</b>"
    if not ENABLE_LIVE_TRADING:
        record_open_trade(chat_id,a,side,pos["amount"],risk_percent,"PAPER")
        return msg + "\n\n🧪 PAPER MODE : trade enregistré, aucun ordre réel envoyé."
    if ccxt is None:
        return msg + "\n\n❌ ccxt non installé. Lance : pip install ccxt"
    if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
        return msg + "\n\n❌ Clés Kraken manquantes dans .env"
    try:
        ex=ccxt.kraken({"apiKey":KRAKEN_API_KEY,"secret":KRAKEN_API_SECRET,"enableRateLimit":True}); ex.load_markets()
        order=ex.create_market_order(pair, side, pos["amount"])
        record_open_trade(chat_id,a,side,pos["amount"],risk_percent,order.get("id","LIVE"))
        return msg + f"\n\n✅ Ordre marché envoyé. ID : <code>{order.get('id','N/A')}</code>\n🛡️ Le bot surveille TP/SL automatiquement."
    except Exception as e:
        return msg + f"\n\n❌ Erreur Kraken : <code>{str(e)[:400]}</code>"


def save_analysis(chat_id, a):
    if not a.get("ok"): return
    with db_conn() as con:
        con.execute("INSERT INTO analyses (ts,chat_id,wallet,coin,symbol,signal,price,entry_low,entry_high,sl,tp1,tp2,score,risk,mode,source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(int(time.time()),chat_id,a["wallet"],a["coin"],a["symbol"],a["signal"],a["price"],a["entry_low"],a["entry_high"],a["sl"],a["tp1"],a["tp2"],a["score"],a["risk"],a["mode"],a["source"]))
        con.commit()

# ================= MENUS =================
def send_home(chat_id):
    tg_send(chat_id, f"""🚀 <b>LVBXNT Crypto Bot</b>

✨ Bot premium prêt à analyser le marché.
⚙️ Mode : <b>{STATE['mode']}</b>
🔔 Auto Scan : <b>{'ON' if STATE['auto_scan'] else 'OFF'}</b>

👇 Choisis une action""", main_menu_keyboard())

def send_settings(chat_id):
    tg_send(chat_id, f"""⚙️ <b>Réglages Pro</b>

• Mode actif : <b>{STATE['mode']}</b>
• IA Scoring : <b>{'ON' if AI_SCORING else 'OFF'}</b>
• Risque adaptatif : <b>{'ON' if AI_ADAPTIVE_RISK else 'OFF'}</b>

Modes disponibles :
• 🛡️ Prudent = moins d'entrées, setups propres
• ⚖️ Normal = équilibre
• 🚀 Agressif = plus d'opportunités, plus risqué""", settings_keyboard())

def send_wallets(chat_id, purpose="watchlist"):
    title="💼 <b>Watchlist par portefeuille</b>" if purpose=="watchlist" else "📊 <b>Analyse Premium</b>"
    tg_send(chat_id, f"{title}\n\nChoisis ton portefeuille 👇\n\n🏦 Kraken\n🦊 Exodus\n🛡️ Trust Wallet", wallet_keyboard("🏠 Menu"))

def send_wallet_coins(chat_id, wallet, purpose="analysis"):
    coins=WALLETS[wallet]; msg=f"💼 <b>{wallet}</b>\n\n"+"\n".join([f"{coin_emoji(c)} {c}/USDT" for c in coins])+"\n\n👇 Choisis la crypto à analyser"
    tg_send(chat_id,msg,coins_keyboard(wallet))

def dashboard(chat_id):
    with db_conn() as con:
        rows=con.execute("SELECT ts,wallet,coin,symbol,signal,price,sl,tp1,tp2,score,source FROM analyses WHERE chat_id=? ORDER BY ts DESC LIMIT 50",(chat_id,)).fetchall()
    if not rows:
        tg_send(chat_id,"📈 <b>Dashboard Stats</b>\n\n📦 Total analyses : <b>0</b>\n🏆 Winrate : <b>N/A</b>\n💰 Profit estimé : <b>0.00%</b>\n📌 Trades ouverts : <b>0/max</b>\n\n📁 Historique :\n• Aucune encore",main_menu_keyboard()); return
    by_date={}; wins=losses=open_trades=closed=0; pnl_total=0.0; coin_perf={}
    for ts,wallet,coin,symbol,signal,price,sl,tp1,tp2,score,source in rows:
        d=datetime.fromtimestamp(ts).strftime("%d %m %Y")
        det=trade_result_details(symbol,signal,price,sl,tp1); st=det["status"]; pnl=det["pnl"]
        by_date.setdefault(d,[]).append((coin,signal,score,st,source,pnl))
        if st=="✅": wins+=1; closed+=1; pnl_total+=pnl
        elif st=="❌": losses+=1; closed+=1; pnl_total+=pnl
        elif st=="⏳" and signal in ["BUY","SELL"]: open_trades+=1
        coin_perf.setdefault(coin,0.0); coin_perf[coin]+=pnl
    winrate=(wins/closed*100) if closed else None
    best=sorted(coin_perf.items(), key=lambda x:x[1], reverse=True)[:3]
    worst=sorted(coin_perf.items(), key=lambda x:x[1])[:2]
    msg="📈 <b>Dashboard Stats</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    msg+=f"📦 Total analyses : <b>{len(rows)}</b>\n"
    msg+=f"🏆 Winrate : <b>{winrate:.0f}%</b>\n" if winrate is not None else "🏆 Winrate : <b>N/A</b>\n"
    msg+=f"✅ Gagnés : <b>{wins}</b> | ❌ Perdus : <b>{losses}</b>\n"
    msg+=f"💰 Profit estimé : <b>{pnl_total:+.2f}%</b>\n"
    msg+=f"📌 Trades ouverts : <b>{open_trades}/max</b>\n"
    if best:
        msg+="\n🔥 <b>Meilleurs coins</b>\n" + "".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin,p in best])
    if worst:
        neg="".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin,p in worst if p<0])
        if neg: msg+="\n⚠️ <b>Coins à surveiller</b>\n" + neg
    msg+="\n📁 <b>Historique par date</b>\n"
    for d,items in by_date.items():
        msg+=f"\n📅 <b>{d}</b>\n"
        for coin,signal,score,st,source,pnl in items[:8]: msg+=f"{st} {coin}/USDT • {signal} • {score}% • {pnl:+.2f}% • {source}\n"
    tg_send(chat_id,msg[:3600] + ai_dashboard_block(chat_id),main_menu_keyboard())

def run_sniper(chat_id):
    """Sniper rapide = analyse toutes tes cryptos et affiche max 3 setups. Aucun trade automatique."""
    tg_send(chat_id, "🎯 <b>Sniper</b>\n\nScan ultra rapide des opportunités... ⏳")
    results=[]

    def _scan_one(item):
        wallet, coin = item
        try:
            a = analyze_coin(coin, wallet, "sniper", chat_id)
            bt = a.get("backtest", {}) if a.get("ok") else {}
            if is_clean_trade(a, MIN_SNIPER_SCORE) and (bt.get("winrate") is None or bt.get("winrate", 0) >= 55):
                return a
        except Exception as e:
            print("sniper scan error", item, e)
        return None

    items=[(wallet, coin) for wallet, coins in WALLETS.items() for coin in coins]
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=16) as ex:
            futs=[ex.submit(_scan_one, item) for item in items]
            for fut in as_completed(futs, timeout=45):
                a=fut.result()
                if a: results.append(a)
    except Exception as e:
        print("sniper parallel fallback:", e)
        for item in items:
            a=_scan_one(item)
            if a: results.append(a)

    picks=sorted(results,key=lambda x:(x["score"],x.get("backtest",{}).get("winrate") or 0),reverse=True)[:3]
    if not picks:
        tg_send(chat_id,"🎯 <b>Sniper</b>\n\n❌ <b>NO TRADE</b>\n\nAucun setup super qualifié maintenant. Le bot préfère attendre.",main_menu_keyboard())
        return

    tg_send(chat_id,f"🎯 <b>Sniper</b>\n\n✅ <b>{len(picks)}</b> setup(s) super qualifié(s) trouvé(s).\n👇 Choisis un risque sous l’analyse, puis Trade.",main_menu_keyboard())
    for i,a in enumerate(picks,1):
        save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
        if i==1 and a.get("signal") in ["BUY","SELL"]:
            STATE["pending_trade"][chat_id]=a
        tg_send(chat_id, f"🏆 <b>SNIPER #{i}</b>\n" + signal_message(a), trade_inline_keyboard(a.get("coin", "")))

def run_backtest(chat_id):
    tg_send(chat_id,"🧪 <b>Backtest automatique</b>\n\nJe teste tes 30 cryptos sur les dernières bougies 1H... ⏳")
    results=[]
    for wallet,coins in WALLETS.items():
        for coin in coins:
            sym=resolve_binance_symbol(coin)
            if sym:
                bt=backtest_symbol(sym,STATE["mode"])
                if bt.get("trades",0)>0: results.append((coin,wallet,bt))
    results.sort(key=lambda x:(x[2].get("winrate") or 0,x[2].get("trades") or 0), reverse=True)
    if not results: tg_send(chat_id,"🧪 <b>Backtest</b>\n\nAucun résultat exploitable pour le moment.",main_menu_keyboard()); return
    msg="🧪 <b>Backtest automatique</b>\n\n🏆 Top résultats :\n"
    for coin,wallet,bt in results[:12]: msg+=f"\n{coin_emoji(coin)} <b>{coin}/USDT</b> • {wallet}\n✅ Winrate : <b>{bt['winrate']:.0f}%</b> • Trades : <b>{bt['trades']}</b> • {bt['wins']}W/{bt['losses']}L\n"
    msg+="\n⚠️ Backtest simple = aide décision, pas garantie."
    tg_send(chat_id,msg[:3900],main_menu_keyboard())

def run_auto_scan(chat_id):
    STATE["auto_scan"]=not STATE["auto_scan"]; STATE["last_scan_chat_id"]=chat_id if STATE["auto_scan"] else None
    status = "ON" if STATE["auto_scan"] else "OFF"
    full = "FULL AUTO activé" if STATE["auto_scan"] else "FULL AUTO désactivé"
    tg_send(chat_id, f"🔔 <b>Auto Scan : {status}</b>\n🤖 <b>{full}</b>", main_menu_keyboard())

def auto_scan_loop():
    """Auto Scan exclusif : scan permanent + trade Kraken auto 1% uniquement sur setups élite."""
    while True:
        time.sleep(SCAN_INTERVAL_SECONDS)
        chat_id=STATE.get("last_scan_chat_id")
        if STATE.get("auto_scan") and chat_id:
            try:
                if count_open_trades(chat_id) >= MAX_OPEN_TRADES:
                    continue
                guard = btc_volatility_guard()
                if not guard.get("ok", True):
                    continue
                items=[(wallet, coin) for wallet, coins in WALLETS.items() for coin in coins]
                results=[]
                def _scan(item):
                    wallet, coin = item
                    try:
                        a=analyze_coin(coin,wallet,"auto_alert",chat_id)
                        if is_clean_trade(a,MIN_AUTOTRADE_SCORE) and not was_recently_alerted(chat_id,a["symbol"],a["signal"],6):
                            ok_safe, _ = account_safety_ok(chat_id, a)
                            if ok_safe: return a
                    except Exception as e:
                        print("autoscan pair error", item, e)
                    return None
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=12) as ex:
                    futs=[ex.submit(_scan, item) for item in items]
                    for fut in as_completed(futs, timeout=50):
                        a=fut.result()
                        if a: results.append(a)
                slots=max(0,MAX_OPEN_TRADES-count_open_trades(chat_id))
                picks=sorted(results,key=lambda x:(x["score"], x.get("rr", 0), x.get("vol_ratio", 0)),reverse=True)[:slots]
                for a in picks:
                    save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
                    STATE["pending_trade"][chat_id]=a
                    tg_send(chat_id,"🔔 <b>Auto Scan Elite</b>\n🤖 Trade auto 1% détecté", main_menu_keyboard())
                    tg_send(chat_id,signal_message(a), main_menu_keyboard())
                    tg_send(chat_id, execute_kraken_trade(chat_id, AUTO_TRADE_RISK_PERCENT), main_menu_keyboard())
            except Exception as e: print("autoscan error:",e)


def close_trade_market(pair, side, amount):
    """Ferme un trade en live. Pour BUY on vend, pour SELL on rachète."""
    if not ENABLE_LIVE_TRADING:
        return {"id":"PAPER_CLOSE"}
    if ccxt is None:
        raise Exception("ccxt non installé")
    ex=ccxt.kraken({"apiKey":KRAKEN_API_KEY,"secret":KRAKEN_API_SECRET,"enableRateLimit":True}); ex.load_markets()
    close_side="sell" if side=="buy" else "buy"
    return ex.create_market_order(pair, close_side, amount)

def monitor_open_trades_loop():
    """Surveille TP/SL, sécurise 50% à TP1, breakeven et trailing stop."""
    while True:
        time.sleep(30)
        try:
            with db_conn() as con:
                rows=con.execute("""SELECT id,chat_id,coin,pair,side,amount,entry,sl,tp1,tp2,tp1_taken,highest_price,lowest_price
                                    FROM open_trades WHERE status='OPEN' ORDER BY ts ASC LIMIT 20""").fetchall()
            for tid,chat_id,coin,pair,side,amount,entry,sl,tp1,tp2,tp1_taken,highest_price,lowest_price in rows:
                sym=resolve_binance_symbol(coin)
                if not sym: continue
                px=float(http_get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", {"symbol":sym}).get("price"))
                highest_price=max(float(highest_price or entry), px)
                lowest_price=min(float(lowest_price or entry), px)
                with db_conn() as con:
                    con.execute("UPDATE open_trades SET highest_price=?, lowest_price=? WHERE id=?", (highest_price, lowest_price, tid)); con.commit()

                hit=None; pnl=0.0
                if side=="buy":
                    if px <= sl:
                        hit="SL"; pnl=(px-entry)/entry*100
                    elif px >= tp2:
                        hit="TP2"; pnl=(px-entry)/entry*100
                    elif not tp1_taken and px >= tp1:
                        close_amt = amount * (PARTIAL_TP1_PERCENT/100)
                        order=close_trade_market(pair, side, close_amt)
                        new_amount = max(0, amount-close_amt)
                        new_sl = entry
                        with db_conn() as con:
                            con.execute("UPDATE open_trades SET amount=?, sl=?, tp1_taken=?, note=? WHERE id=?", (new_amount, new_sl, 1, "TP1_PARTIAL_BE", tid)); con.commit()
                        tg_send(chat_id, f"""🥇 <b>TP1 touché</b>
━━━━━━━━━━━━━━━━━━━━
🪙 {pair}
✅ {PARTIAL_TP1_PERCENT:.0f}% sécurisé
🔒 SL déplacé breakeven : <b>{fmt_price(new_sl)}</b>
🧾 ID : <code>{order.get('id','N/A')}</code>""", main_menu_keyboard())
                        continue
                    elif ENABLE_TRAILING_STOP and tp1_taken:
                        new_sl=max(sl, px - abs(tp1-entry)*0.55)
                        if new_sl > sl:
                            with db_conn() as con:
                                con.execute("UPDATE open_trades SET sl=?, note=? WHERE id=?", (new_sl, "TRAIL", tid)); con.commit()
                else:
                    if px >= sl:
                        hit="SL"; pnl=(entry-px)/entry*100
                    elif px <= tp2:
                        hit="TP2"; pnl=(entry-px)/entry*100
                    elif not tp1_taken and px <= tp1:
                        close_amt = amount * (PARTIAL_TP1_PERCENT/100)
                        order=close_trade_market(pair, side, close_amt)
                        new_amount = max(0, amount-close_amt)
                        new_sl = entry
                        with db_conn() as con:
                            con.execute("UPDATE open_trades SET amount=?, sl=?, tp1_taken=?, note=? WHERE id=?", (new_amount, new_sl, 1, "TP1_PARTIAL_BE", tid)); con.commit()
                        tg_send(chat_id, f"""🥇 <b>TP1 touché</b>
━━━━━━━━━━━━━━━━━━━━
🪙 {pair}
✅ {PARTIAL_TP1_PERCENT:.0f}% sécurisé
🔒 SL déplacé breakeven : <b>{fmt_price(new_sl)}</b>
🧾 ID : <code>{order.get('id','N/A')}</code>""", main_menu_keyboard())
                        continue
                    elif ENABLE_TRAILING_STOP and tp1_taken:
                        new_sl=min(sl, px + abs(entry-tp1)*0.55)
                        if new_sl < sl:
                            with db_conn() as con:
                                con.execute("UPDATE open_trades SET sl=?, note=? WHERE id=?", (new_sl, "TRAIL", tid)); con.commit()

                if not hit: continue
                order=close_trade_market(pair, side, amount)
                with db_conn() as con:
                    con.execute("UPDATE open_trades SET status=?, exit_price=?, pnl_percent=?, closed_ts=? WHERE id=?", (hit, px, pnl, int(time.time()), tid)); con.commit()
                icon="✅" if hit.startswith("TP") else "❌"
                tg_send(chat_id, f"""{icon} <b>Trade fermé automatiquement</b>
━━━━━━━━━━━━━━━━━━━━
🪙 {pair}
📍 Sortie : <b>{hit}</b>
💰 Prix : <b>{fmt_price(px)}</b>
📈 PnL : <b>{pnl:+.2f}%</b>
🧾 Close ID : <code>{order.get('id','N/A')}</code>""", main_menu_keyboard())
        except Exception as e:
            print("monitor_open_trades error:", e)

# ================= ROUTER =================
def clean_coin_from_text(text):
    raw=text.replace("📈","").replace("/USDT","").strip().upper()
    for coins in WALLETS.values():
        for c in coins:
            if raw.endswith(c) or raw==c: return c
    for p in raw.split():
        if any(p==c for coins in WALLETS.values() for c in coins): return p
    return None

def wallet_from_text(text):
    if "Kraken" in text: return "Kraken"
    if "Exodus" in text: return "Exodus"
    if "Trust" in text: return "Trust Wallet"
    return None

def handle_callback_query(cb):
    callback_id = cb.get("id")
    data = cb.get("data") or ""
    msg = cb.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return
    if data.startswith("risk:"):
        parts=data.split(":")
        try:
            pct=float(parts[1])
        except Exception:
            pct=1.0
        coin=parts[2] if len(parts)>2 else ""
        if coin:
            a=STATE.get("analysis_by_coin",{}).get(chat_id,{}).get(coin)
            if a and a.get("signal") in ["BUY","SELL"]:
                STATE["pending_trade"][chat_id]=a
        STATE["risk_choice"][chat_id]=pct
        tg_answer_callback(callback_id, f"Risque {pct:.0f}% sélectionné")
        tg_edit_markup(chat_id, msg.get("message_id"), confirm_trade_inline_keyboard(coin))
        return
    if data.startswith("trade"):
        parts=data.split(":")
        coin=parts[1] if len(parts)>1 else ""
        if coin:
            a=STATE.get("analysis_by_coin",{}).get(chat_id,{}).get(coin)
            if a and a.get("signal") in ["BUY","SELL"]:
                STATE["pending_trade"][chat_id]=a
        pct=STATE["risk_choice"].get(chat_id, 1.0)
        tg_answer_callback(callback_id, "Trade demandé")
        tg_send(chat_id, execute_kraken_trade(chat_id, pct), main_menu_keyboard())
        return
    if data == "cancel":
        STATE.get("pending_trade",{}).pop(chat_id,None)
        tg_answer_callback(callback_id, "Annulé")
        tg_send(chat_id,"❌ Trade annulé.",main_menu_keyboard())
        return

def handle_message(msg):
    chat_id=msg.get("chat",{}).get("id"); text=(msg.get("text") or "").strip()
    if not chat_id or not text: return
    if text.startswith("/start") or text in ["🏠 Menu","Menu","🏡 Menu"]: send_home(chat_id); return
    if text.startswith("/analyze"):
        parts=text.split()
        if len(parts)>=2:
            coin=parts[1].replace("/USDT","").upper(); wallet=next((w for w,cs in WALLETS.items() if coin in cs),"")
            a=analyze_coin(coin,wallet,"manual",chat_id)
            save_analysis(chat_id,a)
            if a.get("signal") in ["BUY","SELL"]:
                STATE["pending_trade"][chat_id]=a
            tg_send(chat_id,signal_message(a), trade_inline_keyboard(a.get("coin", "")))
        else: send_wallets(chat_id,"analysis")
        return
    if text=="🤖 Kraken Pro": tg_send(chat_id, kraken_status_message(), main_menu_keyboard()); return
    if text=="🔐 Test Kraken": tg_send(chat_id, test_kraken_connection(), settings_keyboard()); return
    if text=="🧹 Reset Paper Trades": tg_send(chat_id, reset_paper_trades(chat_id), settings_keyboard()); return
    if text in ["1%", "2%", "3%", "1% Risque", "2% Risque", "3% Risque"]:
        pct=float(text.split("%")[0]); STATE["risk_choice"][chat_id]=pct
        tg_send(chat_id, f"✅ Risque sélectionné : <b>{pct:.0f}%</b>. Utilise les boutons inline sous l’analyse.", main_menu_keyboard()); return
    if text=="❌ Annuler": STATE.get("pending_trade",{}).pop(chat_id,None); tg_send(chat_id,"❌ Trade annulé.",main_menu_keyboard()); return
    if text in ["🚀 Trade", "✅ Trade"]: tg_send(chat_id, execute_kraken_trade(chat_id, STATE["risk_choice"].get(chat_id,1.0)), main_menu_keyboard()); return
    if text=="📊 Analyse Premium": send_wallets(chat_id,"analysis"); return
    if text=="💼 Watchlist": send_wallets(chat_id,"watchlist"); return
    if text=="💼 Wallets": send_wallets(chat_id,"analysis"); return
    wallet=wallet_from_text(text)
    if wallet: send_wallet_coins(chat_id,wallet,"analysis"); return
    coin=clean_coin_from_text(text)
    if coin:
        wallet=next((w for w,cs in WALLETS.items() if coin in cs),""); a=analyze_coin(coin,wallet,"manual",chat_id)
        save_analysis(chat_id,a)
        if a.get("signal") in ["BUY","SELL"]:
            STATE["pending_trade"][chat_id]=a
        tg_send(chat_id,signal_message(a), trade_inline_keyboard(a.get("coin", "")))
        return
    if text=="⚙️ Réglages Pro": send_settings(chat_id); return
    if text in ["🛡️ Prudent","⚖️ Normal","🚀 Agressif"]:
        STATE["mode"]="Prudent" if "Prudent" in text else "Agressif" if "Agressif" in text else "Normal"; send_settings(chat_id); return
    if text=="📈 Dashboard": dashboard(chat_id); return
    if text=="🎯 Sniper": threading.Thread(target=run_sniper, args=(chat_id,), daemon=True).start(); return
    if text=="🧪 Backtest": threading.Thread(target=run_backtest, args=(chat_id,), daemon=True).start(); return
    if text=="🔔 Auto Scan": run_auto_scan(chat_id); return
    tg_send(chat_id,"Je n’ai pas compris 👇",main_menu_keyboard())


# ================= V23 INSTITUTIONAL 98 PACK OVERRIDES =================
# Objectif : moins de trades, mais setups beaucoup plus propres.
# Important : aucune stratégie ne garantit un résultat. Le pack augmente surtout la qualité du filtrage + risk management.

V25_VERSION = "V25 HEDGE AI PRO PACK"
_old_analyze_coin = analyze_coin
_old_signal_message = signal_message
_old_main_menu_keyboard = main_menu_keyboard


def main_menu_keyboard():
    return reply_keyboard([
        ["📊 Analyse Premium"],
        ["⚙️ Réglages Pro", "📈 Dashboard"],
        ["🎯 Sniper"],
        ["🧪 Backtest", "🔔 Auto Scan"],
        ["💼 Watchlist"],
    ])


def kraken_public_price(coin):
    """Prix public Kraken sans clé API. Sert à confirmer Binance et détecter gros écart."""
    try:
        if ccxt is not None:
            ex = ccxt.kraken({"enableRateLimit": True})
            pair = "BTC/USDT" if coin == "BTC" else f"{coin}/USDT"
            ticker = ex.fetch_ticker(pair)
            last = ticker.get("last") or ticker.get("close")
            if last:
                return float(last)
    except Exception:
        pass
    try:
        pair = "XBTUSDT" if coin == "BTC" else f"{coin}USDT"
        data = http_get("https://api.kraken.com/0/public/Ticker", {"pair": pair})
        res = data.get("result", {})
        if res:
            first = list(res.values())[0]
            return float(first["c"][0])
    except Exception:
        pass
    return None


def price_consensus(coin, binance_price):
    kp = cached(f"kraken_public:{coin}", 45, lambda: kraken_public_price(coin))
    if not kp or not binance_price:
        return {"ok": True, "spread_pct": 0.0, "kraken_price": kp, "note": "Kraken public N/A"}
    spread = abs(float(binance_price) - float(kp)) / max(float(binance_price), float(kp)) * 100
    ok = spread <= MAX_EXCHANGE_SPREAD_PERCENT
    note = "Consensus OK" if ok else f"Spread élevé {spread:.2f}%"
    return {"ok": ok, "spread_pct": spread, "kraken_price": kp, "note": note}


def institutional_gate(a):
    if not a.get("ok") or a.get("signal") not in ["BUY", "SELL"]:
        return False, "pas de signal"
    smc = a.get("smc", {})
    tags = " ".join(smc.get("tags", [])).lower()
    smc_elite = ("bos" in tags and ("liquidity" in tags or "sweep" in tags) and "fvg" in tags) or smc.get("score", 0) >= 45
    score_ok = a.get("score", 0) >= INSTITUTIONAL_MIN_SCORE
    rr_ok = a.get("rr", 0) >= INSTITUTIONAL_MIN_RR
    vol_ok = a.get("vol_ratio", 0) >= INSTITUTIONAL_MIN_VOLUME_RATIO
    mtf_ok = a.get("mtf", {}).get("confirm", False)
    btc_ok = a.get("vol_guard", {}).get("ok", True)
    consensus = a.get("price_consensus", {"ok": True})
    consensus_ok = consensus.get("ok", True) if PRICE_CONSENSUS_FILTER else True
    reasons = []
    if not score_ok: reasons.append(f"score < {INSTITUTIONAL_MIN_SCORE}")
    if not rr_ok: reasons.append(f"R/R < {INSTITUTIONAL_MIN_RR}")
    if not vol_ok: reasons.append(f"volume < {INSTITUTIONAL_MIN_VOLUME_RATIO}x")
    if not mtf_ok: reasons.append("MTF faible")
    if not smc_elite: reasons.append("SMC pas elite")
    if not btc_ok: reasons.append("volatilité BTC")
    if not consensus_ok: reasons.append("prix exchange non aligné")
    ok = score_ok and rr_ok and vol_ok and mtf_ok and smc_elite and btc_ok and consensus_ok
    return ok, "OK" if ok else ", ".join(reasons[:3])


def analyze_coin(coin, wallet="", source="manual", chat_id=None):
    a = _old_analyze_coin(coin, wallet, source, chat_id)
    if not a.get("ok"):
        return a
    consensus = price_consensus(coin, a.get("price"))
    a["price_consensus"] = consensus
    # pénalités institutionnelles avant décision finale
    if INSTITUTIONAL_MODE and a.get("signal") in ["BUY", "SELL"]:
        if not consensus.get("ok", True):
            a["score"] = max(0, int(a.get("score", 0)) - 8)
            a.setdefault("reasons", []).append("V23 : spread exchange élevé")
        if a.get("vol_ratio", 0) >= 1.8 and a.get("rr", 0) >= 2.0:
            a["score"] = min(100, int(a.get("score", 0)) + 3)
            a.setdefault("reasons", []).append("V23 : momentum premium")
        ok, why = institutional_gate(a)
        a["institutional_ok"] = ok
        a["institutional_reason"] = why
        # Pour les modes auto/sniper, on refuse strictement. Pour analyse premium, on affiche quand même avec ATTENDRE.
        if not ok and source in ["sniper", "auto_alert", "autoscan"]:
            a["signal"] = "WAIT"
            a["direction"] = "Neutre"
            a["profitable_ok"] = False
        elif not ok:
            a["profitable_ok"] = False
    else:
        a["institutional_ok"] = a.get("signal") in ["BUY", "SELL"]
        a["institutional_reason"] = "OK" if a.get("institutional_ok") else "attente"
    return a


def is_clean_trade(a, min_score=70):
    if INSTITUTIONAL_MODE:
        ok, _ = institutional_gate(a)
        return bool(ok and a.get("score", 0) >= min_score)
    # fallback logique V22
    if not a.get("ok") or a.get("signal") not in ["BUY", "SELL"]:
        return False
    return bool(a.get("score", 0) >= min_score and a.get("rr", 0) >= MIN_RR and a.get("vol_ratio", 0) >= MIN_VOLUME_RATIO)


def signal_message(a):
    if not a.get("ok"):
        return f"⚠️ <b>Analyse impossible</b>\n\n🪙 {a.get('coin','')}\n❌ {a.get('error','Erreur inconnue')}"
    sig_emoji = "🟢" if a["signal"] == "BUY" else "🔴" if a["signal"] == "SELL" else "⚪"
    tradable = a.get("signal") in ["BUY", "SELL"] and a.get("institutional_ok", a.get("profitable_ok"))
    verdict = "✅ SETUP ÉLITE" if tradable else "⚪ ATTENDRE"
    smc = a.get("smc", {})
    mtf = a.get("mtf", {})
    consensus = a.get("price_consensus", {})
    setup = []
    if mtf.get("confirm"): setup.append("MTF 1H+4H")
    setup += smc.get("tags", [])[:3]
    if a.get("vol_ratio", 0) >= INSTITUTIONAL_MIN_VOLUME_RATIO: setup.append("Volume premium")
    if consensus.get("spread_pct", 0) > 0: setup.append(f"Spread {consensus.get('spread_pct',0):.2f}%")
    setup_txt = " • ".join(setup[:5]) or "Setup pas assez propre"
    remember_pending_trade(a.get("chat_id"), a)
    return f"""💎 <b>LVBXNT ELITE SIGNAL</b>
━━━━━━━━━━━━━━━━━━━━
🪙 <b>{a['pair']}</b> | {sig_emoji} <b>{a['signal']}</b>
🏁 Verdict : <b>{verdict}</b>

💰 Prix : <b>{fmt_price(a['price'])}</b>
🎯 Entrée limit : <b>{fmt_price(a.get('entry', a['price']))}</b>
🛑 SL : <b>{fmt_price(a['sl'])}</b>
🥇 TP1 : <b>{fmt_price(a['tp1'])}</b>
🥈 TP2 : <b>{fmt_price(a['tp2'])}</b>

🧠 Score : <b>{a['score']}%</b>
⚠️ Risque setup : <b>{a['risk']}</b>
📐 R/R : <b>{a.get('rr',0):.2f}</b>
📊 RSI : <b>{a['rsi']:.1f}</b> | Vol : <b>{a['vol_ratio']:.2f}x</b>
🏦 SMC/ICT : <b>{smc.get('bias','N/A')}</b> • {smc.get('pd','N/A')}
🌍 Régime : <b>{a.get('regime',{}).get('name','N/A')}</b>
🔁 Consensus : <b>{consensus.get('note','OK')}</b>
🧠 IA : <b>{a.get('ai_profile',{}).get('note','apprentissage')}</b>

✅ <b>Confluence</b> : {setup_txt}
🛡️ Filtre V23 : <b>{a.get('institutional_reason','OK')}</b>"""


def elite_report(chat_id):
    with db_conn() as con:
        open_count = count_open_trades(chat_id)
        closed = con.execute("SELECT COUNT(*), AVG(pnl_percent), SUM(CASE WHEN pnl_percent>0 THEN 1 ELSE 0 END) FROM open_trades WHERE chat_id=? AND status='CLOSED'", (chat_id,)).fetchone()
        recent = con.execute("SELECT coin,pair,side,pnl_percent,note FROM open_trades WHERE chat_id=? AND status='CLOSED' ORDER BY closed_ts DESC LIMIT 8", (chat_id,)).fetchall()
    total = closed[0] or 0
    avg = closed[1] or 0
    wins = closed[2] or 0
    wr = (wins/total*100) if total else 0
    msg = f"""🧠 <b>Elite Report V23</b>
━━━━━━━━━━━━━━━━━━━━
📌 Trades ouverts : <b>{open_count}/{MAX_OPEN_TRADES}</b>
🏆 Winrate fermé : <b>{wr:.0f}%</b>
💰 PnL moyen : <b>{avg:+.2f}%</b>
🛡️ Mode : <b>{'Institutional ON' if INSTITUTIONAL_MODE else 'Standard'}</b>
📐 Min R/R : <b>{INSTITUTIONAL_MIN_RR}</b>
🧠 Min score : <b>{INSTITUTIONAL_MIN_SCORE}%</b>
📊 Min volume : <b>{INSTITUTIONAL_MIN_VOLUME_RATIO}x</b>
🔁 Max spread : <b>{MAX_EXCHANGE_SPREAD_PERCENT}%</b>

🔥 <b>Derniers résultats</b>"""
    if not recent:
        msg += "\n• Aucun trade fermé encore"
    else:
        for coin,pair,side,pnl,note in recent:
            msg += f"\n• {pair} {side} : <b>{pnl:+.2f}%</b>"
    tg_send(chat_id, msg[:3900], main_menu_keyboard())


def arbitrage_radar():
    """Radar simple : compare Binance/Kraken. Alert only, pas d'exécution auto."""
    opps=[]
    for coin in WALLETS.get("Kraken", [])[:10]:
        try:
            sym=resolve_binance_symbol(coin)
            if not sym: continue
            bp=float(http_get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", {"symbol": sym}).get("price"))
            kp=kraken_public_price(coin)
            if not kp: continue
            spread=abs(bp-kp)/max(bp,kp)*100
            if spread>=ARBITRAGE_ALERT_PERCENT:
                cheap="Binance" if bp<kp else "Kraken"
                expensive="Kraken" if bp<kp else "Binance"
                opps.append((coin, spread, cheap, expensive, bp, kp))
        except Exception:
            continue
    return sorted(opps, key=lambda x:x[1], reverse=True)[:5]


def run_sniper(chat_id):
    """V23 turbo : top 3 setups institutionnels, aucun trade automatique."""
    tg_send(chat_id, "🎯 <b>Sniper V23</b>\n\nScan turbo des opportunités élite... ⏳")
    results=[]
    items=[(wallet, coin) for wallet, coins in WALLETS.items() for coin in coins]

    def _scan_one(item):
        wallet, coin = item
        try:
            a = analyze_coin(coin, wallet, "sniper", chat_id)
            bt = a.get("backtest", {}) if a.get("ok") else {}
            if is_clean_trade(a, MIN_SNIPER_SCORE) and (bt.get("winrate") is None or bt.get("winrate", 0) >= 55):
                return a
        except Exception as e:
            print("V23 sniper error", item, e)
        return None

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
        started=time.time()
        with ThreadPoolExecutor(max_workers=SNIPER_WORKERS) as ex:
            futs=[ex.submit(_scan_one, item) for item in items]
            try:
                for fut in as_completed(futs, timeout=SNIPER_MAX_SECONDS):
                    a=fut.result()
                    if a: results.append(a)
                    if time.time()-started > SNIPER_MAX_SECONDS: break
            except TimeoutError:
                pass
    except Exception as e:
        print("V23 sniper fallback", e)
        for item in items:
            a=_scan_one(item)
            if a: results.append(a)

    picks=sorted(results,key=lambda x:(x.get("score",0),x.get("rr",0),x.get("vol_ratio",0)),reverse=True)[:3]
    if not picks:
        tg_send(chat_id,"🎯 <b>Sniper V23</b>\n\n❌ <b>NO TRADE</b>\n\nAucun setup élite maintenant.",main_menu_keyboard())
        return
    tg_send(chat_id,f"🎯 <b>Sniper V23</b>\n\n✅ <b>{len(picks)}</b> setup(s) élite trouvé(s).",main_menu_keyboard())
    for i,a in enumerate(picks,1):
        save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
        STATE.setdefault("analysis_by_coin",{}).setdefault(chat_id,{})[a.get("coin")]=a
        if i==1: STATE["pending_trade"][chat_id]=a
        tg_send(chat_id, f"🏆 <b>SNIPER ELITE #{i}</b>\n" + signal_message(a), trade_inline_keyboard(a.get("coin", "")))


def run_auto_scan(chat_id):
    STATE["auto_scan"] = not STATE["auto_scan"]
    STATE["last_scan_chat_id"] = chat_id if STATE["auto_scan"] else None
    status = "ON" if STATE["auto_scan"] else "OFF"
    full = "FULL AUTO KRAKEN 1% activé" if STATE["auto_scan"] else "FULL AUTO désactivé"
    tg_send(chat_id, f"🔔 <b>Auto Scan : {status}</b>\n🤖 <b>{full}</b>", main_menu_keyboard())


def auto_scan_loop():
    """V23 Auto Scan : prend uniquement le meilleur setup institutionnel disponible."""
    while True:
        time.sleep(SCAN_INTERVAL_SECONDS)
        chat_id=STATE.get("last_scan_chat_id")
        if not (STATE.get("auto_scan") and chat_id):
            continue
        try:
            if count_open_trades(chat_id) >= MAX_OPEN_TRADES:
                continue
            guard = btc_volatility_guard()
            if not guard.get("ok", True):
                continue
            items=[(wallet, coin) for wallet, coins in WALLETS.items() for coin in coins]
            results=[]
            def _scan(item):
                wallet, coin = item
                try:
                    a=analyze_coin(coin,wallet,"auto_alert",chat_id)
                    if is_clean_trade(a, MIN_AUTOTRADE_SCORE) and not was_recently_alerted(chat_id,a["symbol"],a["signal"],AUTO_SCAN_COOLDOWN_HOURS):
                        ok_safe, _ = account_safety_ok(chat_id, a)
                        if ok_safe: return a
                except Exception as e:
                    print("V23 autoscan pair error", item, e)
                return None
            from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
            with ThreadPoolExecutor(max_workers=SNIPER_WORKERS) as ex:
                futs=[ex.submit(_scan, item) for item in items]
                try:
                    for fut in as_completed(futs, timeout=max(SNIPER_MAX_SECONDS, 20)):
                        a=fut.result()
                        if a: results.append(a)
                except TimeoutError:
                    pass
            slots=max(0, MAX_OPEN_TRADES-count_open_trades(chat_id))
            if not results or slots<=0:
                continue
            picks=sorted(results,key=lambda x:(x.get("score",0),x.get("rr",0),x.get("vol_ratio",0)),reverse=True)
            if AUTO_SCAN_ONLY_BEST:
                picks=picks[:1]
            else:
                picks=picks[:slots]
            for a in picks[:slots]:
                save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
                STATE["pending_trade"][chat_id]=a
                tg_send(chat_id,"🔔 <b>Auto Scan V23</b>\n🤖 Setup élite détecté → trade auto 1%", main_menu_keyboard())
                tg_send(chat_id,signal_message(a), main_menu_keyboard())
                tg_send(chat_id, execute_kraken_trade(chat_id, AUTO_TRADE_RISK_PERCENT), main_menu_keyboard())
        except Exception as e:
            print("V23 autoscan error:", e)


def send_home(chat_id):
    tg_send(chat_id, f"""🚀 <b>LVBXNT Crypto Bot</b>

✨ Version : <b>{V25_VERSION}</b>
⚙️ Mode : <b>{STATE['mode']}</b>
🔔 Auto Scan : <b>{'ON' if STATE['auto_scan'] else 'OFF'}</b>
🛡️ Institutional : <b>{'ON' if INSTITUTIONAL_MODE else 'OFF'}</b>

👇 Choisis une action""", main_menu_keyboard())


_old_handle_message = handle_message

def handle_message(msg):
    chat_id=msg.get("chat",{}).get("id"); text=(msg.get("text") or "").strip()
    if text == "🧠 Elite Report":
        elite_report(chat_id); return
    return _old_handle_message(msg)


# ================= V25 HEDGE AI PRO PACK OVERRIDES =================
# Sans copy trading. Local-first + prêt Contabo 24/7.
V25_MODE = os.getenv("V25_MODE", "1") == "1"
HEDGE_SHIELD = os.getenv("HEDGE_SHIELD", "1") == "1"
HEDGE_MAX_BTC_MOVE_PERCENT = float(os.getenv("HEDGE_MAX_BTC_MOVE_PERCENT", "2.6"))
V25_MIN_SCORE = int(os.getenv("V25_MIN_SCORE", "90"))
V25_MIN_RR = float(os.getenv("V25_MIN_RR", "1.85"))
V25_MIN_VOLUME_RATIO = float(os.getenv("V25_MIN_VOLUME_RATIO", "1.30"))
V25_MIN_AI_WINRATE = float(os.getenv("V25_MIN_AI_WINRATE", "54"))
V25_SMART_LIMIT_OFFSET_ATR = float(os.getenv("V25_SMART_LIMIT_OFFSET_ATR", "0.06"))
V25_REDUCE_RISK_AFTER_LOSS = os.getenv("V25_REDUCE_RISK_AFTER_LOSS", "1") == "1"
V25_DRAWDOWN_PAUSE_PERCENT = float(os.getenv("V25_DRAWDOWN_PAUSE_PERCENT", "4"))
V25_MAX_CORRELATED_TRADES = int(os.getenv("V25_MAX_CORRELATED_TRADES", "1"))
V25_TRADE_SESSION_FILTER = os.getenv("V25_TRADE_SESSION_FILTER", "1") == "1"
V25_MIN_HISTORY_TRADES_FOR_AI = int(os.getenv("V25_MIN_HISTORY_TRADES_FOR_AI", "12"))
V25_EXECUTION_RETRY = int(os.getenv("V25_EXECUTION_RETRY", "2"))
V25_VERSION = "V25 HEDGE AI PRO PACK"


def _closed_trade_rows(chat_id, limit=250):
    try:
        with db_conn() as con:
            return con.execute("""
                SELECT coin, side, pnl_percent, risk_percent, strategy_snapshot, closed_ts, note
                FROM open_trades
                WHERE chat_id=? AND status='CLOSED'
                ORDER BY closed_ts DESC LIMIT ?
            """, (chat_id, limit)).fetchall()
    except Exception:
        return []


def v25_ai_advanced_profile(chat_id, coin=None):
    """AI local avancée : calcule bonus/malus à partir du journal réel."""
    rows = _closed_trade_rows(chat_id, 250)
    if not rows:
        return {"ready": False, "trades": 0, "winrate": 0, "score_adjust": 0, "risk_mult": 1.0, "note": "IA en apprentissage"}
    if coin:
        crows = [r for r in rows if str(r[0]).upper() == str(coin).upper()]
        use = crows if len(crows) >= max(4, V25_MIN_HISTORY_TRADES_FOR_AI//2) else rows
    else:
        use = rows
    wins = [r for r in use if float(r[2] or 0) > 0]
    losses = [r for r in use if float(r[2] or 0) < 0]
    total = len(use)
    winrate = (len(wins) / total * 100) if total else 0
    avg_pnl = sum(float(r[2] or 0) for r in use) / total if total else 0
    last5 = use[:5]
    last5_pnl = sum(float(r[2] or 0) for r in last5)
    loss_streak = 0
    for r in use:
        if float(r[2] or 0) < 0: loss_streak += 1
        else: break
    score_adjust = 0
    risk_mult = 1.0
    if total >= V25_MIN_HISTORY_TRADES_FOR_AI:
        if winrate >= 62 and avg_pnl > 0:
            score_adjust += 5; risk_mult = 1.15
        elif winrate >= V25_MIN_AI_WINRATE and avg_pnl >= 0:
            score_adjust += 2; risk_mult = 1.0
        else:
            score_adjust -= 6; risk_mult = 0.65
        if last5_pnl < -2 or loss_streak >= 2:
            score_adjust -= 6; risk_mult = 0.5
    note = f"WR {winrate:.1f}% • Avg {avg_pnl:.2f}% • StreakLoss {loss_streak}"
    return {"ready": total >= V25_MIN_HISTORY_TRADES_FOR_AI, "trades": total, "winrate": winrate, "avg_pnl": avg_pnl,
            "last5_pnl": last5_pnl, "loss_streak": loss_streak, "score_adjust": score_adjust,
            "risk_mult": risk_mult, "note": note}


def v25_hedge_shield(a):
    """Pas de hedging automatique spot. Shield = bloque les trades quand risque corrélé BTC trop haut."""
    if not HEDGE_SHIELD:
        return True, "OFF"
    guard = btc_volatility_guard()
    if not guard.get("ok", True):
        return False, "BTC volatilité forte"
    try:
        rows = klines("BTCUSDT", "1h", 8)
        if len(rows) >= 2:
            move = abs((rows[-1][4] - rows[-2][4]) / rows[-2][4] * 100)
            if move >= HEDGE_MAX_BTC_MOVE_PERCENT:
                return False, f"BTC move {move:.2f}%"
    except Exception:
        pass
    return True, "OK"


def v25_session_ok():
    """Filtre simple : évite les minutes de faible liquidité/rollover."""
    if not V25_TRADE_SESSION_FILTER:
        return True, "OFF"
    try:
        h = datetime.datetime.utcnow().hour
        # crypto 24/7, mais on évite l'heure très calme autour de 00 UTC
        if h in [0]:
            return False, "session calme UTC"
    except Exception:
        pass
    return True, "OK"


def v25_correlation_open_trades_ok(chat_id, coin):
    """Limite l'exposition corrélée : altcoins = max trades corrélés."""
    try:
        if str(coin).upper() in ["BTC", "ETH"]:
            return True, "OK"
        with db_conn() as con:
            rows = con.execute("SELECT coin FROM open_trades WHERE chat_id=? AND status='OPEN'", (chat_id,)).fetchall()
        alt_open = [r[0] for r in rows if str(r[0]).upper() not in ["BTC", "ETH"]]
        if len(alt_open) >= V25_MAX_CORRELATED_TRADES:
            return False, "exposition altcoin max"
    except Exception:
        pass
    return True, "OK"


def v25_smart_entry(a):
    """Une seule entrée précise : léger offset ATR pour limit intelligent."""
    entry = float(a.get("entry", a.get("price", 0)))
    atr = float(a.get("atr", 0) or 0)
    if atr > 0 and a.get("signal") == "BUY":
        entry = entry - (atr * V25_SMART_LIMIT_OFFSET_ATR)
    elif atr > 0 and a.get("signal") == "SELL":
        entry = entry + (atr * V25_SMART_LIMIT_OFFSET_ATR)
    a["entry"] = entry
    a["entry_low"] = entry
    a["entry_high"] = entry
    a["entry_reason"] = "Entrée unique V25 : FVG/SMC + smart limit"
    return a


_old_analyze_coin_v25 = analyze_coin

def analyze_coin(coin, wallet="", source="manual", chat_id=None):
    a = _old_analyze_coin_v25(coin, wallet, source, chat_id)
    if not isinstance(a, dict) or not a.get("ok"):
        return a
    if not V25_MODE:
        return a
    a = v25_smart_entry(a)
    ai = v25_ai_advanced_profile(chat_id or a.get("chat_id") or 0, coin)
    a["v25_ai"] = ai
    a["score"] = max(0, min(100, int(a.get("score", 0) + ai.get("score_adjust", 0))))
    hedge_ok, hedge_note = v25_hedge_shield(a)
    sess_ok, sess_note = v25_session_ok()
    corr_ok, corr_note = v25_correlation_open_trades_ok(chat_id or 0, coin)
    a["v25_hedge_ok"] = hedge_ok
    a["v25_hedge_note"] = hedge_note
    a["v25_session_ok"] = sess_ok
    a["v25_session_note"] = sess_note
    a["v25_corr_ok"] = corr_ok
    a["v25_corr_note"] = corr_note
    # compat avec filtre institutionnel existant
    a["institutional_ok"] = a.get("institutional_ok", True) and hedge_ok and sess_ok and corr_ok
    if not hedge_ok: a["institutional_reason"] = "Hedge Shield: " + hedge_note
    elif not sess_ok: a["institutional_reason"] = "Session: " + sess_note
    elif not corr_ok: a["institutional_reason"] = "Corrélation: " + corr_note
    else: a["institutional_reason"] = a.get("institutional_reason", "V25 OK")
    return a


def v25_gate(a):
    if not V25_MODE:
        return is_clean_trade(a, MIN_AUTOTRADE_SCORE), "standard"
    if a.get("signal") not in ["BUY", "SELL"]:
        return False, "no signal"
    checks = []
    if a.get("score", 0) < V25_MIN_SCORE: checks.append(f"score<{V25_MIN_SCORE}")
    if a.get("rr", 0) < V25_MIN_RR: checks.append(f"RR<{V25_MIN_RR}")
    if a.get("vol_ratio", 0) < V25_MIN_VOLUME_RATIO: checks.append(f"volume<{V25_MIN_VOLUME_RATIO}x")
    if not a.get("mtf", {}).get("confirm"): checks.append("MTF")
    if not a.get("smc", {}).get("bos") or not a.get("smc", {}).get("liquidity_grab") or not a.get("smc", {}).get("fvg"):
        checks.append("SMC incomplet")
    if not a.get("v25_hedge_ok", True): checks.append("hedge shield")
    if not a.get("v25_session_ok", True): checks.append("session")
    if not a.get("v25_corr_ok", True): checks.append("corrélation")
    ok = len(checks) == 0
    return ok, "OK" if ok else ", ".join(checks)


_old_is_clean_trade_v25 = is_clean_trade

def is_clean_trade(a, min_score=MIN_TRADE_SCORE):
    if V25_MODE:
        ok, _ = v25_gate(a)
        return ok
    return _old_is_clean_trade_v25(a, min_score)


def signal_message(a):
    if not a.get("ok"):
        return f"❌ Analyse impossible : {a.get('error','erreur')}"
    ok, gate_note = v25_gate(a)
    action = "✅ SETUP V25" if ok else "⚪ ATTENTE"
    ai = a.get("v25_ai", {})
    rr = a.get("rr", 0)
    return f"""📊 <b>{a['pair']}</b>
━━━━━━━━━━━━━━━━━━━━
🚦 Signal : <b>{a['signal']}</b>
🎯 Score : <b>{a['score']}%</b>
🏦 Qualité : <b>{action}</b>

💰 Entrée : <b>{fmt_price(a['entry'])}</b>
🛑 SL : <b>{fmt_price(a['sl'])}</b>
🥇 TP1 : <b>{fmt_price(a['tp1'])}</b>
🥈 TP2 : <b>{fmt_price(a['tp2'])}</b>
📐 R/R : <b>{rr:.2f}</b>

🧠 SMC : <b>{smc_summary(a)}</b>
📊 Volume : <b>{a.get('vol_ratio',0):.2f}x</b>
🌍 Régime : <b>{a.get('regime',{}).get('name','N/A')}</b>
🛡️ Shield : <b>{gate_note}</b>
🤖 IA : <b>{ai.get('note','N/A')}</b>"""


_old_calculate_position_v25 = calculate_position

def calculate_position(a, risk_percent):
    if V25_MODE:
        ai = a.get("v25_ai") or v25_ai_advanced_profile(a.get("chat_id",0), a.get("coin"))
        if V25_REDUCE_RISK_AFTER_LOSS and ai.get("loss_streak", 0) >= 1:
            risk_percent = min(float(risk_percent), 0.5)
    return _old_calculate_position_v25(a, risk_percent)


_old_execute_kraken_trade_v25 = execute_kraken_trade

def execute_kraken_trade(chat_id, risk_percent):
    a = STATE.get("pending_trade", {}).get(chat_id)
    if V25_MODE and a:
        ok, why = v25_gate(a)
        if not ok:
            return f"🛡️ <b>Trade bloqué V25</b>\nRaison : {why}"
        ok_safe, why_safe = account_safety_ok(chat_id, a)
        if not ok_safe:
            return f"🛡️ <b>Risk Engine bloque le trade</b>\nRaison : {why_safe}"
    return _old_execute_kraken_trade_v25(chat_id, risk_percent)


def v25_report(chat_id):
    rows = _closed_trade_rows(chat_id, 500)
    total = len(rows)
    wins = len([r for r in rows if float(r[2] or 0) > 0])
    pnl = sum(float(r[2] or 0) for r in rows)
    wr = wins/total*100 if total else 0
    ai = v25_ai_advanced_profile(chat_id)
    txt = f"""🧬 <b>V25 PRO+ REPORT</b>
━━━━━━━━━━━━━━━━━━━━
📊 Trades fermés : <b>{total}</b>
✅ Winrate : <b>{wr:.1f}%</b>
💰 PnL total : <b>{pnl:.2f}%</b>
🤖 IA : <b>{ai.get('note','N/A')}</b>

🛡️ Protections :
• Hedge Shield : <b>{'ON' if HEDGE_SHIELD else 'OFF'}</b>
• Min score : <b>{V25_MIN_SCORE}%</b>
• Min R/R : <b>{V25_MIN_RR}</b>
• Min volume : <b>{V25_MIN_VOLUME_RATIO}x</b>
• Copy trading : <b>OFF</b>
• Contabo ready : <b>YES</b>"""
    tg_send(chat_id, txt, main_menu_keyboard())


_old_main_menu_keyboard_v25 = main_menu_keyboard

def main_menu_keyboard():
    return reply_keyboard([
        ["📊 Analyse Premium"],
        ["⚙️ Réglages Pro", "📈 Dashboard"],
        ["🎯 Sniper"],
        ["🧪 Backtest", "🔔 Auto Scan"],
        ["💼 Watchlist"],
    ])


_old_handle_message_v25 = handle_message

def handle_message(msg):
    chat_id=msg.get("chat",{}).get("id"); text=(msg.get("text") or "").strip()
    if text == "🧬 V25 Report":
        v25_report(chat_id); return
    return _old_handle_message_v25(msg)


# V25 Auto Scan : full auto, un seul meilleur setup, 1% risque, protections strictes.
def auto_scan_loop():
    while True:
        time.sleep(SCAN_INTERVAL_SECONDS)
        chat_id=STATE.get("last_scan_chat_id")
        if not (STATE.get("auto_scan") and chat_id):
            continue
        try:
            if count_open_trades(chat_id) >= MAX_OPEN_TRADES:
                continue
            guard = btc_volatility_guard()
            if not guard.get("ok", True):
                continue
            items=[(wallet, coin) for wallet, coins in WALLETS.items() for coin in coins]
            results=[]
            def _scan(item):
                wallet, coin = item
                try:
                    a=analyze_coin(coin,wallet,"auto_alert",chat_id)
                    ok, why = v25_gate(a) if V25_MODE else (is_clean_trade(a, MIN_AUTOTRADE_SCORE), "OK")
                    if ok and not was_recently_alerted(chat_id,a["symbol"],a["signal"],AUTO_SCAN_COOLDOWN_HOURS):
                        ok_safe, _ = account_safety_ok(chat_id, a)
                        if ok_safe: return a
                except Exception as e:
                    print("V25 autoscan pair error", item, e)
                return None
            from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
            with ThreadPoolExecutor(max_workers=SNIPER_WORKERS) as ex:
                futs=[ex.submit(_scan, item) for item in items]
                try:
                    for fut in as_completed(futs, timeout=max(SNIPER_MAX_SECONDS, 20)):
                        a=fut.result()
                        if a: results.append(a)
                except TimeoutError:
                    pass
            if not results:
                continue
            a=sorted(results,key=lambda x:(x.get("score",0),x.get("rr",0),x.get("vol_ratio",0)),reverse=True)[0]
            save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
            STATE["pending_trade"][chat_id]=a
            tg_send(chat_id,"🔔 <b>Auto Scan V25</b>\n🤖 Setup élite détecté → trade auto 1%", main_menu_keyboard())
            tg_send(chat_id,signal_message(a), main_menu_keyboard())
            tg_send(chat_id, execute_kraken_trade(chat_id, AUTO_TRADE_RISK_PERCENT), main_menu_keyboard())
        except Exception as e:
            print("V25 autoscan error:", e)


def send_home(chat_id):
    tg_send(chat_id, f"""🚀 <b>LVBXNT Crypto Bot</b>

✨ Version : <b>{V25_VERSION}</b>
⚙️ Mode : <b>{STATE['mode']}</b>
🔔 Auto Scan : <b>{'ON' if STATE['auto_scan'] else 'OFF'}</b>
🧬 V25 : <b>{'ON' if V25_MODE else 'OFF'}</b>

👇 Choisis une action""", main_menu_keyboard())



# ================= V25 UX PATCH : REPORT INLINE DASHBOARD ONLY =================
def v25_dashboard_inline_keyboard():
    return {"inline_keyboard": [[{"text": "🧬 V25 Report", "callback_data": "v25_report"}]]}


def dashboard(chat_id):
    """Dashboard avec bouton V25 Report en inline uniquement."""
    with db_conn() as con:
        rows = con.execute(
            "SELECT ts,wallet,coin,symbol,signal,price,sl,tp1,tp2,score,source FROM analyses WHERE chat_id=? ORDER BY ts DESC LIMIT 50",
            (chat_id,)
        ).fetchall()

    if not rows:
        empty_msg = "📈 <b>Dashboard Stats</b>\n\n📦 Total analyses : <b>0</b>\n🏆 Winrate : <b>N/A</b>\n💰 Profit estimé : <b>0.00%</b>\n📌 Trades ouverts : <b>0/max</b>\n\n📁 Historique :\n• Aucune encore"
        tg_send(chat_id, empty_msg, v25_dashboard_inline_keyboard())
        return

    by_date = {}
    wins = losses = open_trades = closed = 0
    pnl_total = 0.0
    coin_perf = {}

    for ts, wallet, coin, symbol, signal, price, sl, tp1, tp2, score, source in rows:
        d = datetime.fromtimestamp(ts).strftime("%d %m %Y")
        det = trade_result_details(symbol, signal, price, sl, tp1)
        st = det["status"]
        pnl = det["pnl"]
        by_date.setdefault(d, []).append((coin, signal, score, st, source, pnl))
        if st == "✅":
            wins += 1
            closed += 1
            pnl_total += pnl
        elif st == "❌":
            losses += 1
            closed += 1
            pnl_total += pnl
        elif st == "⏳" and signal in ["BUY", "SELL"]:
            open_trades += 1
        coin_perf.setdefault(coin, 0.0)
        coin_perf[coin] += pnl

    winrate = (wins / closed * 100) if closed else None
    best = sorted(coin_perf.items(), key=lambda x: x[1], reverse=True)[:3]
    worst = sorted(coin_perf.items(), key=lambda x: x[1])[:2]

    msg = "📈 <b>Dashboard Stats</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📦 Total analyses : <b>{len(rows)}</b>\n"
    msg += f"🏆 Winrate : <b>{winrate:.0f}%</b>\n" if winrate is not None else "🏆 Winrate : <b>N/A</b>\n"
    msg += f"✅ Gagnés : <b>{wins}</b> | ❌ Perdus : <b>{losses}</b>\n"
    msg += f"💰 Profit estimé : <b>{pnl_total:+.2f}%</b>\n"
    msg += f"📌 Trades ouverts : <b>{open_trades}/max</b>\n"

    if best:
        msg += "\n🔥 <b>Meilleurs coins</b>\n" + "".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin, p in best])
    if worst:
        neg = "".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin, p in worst if p < 0])
        if neg:
            msg += "\n⚠️ <b>Coins à surveiller</b>\n" + neg

    msg += "\n📁 <b>Historique par date</b>\n"
    for d, items in by_date.items():
        msg += f"\n📅 <b>{d}</b>\n"
        for coin, signal, score, st, source, pnl in items[:8]:
            msg += f"{st} {coin}/USDT • {signal} • {score}% • {pnl:+.2f}% • {source}\n"

    tg_send(chat_id, msg[:3600] + ai_dashboard_block(chat_id), v25_dashboard_inline_keyboard())


_old_handle_callback_query_v25_inline = handle_callback_query

def handle_callback_query(cb):
    data = cb.get("data") or ""
    callback_id = cb.get("id")
    msg = cb.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    if data == "v25_report" and chat_id:
        tg_answer_callback(callback_id, "V25 Report")
        v25_report(chat_id)
        return
    return _old_handle_callback_query_v25_inline(cb)

# ================= POLLING + WEBHOOK =================
def polling_loop():
    print("✅ LVBXNT Crypto Bot V25 HEDGE AI PRO PACK lancé en polling")
    while True:
        try:
            data=requests.get(f"{TG_API}/getUpdates", params={"timeout":25,"offset":STATE["last_update_id"]+1}, timeout=35).json()
            for upd in data.get("result",[]):
                STATE["last_update_id"]=max(STATE["last_update_id"],upd.get("update_id",0))
                if "message" in upd: handle_message(upd["message"])
                if "callback_query" in upd: handle_callback_query(upd["callback_query"])
        except KeyboardInterrupt: break
        except Exception as e: print("polling error:",e); time.sleep(3)

@app.route("/",methods=["GET"])
def health(): return jsonify({"ok":True,"bot":"LVBXNT Crypto Bot V25 HEDGE AI PRO PACK","mode":RUN_MODE})

@app.route(f"/webhook/{WEBHOOK_SECRET}",methods=["POST"])
def webhook():
    upd=request.get_json(force=True,silent=True) or {}
    if "message" in upd: handle_message(upd["message"])
    if "callback_query" in upd: handle_callback_query(upd["callback_query"])
    return jsonify({"ok":True})

@app.route("/set_webhook",methods=["GET"])
def set_webhook():
    if request.args.get("secret")!=ADMIN_SECRET: return jsonify({"ok":False,"error":"unauthorized"}),401
    if not EXTERNAL_BASE_URL: return jsonify({"ok":False,"error":"EXTERNAL_BASE_URL missing"})
    url=f"{EXTERNAL_BASE_URL}/webhook/{WEBHOOK_SECRET}"
    return jsonify(requests.get(f"{TG_API}/setWebhook", params={"url":url}, timeout=REQUEST_TIMEOUT).json())

if __name__=="__main__":
    init_db()
    if ENABLE_AUTOSCAN_THREAD:
        import threading
        threading.Thread(target=auto_scan_loop, daemon=True).start()
        threading.Thread(target=monitor_open_trades_loop, daemon=True).start()
    if RUN_MODE=="webhook": app.run(host="0.0.0.0", port=PORT)
    else: polling_loop()
