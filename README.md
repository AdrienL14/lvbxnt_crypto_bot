# LVBXNT Crypto Bot V11 Auto Scan Stats AI

Upgrade ajouté sans casser le bot actuel :
- 📡 Auto Scan : scan silencieux + alertes intégrées dans Auto Scan pour nouveaux setups Sniper 90%+
- 📈 Dashboard stats : winrate, gagnés/perdus, profit estimé, meilleurs coins
- 🧠 IA Learning : ajuste la prudence selon trades gagnés/perdus + backtest
- 🎯 Bouton Sniper : nom propre avec emoji uniquement
- 🧪 Backtest automatique conservé
- Confirmation multi-timeframe 1H + 4H conservée
- Filtre rentable : confiance >= 70%, risque Faible/Moyen, max 1-2 trades ouverts

## Installation
```bash
pip install -r requirements.txt
```

## Config
Copie `.env.example` en `.env`, puis mets ton token Telegram :
```env
BOT_TOKEN=ton_token
```

## Lancement local
```bash
python app.py
```
