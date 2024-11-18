from decimal import Decimal

import pandas as pd

from db import add_wallet_balance, get_previous_wallet_balance, get_all_wallets, get_all_tokens
from solana_tracker import get_wallet_balance

tokens = get_all_tokens()
wallets = get_all_wallets()

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

async def check_wallet_balances():
    """
    Check the balance of all wallets and report changes
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

    # Report changes
    messages = []
    for _, row in significant_changes.iterrows():
        message = format_balance_change(row)
        messages.append(message)

    if messages:
        response = "\n".join(messages)
    else:
        response = "No significant balance changes"

    # Update wallet balances in db
    for _, row in current_wallet_balances.iterrows():
        add_wallet_balance(row['wallet_address'], row['token_address'], row['balance'], row['value'])

    return response

if __name__ == '__main__':
    print(check_wallet_balances())
