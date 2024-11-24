import os
import asyncio
import discord

from wallet_tracker import check_wallet_balances
from discord_bot import create_embed, create_summary_embed


DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
DISCORD_CHANNEL_ID = int(os.environ['DISCORD_CHANNEL_ID'])

async def run_scheduled_task():
    intents = discord.Intents.default()
    bot = discord.Client(intents=intents)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        try:
            channel = bot.get_channel(DISCORD_CHANNEL_ID)
            
            changes, previous_check_time = await check_wallet_balances()
            if len(changes) == 0:
                return
            
            CHANGES_PER_EMBED = 20
            batches = [changes[i:i + CHANGES_PER_EMBED] 
                      for i in range(0, len(changes), CHANGES_PER_EMBED)]
            total_pages = len(batches)

            first_embed = create_embed(batches[0], previous_check_time, 1, total_pages)
            await channel.send(embed=first_embed)

            for i, batch in enumerate(batches[1:], 2):
                embed = create_embed(batch, previous_check_time, i, total_pages)
                await channel.send(embed=embed)

            summary_embed = create_summary_embed(changes)
            await channel.send(embed=summary_embed)

        finally:
            await bot.close()

    await bot.start(DISCORD_BOT_TOKEN)

# Run the async function
asyncio.run(run_scheduled_task())
