import os
import discord
from discord.ext import commands

from solana_tracker import check_wallet_balances

DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.default()
intents.message_content = True  # May not be necessary for slash commands

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree  # This is the command tree for slash commands

@tree.command(name="check_wallet_balances", description="Check wallet balances and report changes.")
async def check_wallet_balances_command(interaction: discord.Interaction):
    # Run the balance checking function
    response = await check_wallet_balances()
    # Send the response
    await interaction.response.send_message(response)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await tree.sync()  # Sync commands with Discord
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(DISCORD_BOT_TOKEN)