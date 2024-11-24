import os
import requests

from dotenv import load_dotenv
import numpy as np
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
