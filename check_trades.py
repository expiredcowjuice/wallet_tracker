import os
import asyncio
import aiohttp

from dotenv import load_dotenv
from discord import Webhook

from wallet_tracker import initialize, check_trades
from utils import create_wallet_trade_embed, logger

load_dotenv()
DISCORD_WEBHOOK_TRADES_URL = os.environ['DISCORD_WEBHOOK_TRADES_URL']

async def run_check_trades():
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(DISCORD_WEBHOOK_TRADES_URL, session=session)
        
        async def log_status(message: str):
            logger.info(message)        

        logger.info('Initializing trades tracker...')
        await initialize()

        logger.info('Checking trades...')
        trades = await check_trades(status_callback=log_status)
        
        if len(trades) == 0:
            logger.info('No trades to send')
            return
        
        logger.info(f'Sending {len(trades)} trades...')
        
        embed = create_wallet_trade_embed(trades)
        await webhook.send(embed=embed)
    
        
if __name__ == '__main__':
    asyncio.run(run_check_trades())
