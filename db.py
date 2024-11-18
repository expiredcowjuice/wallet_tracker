import os

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

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
            alias VARCHAR(128)
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

def add_wallet(wallet_address, alias=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wallets (wallet_address, alias)
        VALUES (%s, %s)
        ON CONFLICT (wallet_address) DO NOTHING;
    """, (wallet_address, alias))
    conn.commit()
    cursor.close()
    conn.close()

def add_token(token_address, name=None, symbol=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tokens (token_address, name, symbol)
        VALUES (%s, %s, %s)
        ON CONFLICT (token_address) DO NOTHING;
    """, (token_address, name, symbol))
    conn.commit()
    cursor.close()
    conn.close()

def add_wallet_balance(wallet_address, token_address, balance, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wallet_balance_history (wallet_address, token_address, balance, value)
        VALUES (%s, %s, %s, %s)
    """, (wallet_address, token_address, balance, value))
    conn.commit()

def get_all_wallets():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM wallets;")
    wallets = cursor.fetchall()
    cursor.close()
    conn.close()
    return wallets

def get_all_tokens():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM tokens;")
    tokens = cursor.fetchall()
    cursor.close()
    conn.close()
    return tokens

def get_previous_wallet_balance():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT 
            w.wallet_address,
            t.token_address,
            COALESCE(
                (SELECT balance
                 FROM wallet_balance_history wbh
                 WHERE wbh.wallet_address = w.wallet_address 
                 AND wbh.token_address = t.token_address
                 ORDER BY timestamp DESC 
                 LIMIT 1),
                0
            ) as balance,
            COALESCE(
                (SELECT value
                 FROM wallet_balance_history wbh
                 WHERE wbh.wallet_address = w.wallet_address 
                 AND wbh.token_address = t.token_address
                 ORDER BY timestamp DESC 
                 LIMIT 1),
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