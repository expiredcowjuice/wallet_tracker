from datetime import datetime
from decimal import Decimal
import pytz

import pandas as pd

from db import get_previous_wallet_balance, get_all_wallets, get_all_tokens, upsert_wallets, upsert_tokens, upsert_wallet_balances
from solana_tracker import get_wallet_balance, get_token_info


# Move these into an async initialization function
tokens = []
wallets = []

########################
# Helper Functions
########################

def format_balance_change(row):
    """
    Format balance changes for embed
    Returns a tuple of (title, fields)
    """
    token_symbol = get_token_symbol(row['token_address'])
    wallet_alias = get_wallet_alias(row['wallet_address'])
    
    is_increase = row['balance_change'] > 0
    direction_emoji = "⬆️" if is_increase else "⬇️"
    color_emoji = "🟢" if is_increase else "🔴"
    
    title = f"{color_emoji} {wallet_alias} - {token_symbol}"
        
    fields = [
        {
            'name': 'Previous Balance',
            'value': f'{row["previous_balance"]:,.2f}',
            'inline': True
        },
        {
            'name': 'Current Balance',
            'value': f'{row["current_balance"]:,.2f}',
            'inline': True
        },
        {
            'name': 'Change',
            'value': f'{direction_emoji} {abs(row["balance_change"]):,.2f} (~${abs(row["value_change"]):,.2f} USD)',
            'inline': False
        }
    ]
    
    return title, fields

def format_address(address):
    """
    Format an address with the first 4 and last 4 characters
    """
    return f"{address[:4]}...{address[-4:]}"

def ensure_list(item):
    """
    Ensure an item is a list
    """
    return [item] if not isinstance(item, list) else item

def format_datetime(utc_time: datetime) -> str:
    """
    Format a UTC datetime object to local time
    """
    local_tz = datetime.now().astimezone().tzinfo  # Get local timezone
    local_time = utc_time.replace(tzinfo=pytz.UTC).astimezone(local_tz)
    return local_time.strftime('%Y-%m-%d %H:%M %Z')

########################
# Wallet Tracker Functions
########################

async def initialize():
    """
    Initialize global variables
    """
    global tokens, wallets
    tokens = await get_all_tokens()
    wallets = await get_all_wallets()

def get_token_name(token_address):
    """
    Get the name of a token
    """
    token = [token for token in tokens if token['token_address'] == token_address][0]
    return token['name']

def get_token_symbol(token_address):
    """
    Get the symbol of a token
    """
    token = [token for token in tokens if token['token_address'] == token_address][0]
    return token['symbol']

def get_wallet_alias(wallet_address):
    """
    Get the alias of a wallet
    """
    wallet = [wallet for wallet in wallets if wallet['wallet_address'] == wallet_address][0]
    return wallet['alias']


async def check_wallet_balances(status_callback=None) -> tuple[list[dict], str]:
    """
    Check the balance of all wallets, reports changes and upserts new balances to db
    Returns a tuple of (changes, previous_check_time)
    """

    # Get current wallet balances
    current_wallet_balances = pd.DataFrame()
    token_addresses = [token['token_address'] for token in tokens]

    for wallet in wallets:
        if status_callback:
            await status_callback(wallet['alias'])
            
        try:
            df = await get_wallet_balance(wallet['wallet_address'])
        except Exception as e:
            print(f"Error getting wallet balance for {wallet['alias']}: {str(e)}")
            continue # Issue with dealing with API limits

        # Add missing tokens with 0 balance, captures when a wallet sells out all of a token
        missing_token_balances = pd.DataFrame({'token_address': token_addresses, 'balance': 0, 'value': 0})
        df = pd.concat([df, missing_token_balances]).drop_duplicates(subset=['token_address'], keep='first')
        
        # Filter out any tokens that are not in the list of tokens
        df = df[df['token_address'].isin(token_addresses)]

        # Add wallet address to dataframe
        df = df.assign(wallet_address=wallet['wallet_address'])

        # Append to current wallet balances
        current_wallet_balances = pd.concat([current_wallet_balances, df])

    # Get previous wallet balances
    previous_wallet_balances = pd.DataFrame(await get_previous_wallet_balance())
    previous_wallet_balances = previous_wallet_balances[previous_wallet_balances['token_address'].isin(token_addresses)]

    # Compare current and previous balances
    current_wallet_balances = current_wallet_balances.sort_values(['wallet_address', 'token_address']).reset_index(drop=True)
    previous_wallet_balances = previous_wallet_balances.sort_values(['wallet_address', 'token_address']).reset_index(drop=True)

    # Assert that the two wallets have the same length
    assert len(current_wallet_balances) == len(previous_wallet_balances)
    
    # Calculate changes
    balance_changes = pd.DataFrame({
        'wallet_address': current_wallet_balances['wallet_address'],
        'token_address': current_wallet_balances['token_address'],
        'previous_balance': previous_wallet_balances['balance'],
        'current_balance': current_wallet_balances['balance'],
        'balance_change': current_wallet_balances['balance'].apply(Decimal) - previous_wallet_balances['balance'],
        'value_change': current_wallet_balances['value'].apply(Decimal) - previous_wallet_balances['value'],
    })

    # Ignore SOL
    significant_changes = balance_changes[(abs(balance_changes['balance_change']) > 0.5) & (balance_changes['token_address'] != 'So11111111111111111111111111111111111111112')]

    # Update wallet balances in db
    # Convert DataFrame to list of tuples for database insertion
    current_wallet_balances = current_wallet_balances[current_wallet_balances['balance'] > 0]
    current_wallet_balances = list(zip(
        current_wallet_balances['wallet_address'],
        current_wallet_balances['token_address'],
        current_wallet_balances['balance'],
        current_wallet_balances['value']
    ))
    await upsert_wallet_balances(current_wallet_balances)

    previous_check_time = format_datetime(previous_wallet_balances['previous_check_time'][0]) if previous_wallet_balances['previous_check_time'][0] else 'No previous data'

    return significant_changes.to_dict(orient='records'), previous_check_time

async def list_wallets():
    """
    Return list of wallet dictionaries
    """
    return wallets

async def list_tokens():
    """
    Return list of token dictionaries
    """
    return tokens

async def add_wallets(wallets: list[dict]):
    """
    Add wallets
    """
    result = await upsert_wallets(wallets)
    
    if len(result['upserted']) == 1:
        response = f'Successfully added 1 new wallet: {result["upserted"][0]["alias"]} ({format_address(result["upserted"][0]["wallet_address"])})'
    else:
        response = f'Added {len(result["upserted"])} new wallets'
    
    if result['conflicts']:
        conflict_list = ", ".join(
            f'{c["wallet_address"]} ({c["alias"]})' 
            for c in result['conflicts']
        )
        response += f'\nSkipped existing wallets: {conflict_list}'
    
    return response

async def add_tokens(tokens: list[str]):
    """
    Add tokens
    """
    tokens = [await get_token_info(token) for token in tokens]

    result = await upsert_tokens(tokens)

    if len(result['upserted']) == 1:
        token = result['upserted'][0]
        response = f'Successfully added 1 new token: ${token["symbol"]} {token["name"]} ({format_address(token["token_address"])})'
    else:
        response = f'Added {len(result["upserted"])} new tokens'
    
    if result['conflicts']:
        conflict_list = ", ".join(
            f'{c["token_address"]} (${c["symbol"]} {c["name"]})' 
            for c in result['conflicts']
        )
        response += f'\nSkipped existing tokens: {conflict_list}'
    
    return response

def create_token_summary(changes):
    """Create a summary of token flows"""
    token_stats = {}
    
    for change in changes:
        token_addr = change['token_address']
        token_symbol = get_token_symbol(token_addr)
        
        if token_addr not in token_stats:
            token_stats[token_addr] = {
                'symbol': token_symbol,
                'buy_amount': 0,
                'sell_amount': 0, 
                'buy_value': 0,
                'sell_value': 0,
                'buying_wallets': set(),
                'selling_wallets': set()
            }
        
        if change['balance_change'] > 0:
            token_stats[token_addr]['buy_amount'] += change['balance_change']
            token_stats[token_addr]['buy_value'] += change['value_change']
            token_stats[token_addr]['buying_wallets'].add(change['wallet_address'])
        else:
            token_stats[token_addr]['sell_amount'] += abs(change['balance_change'])
            token_stats[token_addr]['sell_value'] += abs(change['value_change'])
            token_stats[token_addr]['selling_wallets'].add(change['wallet_address'])
    
    # Format the summary
    summary_lines = []
    
    for stats in token_stats.values():
        summary = (
            f"**{stats['symbol']}**\n"
            f"⬆️ Buys: {stats['buy_amount']:,.2f} (${stats['buy_value']:,.2f}) from {len(stats['buying_wallets'])} wallets\n"
            f"⬇️ Sells: {stats['sell_amount']:,.2f} (${stats['sell_value']:,.2f}) from {len(stats['selling_wallets'])} wallets\n"
        )
        summary_lines.append(summary)
    
    return '\n'.join(summary_lines)