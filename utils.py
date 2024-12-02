import datetime
import logging
import sys

import discord

from wallet_tracker import format_balance_change, create_token_summary, format_trades


# Create single logger instance
logger = logging.getLogger('discord_wallet_tracker')
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def create_wallet_balance_change_embed(changes_batch, previous_check_time=None, page=1, total_pages=1):
    embed = discord.Embed(
        title='💰 Wallet Balance Changes',
        description=f'Recent significant changes in wallet balances{f" (Page {page}/{total_pages})" if total_pages > 1 else ""}\n(as of {previous_check_time if previous_check_time else ""})',
        color=discord.Color.brand_green(),
        timestamp=datetime.datetime.now()
    )
    
    for change in changes_batch:
        name, fields = format_balance_change(change)
        
        embed.add_field(
            name=name,
            value='\n'.join(
                f"{field['name']}: {field['value']}"
                for field in fields
            ),
            inline=False
        )
    
    embed.set_footer(text='Last updated')
    return embed

def create_token_flow_summary_embed(changes):
    embed = discord.Embed(
        title='📊 Token Flow Summary',
        description='Aggregate canges by token',
        color=discord.Color.dark_teal(),
        timestamp=datetime.datetime.now()
    )
    
    summary = create_token_summary(changes)
    embed.description = summary
    
    embed.set_footer(text='Last updated')
    return embed

def create_wallet_trade_embed(trades):
    embed = discord.Embed(
        title='📈 Wallet Trades',
        description='Recent trades for wallet',
        color=discord.Color.teal(),
        timestamp=datetime.datetime.now()
    )

    for trade in trades:
        solscan_link = f'https://solscan.io/tx/{trade["tx_hash"]}'
        name, fields = format_trades(trade)

        embed.add_field(
            name=name,
            value='\n'.join(
                f"{field['name']}: {field['value']}"
                for field in fields
            ) + f"\n[{trade['tx_hash'][:4]}...{trade['tx_hash'][-4:]}]({solscan_link})",
            inline=False
        )
    
    embed.set_footer(text='Last updated')
    return embed
