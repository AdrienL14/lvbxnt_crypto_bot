# LVBXNT Crypto Bot — V25 Hedge AI Pro Pack

## Nouveau dans V25
- 🧠 IA avancée locale : ajuste le score selon ton journal de trades
- 🛡️ Hedge Shield : bloque les trades quand BTC/altcoins sont trop risqués
- 🎯 Entrée unique smart limit : plus de zone, une seule entrée précise
- ⚡ Sniper turbo conservé : top 3 setups qualité
- 🤖 Auto Scan exclusif : full auto Kraken en 1% sur le meilleur setup uniquement
- 💰 Risk Engine Pro : réduction du risque après perte + protections existantes
- 📊 V25 Report : performance, IA, protections actives
- 🖥️ Contabo ready : fichiers inclus pour futur lancement 24/7
- ❌ Copy trading volontairement absent

## Installation locale
```bash
pip install -r requirements.txt
python app.py
```

## Important
Garde ton fichier `.env` actuel. Ne le remplace pas.

## Variables V25 optionnelles
```env
V25_MODE=1
HEDGE_SHIELD=1
HEDGE_MAX_BTC_MOVE_PERCENT=2.6
V25_MIN_SCORE=90
V25_MIN_RR=1.85
V25_MIN_VOLUME_RATIO=1.30
V25_MIN_AI_WINRATE=54
V25_SMART_LIMIT_OFFSET_ATR=0.06
V25_REDUCE_RISK_AFTER_LOSS=1
V25_DRAWDOWN_PAUSE_PERCENT=4
V25_MAX_CORRELATED_TRADES=1
V25_TRADE_SESSION_FILTER=1
V25_MIN_HISTORY_TRADES_FOR_AI=12
V25_EXECUTION_RETRY=2
```

## Contabo
Le bot reste local pour le moment. Quand tu as ton VPS, demande simplement : **GO CONTABO**.
Les fichiers `contabo/` sont déjà prêts pour faciliter le passage 24/7.
