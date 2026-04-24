# -*- coding: utf-8 -*-
"""
LVBXNT Crypto Bot - V11 Auto Scan + Stats Dashboard + AI Learning
Local-first. Oracle-ready later. No Render.
APIs gratuites : Binance + CoinGecko + DexScreener.
"""

import os, time, sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import requests
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
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change_me_for_future_oracle")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change_me")

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
STATE = {"mode": "Normal", "auto_scan": False, "last_update_id": 0, "last_scan_chat_id": None}

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

def settings_keyboard(): return reply_keyboard([["🛡️ Prudent", "⚖️ Normal", "🚀 Agressif"], ["🏠 Menu"]])
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
    try:
        with db_conn() as con:
            rows=con.execute("SELECT symbol,signal,sl,tp1 FROM analyses WHERE chat_id=? AND signal IN ('BUY','SELL') ORDER BY ts DESC LIMIT 80",(chat_id,)).fetchall()
        return sum(1 for sym,sig,sl,tp1 in rows if get_trade_status(sym,sig,sl,tp1)=="⏳")
    except Exception: return 0

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

def analyze_coin(coin, wallet="", source="manual", chat_id=None):
    symbol=resolve_binance_symbol(coin)
    if not symbol: return {"ok":False,"coin":coin,"error":f"{coin}/USDT non disponible sur Binance"}
    rows1=get_klines(symbol,"1h",240); rows4=get_klines(symbol,"4h",220)
    if len(rows1)<200 or len(rows4)<200: return {"ok":False,"coin":coin,"error":"Pas assez de données marché"}
    t1,t4=trend(rows1),trend(rows4); closes=[r["close"] for r in rows1]; vols=[r["volume"] for r in rows1]
    price=closes[-1]; aa=atr(rows1,14) or price*0.015; vr=vols[-1]/(sum(vols[-20:])/20) if len(vols)>=20 and sum(vols[-20:]) else 1
    ctx=get_market_context(); dex=get_dex_info(coin); cfg=MODES[STATE["mode"]]; learn=learning_stats(chat_id,coin); bt=backtest_symbol(symbol,STATE["mode"])
    mtf_buy=t1["bullish"] and t4["bullish"]; mtf_sell=t1["bearish"] and t4["bearish"]; mtf=mtf_buy or mtf_sell
    mom_buy=t1["rsi"] is not None and 45<=t1["rsi"]<=cfg["rsi_buy_max"]; mom_sell=t1["rsi"] is not None and cfg["rsi_sell_min"]<=t1["rsi"]<=55
    liq_ok=dex["liquidity"]>=50000 or coin in ["BTC","ETH","SOL","XRP","ADA","AVAX","LINK","LTC","TON"]
    score=0; reasons=[]
    if t1["bullish"] or t1["bearish"]: score+=25; reasons.append("tendance 1H propre")
    elif t1["ema20"] and t1["ema50"] and ((t1["ema20"]>t1["ema50"] and price>t1["ema50"]) or (t1["ema20"]<t1["ema50"] and price<t1["ema50"])): score+=15; reasons.append("tendance 1H moyenne")
    if mtf: score+=20; reasons.append("confirmation 1H + 4H")
    if mom_buy or mom_sell: score+=15; reasons.append("RSI exploitable")
    if vr>=0.85: score+=10; reasons.append("volume correct")
    if ctx["mcap_change"]>-2.5: score+=8; reasons.append("marché global OK")
    if liq_ok: score+=8; reasons.append("liquidité OK")
    if vr>=1.4: score+=4; reasons.append("volume spike")
    if bt["winrate"] is not None and bt["winrate"]>=60 and bt["trades"]>=5: score+=5; reasons.append("backtest positif")
    ai_note="IA neutre"
    ai_min_score=cfg["min_score"]
    if learn["adjust"]>0:
        score+=learn["adjust"]; ai_min_score=max(62,ai_min_score-3); ai_note="IA positive : coin souvent gagnant"; reasons.append("IA : coin performant")
    elif learn["adjust"]<0:
        score+=learn["adjust"]; ai_min_score+=5; ai_note="IA prudente : coin souvent perdant"; reasons.append("IA : prudence renforcée")
    if bt["winrate"] is not None and bt["trades"]>=8:
        if bt["winrate"]>=65: ai_min_score=max(60,ai_min_score-2); reasons.append("IA : backtest solide")
        elif bt["winrate"]<45: ai_min_score+=5; reasons.append("IA : backtest faible")
    score=max(0,min(100,int(score)))
    signal="WAIT"; direction="Neutre"; bt_ok=bt["winrate"] is None or bt["winrate"]>=50
    if mtf_buy and mom_buy and score>=ai_min_score and bt_ok: signal="BUY"; direction="Bullish"
    elif mtf_sell and mom_sell and score>=ai_min_score and bt_ok: signal="SELL"; direction="Bearish"
    buffer=max(aa*0.15, price*0.0015)
    if signal=="BUY": sl=price-aa*cfg["atr_mult_sl"]; risk=price-sl; tp1=price+risk*cfg["rr1"]; tp2=price+risk*cfg["rr2"]
    elif signal=="SELL": sl=price+aa*cfg["atr_mult_sl"]; risk=sl-price; tp1=price-risk*cfg["rr1"]; tp2=price-risk*cfg["rr2"]
    else: sl=price-aa*1.4; tp1=price+aa*1.8; tp2=price+aa*2.8
    risk_txt="Faible" if score>=82 else "Moyen" if score>=70 else "Élevé"
    profitable=signal in ["BUY","SELL"] and score>=70 and risk_txt in ["Faible","Moyen"] and mtf
    if signal in ["BUY","SELL"] and not profitable:
        signal="WAIT"; direction="Neutre"; reasons.append("filtre rentable : setup rejeté")
    return {"ok":True,"wallet":wallet,"coin":coin,"symbol":symbol,"pair":f"{coin}/USDT","price":price,"ema20":t1["ema20"],"ema50":t1["ema50"],"ema200":t1["ema200"],"rsi":t1["rsi"],"atr":aa,"vol_ratio":vr,"dex":dex,"context":ctx,"score":score,"signal":signal,"direction":direction,"entry_low":price-buffer,"entry_high":price+buffer,"sl":sl,"tp1":tp1,"tp2":tp2,"risk":risk_txt,"mode":STATE["mode"],"reasons":reasons,"source":source,"mtf":{"confirm":mtf,"direction_1h":t1["direction"],"direction_4h":t4["direction"],"rsi_4h":t4["rsi"]},"learning":learn,"backtest":bt,"ai_note":ai_note,"ai_min_score":ai_min_score,"profitable_ok":profitable}

def is_clean_trade(a, min_score=70): return bool(a.get("ok") and a.get("signal") in ["BUY","SELL"] and a.get("score",0)>=min_score and a.get("risk") in ["Faible","Moyen"] and a.get("mtf",{}).get("confirm"))

def signal_message(a):
    if not a.get("ok"): return f"⚠️ <b>Analyse impossible</b>\n\n🪙 {a.get('coin','')}\n❌ {a.get('error','Erreur inconnue')}"
    sig_emoji="🟢" if a["signal"]=="BUY" else "🔴" if a["signal"]=="SELL" else "⚪"; verdict="TRADE POSSIBLE" if a["signal"] in ["BUY","SELL"] and a.get("profitable_ok") else "NO TRADE"
    rr=abs((a["tp1"]-a["price"])/(a["price"]-a["sl"])) if (a["price"]-a["sl"]) else 0
    ema_state="EMA20 > EMA50 > EMA200" if a["ema20"]>a["ema50"]>a["ema200"] else "EMA20 < EMA50 < EMA200" if a["ema20"]<a["ema50"]<a["ema200"] else "EMA non alignées"
    bt=a.get("backtest",{}); bt_txt="N/A" if bt.get("winrate") is None else f"{bt['winrate']:.0f}% ({bt['wins']}/{bt['trades']})"
    le=a.get("learning",{}); le_txt="Nouveau" if le.get("winrate") is None else f"{le['winrate']:.0f}% ({le['wins']}/{le['trades']})"
    mtf=a.get("mtf",{}); mtf_icon="✅" if mtf.get("confirm") else "❌"; reasons=", ".join(a.get("reasons",[])[:4]) or "conditions pas assez fortes"
    return f"""💎 <b>LVBXNT CRYPTO SIGNAL</b>
━━━━━━━━━━━━━━━━━━━━
🪙 <b>{a['pair']}</b> | 💼 {a['wallet'] or 'Crypto'}

📊 <b>Marché</b>
• Tendance 1H : <b>{mtf.get('direction_1h','N/A')}</b>
• Tendance 4H : <b>{mtf.get('direction_4h','N/A')}</b>
• Confirmation MTF : <b>{mtf_icon}</b>
• Prix : <b>{fmt_price(a['price'])}</b>
• RSI 1H : <b>{a['rsi']:.1f}</b>
• EMA : <b>{ema_state}</b>
• Volume : <b>{a['vol_ratio']:.2f}x</b>
• Liquidité DEX : <b>{fmt_money(a['dex']['liquidity'])}</b>

{sig_emoji} <b>Signal : {a['signal']}</b>
🎯 Entrée : <b>{fmt_price(a['entry_low'])} - {fmt_price(a['entry_high'])}</b>
🛑 SL : <b>{fmt_price(a['sl'])}</b>
🥇 TP1 : <b>{fmt_price(a['tp1'])}</b>
🥈 TP2 : <b>{fmt_price(a['tp2'])}</b>

⚠️ Risque : <b>{a['risk']}</b>
✅ Confiance : <b>{a['score']}%</b>
📐 R/R TP1 : <b>{rr:.2f}</b>
🧪 Backtest : <b>{bt_txt}</b>
🧠 IA Learning : <b>{le_txt}</b>\n🤖 Décision IA : <b>{a.get('ai_note','IA neutre')}</b>

🧠 <b>Stratégie Pro</b>
{reasons}

🏁 Verdict : <b>{verdict}</b>
━━━━━━━━━━━━━━━━━━━━
⚠️ Pas un conseil financier. Max 1–2 trades ouverts."""

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
        tg_send(chat_id,"📈 <b>Dashboard Stats</b>\n\n📦 Total analyses : <b>0</b>\n🏆 Winrate : <b>N/A</b>\n💰 Profit estimé : <b>0.00%</b>\n📌 Trades ouverts : <b>0/2 max</b>\n\n📁 Historique :\n• Aucune encore",main_menu_keyboard()); return
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
    msg+=f"📌 Trades ouverts : <b>{open_trades}/2 max</b>\n"
    if best:
        msg+="\n🔥 <b>Meilleurs coins</b>\n" + "".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin,p in best])
    if worst:
        neg="".join([f"• {coin}/USDT : <b>{p:+.2f}%</b>\n" for coin,p in worst if p<0])
        if neg: msg+="\n⚠️ <b>Coins à surveiller</b>\n" + neg
    msg+="\n📁 <b>Historique par date</b>\n"
    for d,items in by_date.items():
        msg+=f"\n📅 <b>{d}</b>\n"
        for coin,signal,score,st,source,pnl in items[:8]: msg+=f"{st} {coin}/USDT • {signal} • {score}% • {pnl:+.2f}% • {source}\n"
    tg_send(chat_id,msg[:3900],main_menu_keyboard())

def run_sniper(chat_id):
    """Bouton Sniper = version stricte 90%+."""
    open_trades=count_open_trades(chat_id)
    if open_trades>=2: tg_send(chat_id,"🎯 <b>Sniper</b>\n\n⛔ Max 2 trades ouverts atteint.",main_menu_keyboard()); return
    tg_send(chat_id,"🎯 <b>Sniper</b>\n\nScan premium strict en cours... ⏳\n\nConditions : confiance 90%+, risque Faible/Moyen, confirmation 1H+4H.")
    results=[]
    for wallet,coins in WALLETS.items():
        for coin in coins:
            a=analyze_coin(coin,wallet,"sniper",chat_id); bt=a.get("backtest",{}) if a.get("ok") else {}
            if is_clean_trade(a,90) and (bt.get("winrate") is None or bt.get("winrate",0)>=55): results.append(a)
    picks=sorted(results,key=lambda x:(x["score"],x.get("backtest",{}).get("winrate") or 0),reverse=True)[:min(3,2-open_trades)]
    if not picks: tg_send(chat_id,"🎯 <b>Sniper</b>\n\n❌ <b>NO TRADE</b>\n\nAucun setup 90%+ propre maintenant. Le bot préfère attendre.",main_menu_keyboard()); return
    tg_send(chat_id,f"🎯 <b>Sniper</b>\n\n✅ Setup(s) premium trouvé(s) : <b>{len(picks)}</b>",main_menu_keyboard())
    for a in picks: save_analysis(chat_id,a); mark_alert_sent(chat_id,a); tg_send(chat_id,signal_message(a),main_menu_keyboard())

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
    tg_send(chat_id,f"📡 <b>Notifications Auto</b> : <b>{'ON' if STATE['auto_scan'] else 'OFF'}</b>\n\nQuand Auto Scan est ON, le bot scanne tes coins et t’envoie seulement les nouveaux setups Sniper 90%+.",main_menu_keyboard())

def auto_scan_loop():
    """Auto Scan : scanne en silence et envoie uniquement les nouveaux setups Sniper 90%+."""
    while True:
        time.sleep(SCAN_INTERVAL_SECONDS)
        chat_id=STATE.get("last_scan_chat_id")
        if STATE.get("auto_scan") and chat_id:
            try:
                if count_open_trades(chat_id) >= 2:
                    continue
                results=[]
                for wallet,coins in WALLETS.items():
                    for coin in coins:
                        a=analyze_coin(coin,wallet,"auto_alert",chat_id)
                        if is_clean_trade(a,90) and not was_recently_alerted(chat_id,a["symbol"],a["signal"],6):
                            results.append(a)
                picks=sorted(results,key=lambda x:x["score"],reverse=True)[:max(0,2-count_open_trades(chat_id))]
                for a in picks:
                    save_analysis(chat_id,a); mark_alert_sent(chat_id,a)
                    tg_send(chat_id,"🔔 <b>Auto Scan</b>\n\nNouveau setup Sniper détecté 👇")
                    tg_send(chat_id,signal_message(a),main_menu_keyboard())
            except Exception as e: print("autoscan error:",e)

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

def handle_message(msg):
    chat_id=msg.get("chat",{}).get("id"); text=(msg.get("text") or "").strip()
    if not chat_id or not text: return
    if text.startswith("/start") or text in ["🏠 Menu","Menu","🏡 Menu"]: send_home(chat_id); return
    if text.startswith("/analyze"):
        parts=text.split()
        if len(parts)>=2:
            coin=parts[1].replace("/USDT","").upper(); wallet=next((w for w,cs in WALLETS.items() if coin in cs),"")
            a=analyze_coin(coin,wallet,"manual",chat_id)
            if a.get("signal") in ["BUY","SELL"] and count_open_trades(chat_id)>=2: a["signal"]="WAIT"; a["direction"]="Neutre"; a.setdefault("reasons",[]).append("max 2 trades ouverts atteint")
            save_analysis(chat_id,a); tg_send(chat_id,signal_message(a),main_menu_keyboard())
        else: send_wallets(chat_id,"analysis")
        return
    if text=="📊 Analyse Premium": send_wallets(chat_id,"analysis"); return
    if text=="💼 Watchlist": send_wallets(chat_id,"watchlist"); return
    if text=="💼 Wallets": send_wallets(chat_id,"analysis"); return
    wallet=wallet_from_text(text)
    if wallet: send_wallet_coins(chat_id,wallet,"analysis"); return
    coin=clean_coin_from_text(text)
    if coin:
        wallet=next((w for w,cs in WALLETS.items() if coin in cs),""); a=analyze_coin(coin,wallet,"manual",chat_id)
        if a.get("signal") in ["BUY","SELL"] and count_open_trades(chat_id)>=2: a["signal"]="WAIT"; a["direction"]="Neutre"; a.setdefault("reasons",[]).append("max 2 trades ouverts atteint")
        save_analysis(chat_id,a); tg_send(chat_id,signal_message(a),main_menu_keyboard()); return
    if text=="⚙️ Réglages Pro": send_settings(chat_id); return
    if text in ["🛡️ Prudent","⚖️ Normal","🚀 Agressif"]:
        STATE["mode"]="Prudent" if "Prudent" in text else "Agressif" if "Agressif" in text else "Normal"; send_settings(chat_id); return
    if text=="📈 Dashboard": dashboard(chat_id); return
    if text=="🎯 Sniper": run_sniper(chat_id); return
    if text=="🧪 Backtest": run_backtest(chat_id); return
    if text=="🔔 Auto Scan": run_auto_scan(chat_id); return
    tg_send(chat_id,"Je n’ai pas compris 👇",main_menu_keyboard())

# ================= POLLING + WEBHOOK =================
def polling_loop():
    print("✅ LVBXNT Crypto Bot V11 lancé en polling")
    while True:
        try:
            data=requests.get(f"{TG_API}/getUpdates", params={"timeout":25,"offset":STATE["last_update_id"]+1}, timeout=35).json()
            for upd in data.get("result",[]):
                STATE["last_update_id"]=max(STATE["last_update_id"],upd.get("update_id",0))
                if "message" in upd: handle_message(upd["message"])
        except KeyboardInterrupt: break
        except Exception as e: print("polling error:",e); time.sleep(3)

@app.route("/",methods=["GET"])
def health(): return jsonify({"ok":True,"bot":"LVBXNT Crypto Bot V11","mode":RUN_MODE})

@app.route(f"/webhook/{WEBHOOK_SECRET}",methods=["POST"])
def webhook():
    upd=request.get_json(force=True,silent=True) or {}
    if "message" in upd: handle_message(upd["message"])
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
    if RUN_MODE=="webhook": app.run(host="0.0.0.0", port=PORT)
    else: polling_loop()
