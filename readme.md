# 🐋 Solana Whale Tracker Bot

A Discord bot that tracks wallet balance changes for selected Solana addresses and tokens.

## 📝 Overview

Unlike traditional implementations that only track on-chain trades, this bot monitors actual wallet balances to catch whale movements that might be missed through conventional tracking methods. This is especially useful since:

- Whales often avoid direct swaps
- Many trades happen through private means (OTC, DCA)
- Complex trading patterns can obscure traditional tracking

## 🚀 Features

- Track multiple wallet addresses and tokens
- Monitor balance changes in real-time
- Store historical data in PostgreSQL
- Automated scheduled checks
- Manual balance check commands
- Discord notifications for significant changes

## 💡 How It Works

1. Input wallet addresses and tokens to track
2. Bot fetches wallet balances using Solana Tracker API
3. Data is stored and compared in PostgreSQL database
4. Significant balance changes trigger Discord notifications
5. Runs on schedule with manual check option

## 🛠️ Technologies

- Discord.py
- PostgreSQL
- Solana Tracker API
- Python Scheduler

## Setup

1. Install dependencies
```
pip install -r requirements.txt
```

2. Create `.env` file
```
DISCORD_BOT_TOKEN=<discord token>
DISCORD_CHANNEL_ID=<discord channel id>
DATABASE_URL=<database url>
SOLANA_TRACKER_API_KEY=<solana tracker api key>
```

3. Run the bot
```
python discord_bot.py
```

## Commands

- `/check_wallet_balances` - Check all wallet balances
- `/add_wallet` - Add a wallet to the database
- `/add_token` - Add a token to the database
- `/bulk_add_wallets` - Bulk add wallets from a csv file
- `/bulk_add_tokens` - Bulk add tokens from a csv file
- `/list_wallets` - List all wallets
- `/list_tokens` - List all tokens