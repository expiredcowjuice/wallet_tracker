import os

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

load_dotenv()

def get_db_connection():
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            wallet_address VARCHAR(128) PRIMARY KEY,
            alias VARCHAR(128),
        );
        CREATE TABLE IF NOT EXISTS tokens (
            token_address VARCHAR(128) PRIMARY KEY,
            name VARCHAR(128),
            symbol VARCHAR(32)
        );
        CREATE TABLE IF NOT EXISTS wallet_balance_history (
            wallet_address VARCHAR(128) REFERENCES wallets(wallet_address),
            token_address VARCHAR(128) REFERENCES tokens(token_address),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            balance NUMERIC NOT NULL,
            value NUMERIC NOT NULL,
            PRIMARY KEY (wallet_address, token_address, timestamp)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

async def upsert_wallets(wallets):
    """
    Upsert wallets
    wallets: list of tuples (wallet_address, alias)
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # First, try to insert and get successful inserts
    execute_values(cursor, """
        INSERT INTO wallets (wallet_address, alias)
        VALUES %s
        ON CONFLICT (wallet_address) DO NOTHING
        RETURNING wallet_address, alias;
    """, wallets)
    
    upserted = cursor.fetchall()
    
    # Find which ones weren't inserted (conflicts)
    upserted_wallets = [row['wallet_address'] for row in upserted]
    conflicts = [
        {'wallet_address': addr, 'alias': alias}
        for addr, alias in wallets
        if addr not in upserted_wallets
    ]
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'upserted': upserted,
        'conflicts': conflicts
    }

async def upsert_tokens(tokens):
    """
    Upsert tokens
    tokens: list of tuples (token_address, name, symbol)
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    execute_values(cursor, """
        INSERT INTO tokens (token_address, name, symbol)
        VALUES %s
        ON CONFLICT (token_address) DO NOTHING
        RETURNING token_address, name, symbol;
    """, tokens)
    upserted = cursor.fetchall()

    upserted_tokens = [row['token_address'] for row in upserted]
    conflicts = [
        {'token_address': addr, 'name': name, 'symbol': symbol}
        for addr, name, symbol in tokens
        if addr not in upserted_tokens
    ]
    conn.commit()
    cursor.close()
    conn.close()

    return {
        'upserted': upserted,
        'conflicts': conflicts
    }

async def upsert_wallet_balances(wallet_balances):
    """
    Upsert wallet balances
    wallet_balances: list of tuples (wallet_address, token_address, balance, value)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_values(cursor, """
        INSERT INTO wallet_balance_history (wallet_address, token_address, balance, value)
        VALUES %s
    """, wallet_balances)
    conn.commit()
    cursor.close()
    conn.close()

async def get_all_wallets():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM wallets;")
    wallets = cursor.fetchall()
    cursor.close()
    conn.close()
    return wallets

async def get_all_tokens():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM tokens;")
    tokens = cursor.fetchall()
    cursor.close()
    conn.close()
    return tokens

async def get_previous_wallet_balance():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        WITH latest_timestamp AS (
            SELECT MAX(timestamp) as max_ts
            FROM wallet_balance_history
        )
        SELECT 
            w.wallet_address,
            t.token_address,
            (SELECT max_ts FROM latest_timestamp) as previous_check_time,
            COALESCE(
                (SELECT balance
                 FROM wallet_balance_history wbh
                 WHERE wbh.wallet_address = w.wallet_address 
                 AND wbh.token_address = t.token_address
                 AND wbh.timestamp = (SELECT max_ts FROM latest_timestamp)
                ),
                0
            ) as balance,
            COALESCE(
                (SELECT value
                 FROM wallet_balance_history wbh
                 WHERE wbh.wallet_address = w.wallet_address 
                 AND wbh.token_address = t.token_address
                 AND wbh.timestamp = (SELECT max_ts FROM latest_timestamp)
                ),
                0
            ) as value
        FROM wallets w
        CROSS JOIN tokens t
    """)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

if __name__ == "__main__":
    initialize_db()

