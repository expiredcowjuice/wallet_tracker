import os
import re
import datetime

import asyncio
import discord
from discord.app_commands import describe, AppCommandError
from discord.ext import commands
from functools import wraps

from wallet_tracker import (
    check_wallet_balances, 
    list_wallets, 
    list_tokens, 
    add_wallets, 
    add_tokens,
    initialize,
)
from utils import (
    create_embed,
    create_summary_embed,
)
from multiLineModal import MultiLineModal

DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.default()
intents.message_content = True  # May not be necessary for slash commands

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree  # This is the command tree for slash commands

########################
# Helper Functions
########################
def is_valid_solana_address(address: str) -> bool:
    """
    Validate Solana address format
    """
    # Basic Solana address validation
    # - Must be between 32-44 characters
    # - Must only contain base58 characters (alphanumeric without 0, O, I, l)
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    return bool(re.match(base58_pattern, address))

def parse_code_block(content: str) -> list:
    """
    Parse a code block containing tab-separated data
    """
    # Remove code block markers if present
    content = content.strip('`').strip()
    if content.startswith('```') and content.endswith('```'):
        content = content[3:-3].strip()
    
    # Split into lines and parse
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    result = []
    
    for line in lines:
        # Split by tab while preserving spaces within each column
        parts = tuple(part.strip() for part in line.split('\t'))

        # If only one part, result will be a list of single elements
        if len(parts) == 1:
            result.append(parts[0])
        elif parts:  # Only add non-empty lines
            result.append(parts)
    
    return result


########################
# Decorators
########################
def refresh_state():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            try:
                # Defer first
                await interaction.response.defer()
                # Then refresh state
                await initialize()
                return await func(interaction, *args, **kwargs)
            except Exception as e:
                print(f"Error in refresh_state: {str(e)}")
                try:
                    await interaction.followup.send(f"An error occurred: {str(e)}")
                except:
                    print(f"Failed to send error message")
                raise
        return wrapper
    return decorator


def validate_addresses():
    """
    Decorator to validate addresses before executing command
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction, *args, **kwargs):
            # Check for wallet_address in kwargs
            if 'address' in kwargs:
                address = kwargs['address']
                if not is_valid_solana_address(address):
                    raise AppCommandError(
                        'Invalid Solana address format. Please check the address and try again.'
                    )
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

########################
# Commands
########################
@tree.command(name="check_wallet_balances", description="Check all wallet balances")
@refresh_state()
async def check_wallet_balances_command(interaction: discord.Interaction):
    status_message = await interaction.followup.send('Starting wallet balance check...', wait=True)
    
    async def update_status(message: str):
        await status_message.edit(content=message)
    
    changes, previous_check_time = await check_wallet_balances(status_callback=update_status)
    if len(changes) == 0:
        await status_message.edit(content="No significant balance changes")
        return

    CHANGES_PER_EMBED = 20
    batches = [changes[i:i + CHANGES_PER_EMBED] 
              for i in range(0, len(changes), CHANGES_PER_EMBED)]
    total_pages = len(batches)

    # Send first embed by editing the status message
    first_embed = create_embed(batches[0], previous_check_time, 1, total_pages)
    await status_message.edit(content=None, embed=first_embed)
    
    # Send additional embeds as new messages
    for page, batch in enumerate(batches[1:], 2):
        embed = create_embed(batch, None, page, total_pages)
        await interaction.followup.send(embed=embed)
    
    # Send summary embed as the final message
    summary_embed = create_summary_embed(changes)
    await interaction.followup.send(embed=summary_embed)

@tree.command(name="list_wallets", description="List all wallets")
@refresh_state()
async def list_wallets_command(interaction: discord.Interaction):
    wallets = await list_wallets()
    
    # Create embed
    embed = discord.Embed(
        title='🏦 Tracked Wallets',
        description='List of all tracked wallet addresses',
        color=discord.Color.blue()
    )
    
    for idx, wallet in enumerate(wallets):
        address = wallet['wallet_address']
        alias = wallet['alias']
        
        solscan_link = f'https://solscan.io/account/{address}'
        
        # Add field for each wallet
        embed.add_field(
            name=f'{idx+1}. {alias}',
            value=f'[{address[:4]}...{address[-4:]}]({solscan_link})',
            inline=False
        )
    
    # Add footer with timestamp
    embed.set_footer(text='Last updated')
    embed.timestamp = datetime.datetime.now()
    
    await interaction.followup.send(embed=embed)

@tree.command(name="list_tokens", description="List all tokens")
@refresh_state()
async def list_tokens_command(interaction: discord.Interaction):
    tokens = await list_tokens()
    
    # Create embed
    embed = discord.Embed(
        title='💰 Tracked Tokens',
        description='List of all tracked tokens',
        color=discord.Color.blue()
    )
    
    for idx, token in enumerate(tokens):
        address = token['token_address']
        symbol = token['symbol']
        name = token['name']
        
        solscan_link = f'https://solscan.io/token/{address}'
        
        # Add field for each token
        embed.add_field(
            name=f'{idx+1}. ${symbol} - {name}',
            value=f'[{address[:4]}...{address[-4:]}]({solscan_link})',
            inline=False
        )
    
    # Add footer with timestamp
    embed.set_footer(text='Last updated')
    embed.timestamp = datetime.datetime.now()
    
    await interaction.followup.send(embed=embed)

@tree.command(name="add_wallet", description="Add a wallet")
@refresh_state()
@validate_addresses()
@describe(
    address='The wallet address to track',
    name='A name for this wallet'
)
async def add_wallet_command(interaction: discord.Interaction, address: str, name: str):
    # Run the add wallet function
    response = await add_wallets([(address, name)])
    # Send the response
    await interaction.followup.send(response)

@tree.command(name="add_token", description="Add a token")
@refresh_state()
@validate_addresses()
@describe(
    address='The token address to track',
)
async def add_token_command(interaction: discord.Interaction, address: str):
    # Run the add token function
    response = await add_tokens([address])
    # Send the response
    await interaction.followup.send(response)

@tree.command(name="bulk_add_wallets", description="Bulk add wallets")
@refresh_state()
async def bulk_add_wallets_command(interaction: discord.Interaction):
    future = asyncio.Future()
    await interaction.response.send_modal(MultiLineModal(future=future))
    text = await future

    # Send loading message
    loading_message = await interaction.followup.send('Processing wallets... Please wait.', wait=True)
    
    try:
        # Parse the CSV data
        wallets = parse_code_block(text)
        
        # Add the wallets
        response = await add_wallets(wallets)

        # Edit the loading message with the result
        await loading_message.edit(content=response)
        
    except Exception as e:
        # Edit the loading message with the error
        await loading_message.edit(content=f'Error processing wallets: {str(e)}')

@tree.command(name="bulk_add_tokens", description="Bulk add tokens")
@refresh_state()
async def bulk_add_tokens_command(interaction: discord.Interaction):
    future = asyncio.Future()
    await interaction.response.send_modal(MultiLineModal(future=future))
    text = await future

    # Send loading message
    loading_message = await interaction.followup.send('Processing tokens... Please wait.', wait=True)

    try:
        # Parse the CSV data
        tokens = parse_code_block(text)
        
        # Add the tokens
        response = await add_tokens(tokens)

        # Edit the loading message with the result
        await loading_message.edit(content=response)
        
    except Exception as e:
        # Edit the loading message with the error
        await loading_message.edit(content=f'Error processing tokens: {str(e)}')

########################
# Bot Events
########################
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await tree.sync()  # Sync commands with Discord
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(DISCORD_BOT_TOKEN)