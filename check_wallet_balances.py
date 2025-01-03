import os
import asyncio
import aiohttp

from dotenv import load_dotenv
from discord import Webhook

from wallet_tracker import initialize, check_wallet_balances
from utils import create_wallet_balance_change_embed, create_token_flow_summary_embed, logger

load_dotenv()
DISCORD_WEBHOOK_WALLET_TRACKER_URL = os.environ['DISCORD_WEBHOOK_WALLET_TRACKER_URL']

async def run_check_wallet_balances():
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(DISCORD_WEBHOOK_WALLET_TRACKER_URL, session=session)
        
        async def log_status(message: str):
            logger.info(message)        

        logger.info('Initializing wallet tracker...')
        await initialize()

        logger.info('Checking wallet balances...')
        changes, previous_check_time = await check_wallet_balances(status_callback=log_status)
        
        if len(changes) == 0:
            await webhook.send(content='No significant balance changes')
            logger.info('No changes to send')
            return
        
        logger.info(f'Sending {len(changes)} wallet balance changes...')
        
        CHANGES_PER_EMBED = 20
        batches = [changes[i:i + CHANGES_PER_EMBED] 
                    for i in range(0, len(changes), CHANGES_PER_EMBED)]
        
        for page, batch in enumerate(batches, 1):
            embed = create_wallet_balance_change_embed(batch, previous_check_time if page == 1 else None, page, len(batches))
            await webhook.send(embed=embed)
        
        summary_embed = create_token_flow_summary_embed(changes)
        await webhook.send(embed=summary_embed)
        

if __name__ == '__main__':
    asyncio.run(run_check_wallet_balances())
