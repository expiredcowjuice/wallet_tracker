import os
import requests

import pandas as pd
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv('SOLANA_TRACKER_API_KEY')
BASE_URL = 'https://data.solanatracker.io'

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