import os
import requests

from dotenv import load_dotenv
import pandas as pd


load_dotenv()

API_KEY_1 = os.getenv('SOLANA_TRACKER_API_KEY_1')
API_KEY_2 = os.getenv('SOLANA_TRACKER_API_KEY_2')
BASE_URL = 'https://data.solanatracker.io'
api_key_list = [API_KEY_1, API_KEY_2]
_current_api_key_index = 0

def get_api_key():
    """
    Alternates between the two API keys with each call
    """
    global _current_api_key_index
    api_key = api_key_list[_current_api_key_index]
    _current_api_key_index = (_current_api_key_index + 1) % len(api_key_list)
    return api_key

async def get_wallet_balance(wallet_address):
    """
    Get the balance of a wallet, return dataframe of all tokens and their balances
    """
    url = f'{BASE_URL}/wallet/{wallet_address}'
    headers = {'x-api-key': get_api_key()}
    response = requests.get(url, headers=headers).json()

    tokens = response['tokens']
    df = pd.DataFrame(tokens).drop(columns=['pools', 'events', 'risk', 'buys', 'sells', 'txns'])
    df['token_address'] = df['token'].apply(lambda x: x.get('mint')) # Error where some tokens don't have a mint, skip over them
    df.drop(columns=['token'], inplace=True)
    df.dropna(inplace=True)

    return df

async def get_token_info(token_address):
    """
    Get the info of a token
    """
    url = f'{BASE_URL}/tokens/{token_address}'
    headers = {'x-api-key': get_api_key()}
    response = requests.get(url, headers=headers).json()

    token = response['token']

    return (
        token['mint'],
        token['name'],
        token['symbol'],
    )

async def get_wallet_trades(wallet_address):
    """
    Get the trades of a wallet
    """
    url = f'{BASE_URL}/wallet/{wallet_address}/trades'
    headers = {'x-api-key': get_api_key()}
    response = requests.get(url, headers=headers).json()

    trades = response['trades']
    df = pd.DataFrame(trades).drop(columns=['wallet'])
    df = df.assign(
        from_token=df['from'].apply(lambda x: x.get('token', {}).get('symbol')),
        to_token=df['to'].apply(lambda x: x.get('token', {}).get('symbol')),
        price=df['price'].apply(lambda x: x['usd']),
        volume=df['volume'].apply(lambda x: x['usd']),
        timestamp=pd.to_datetime(df['time'], unit='ms')
    )
    df.rename(columns={'tx': 'tx_hash'}, inplace=True)
    df.drop(columns=['from', 'to', 'time'], inplace=True)
    df.dropna(inplace=True)

    return df
