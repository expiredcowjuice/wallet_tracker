from decimal import Decimal
import os
import requests

import pandas as pd
from dotenv import load_dotenv

from db import add_wallet_balance, get_previous_wallet_balance, get_all_wallets, get_all_tokens

load_dotenv()

API_KEY = os.getenv('SOLANA_TRACKER_API_KEY')
BASE_URL = 'https://data.solanatracker.io'

tokens = get_all_tokens()
wallets = get_all_wallets()

def get_wallet_balance(wallet_address):
    """
    Get the balance of a wallet, return dataframe of all tokens and their balances
    """
    url = f'{BASE_URL}/wallet/{wallet_address}'
    headers = {'x-api-key': API_KEY}
    response = requests.get(url, headers=headers).json()

    tokens = response['tokens']
    df = pd.DataFrame(tokens).drop(columns=['pools', 'events', 'risk', 'buys', 'sells', 'txns'])
    df['token_address'] = df['token'].apply(lambda x: x['mint'])
    df.drop(columns=['token'], inplace=True)

    return df

def get_token_name(token_address):
    """
    Get the name of a token
    """
    token = [token for token in tokens if token['token_address'] == token_address][0]
    return token['name']

def get_wallet_alias(wallet_address):
    """
    Get the alias of a wallet
    """
    wallet = [wallet for wallet in wallets if wallet['wallet_address'] == wallet_address][0]
    return wallet['alias']

def format_balance_change(row):
    """
    Format balance changes with emojis and colors
    🔴 for decrease, 🟢 for increase
    ⬆️ for increase, ⬇️ for decrease
    """
    token_name = get_token_name(row['token_address'])
    wallet_alias = get_wallet_alias(row['wallet_address'])
    
    # Determine direction of change
    direction_emoji = "⬆️" if row['balance_change'] > 0 else "⬇️"
    color_emoji = "🟢" if row['balance_change'] > 0 else "🔴"
    
    message = (
        f"{color_emoji} {wallet_alias} {token_name}: \n"
        f"Previous: {row['previous_balance']:.4f} \n"
        f"Current:  {row['current_balance']:.4f} \n"
        f"Change:   {direction_emoji} {abs(row['balance_change']):.4f} "
        f"(~${abs(row['value_change']):.2f}USD)"
    )
    
    return message

def update_wallet_balances():
    """
    Update the balance of all wallets
    """

    # Get current wallet balances
    current_wallet_balances = pd.DataFrame()
    token_addresses = [token['token_address'] for token in tokens]

    for wallet in wallets:
        df = get_wallet_balance(wallet['wallet_address'])

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
    previous_wallet_balances = pd.DataFrame(get_previous_wallet_balance())
    previous_wallet_balances = previous_wallet_balances[previous_wallet_balances['token_address'].isin(token_addresses)]

    # Compare current and previous balances
    current_wallet_balances = current_wallet_balances.sort_values(['wallet_address', 'token_address']).reset_index(drop=True)
    previous_wallet_balances = previous_wallet_balances.sort_values(['wallet_address', 'token_address']).reset_index(drop=True)

    # Assert that the two wallets have the same dimensions
    assert current_wallet_balances.shape == previous_wallet_balances.shape
    
    # Calculate changes
    balance_changes = pd.DataFrame({
        'wallet_address': current_wallet_balances['wallet_address'],
        'token_address': current_wallet_balances['token_address'],
        'previous_balance': previous_wallet_balances['balance'],
        'current_balance': current_wallet_balances['balance'],
        'balance_change': current_wallet_balances['balance'].apply(Decimal) - previous_wallet_balances['balance'],
        'value_change': current_wallet_balances['value'].apply(Decimal) - previous_wallet_balances['value']
    })

    # Ignore SOL
    significant_changes = balance_changes[(abs(balance_changes['balance_change']) > 0.5) & (balance_changes['token_address'] != 'So11111111111111111111111111111111111111112')]

    if len(significant_changes) > 0:
        print("Significant balance changes:")
        for _, row in significant_changes.iterrows():
            token_name = get_token_name(row['token_address'])
            wallet_alias = get_wallet_alias(row['wallet_address'])
            print(f"{wallet_alias} {token_name}: \n previous: {row['previous_balance']} \n current: {row['current_balance']} \n change: {row['balance_change']} (~${round(row['value_change'], 2)}USD)")
    else:
        print("No significant balance changes")

    # Update wallet balances in db
    for _, row in current_wallet_balances.iterrows():
        add_wallet_balance(row['wallet_address'], row['token_address'], row['balance'], row['value'])

if __name__ == '__main__':
    update_wallet_balances()