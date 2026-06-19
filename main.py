import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get token from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX', '!')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print('------')

@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command to test the bot"""
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command(name='play')
async def play(ctx, *, song):
    """Play a song from YouTube or Spotify"""
    await ctx.send(f'Now playing: {song} (feature coming soon)')

@bot.command(name='stop')
async def stop(ctx):
    """Stop the current song"""
    await ctx.send('Music stopped')

# Run the bot
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_TOKEN not found in .env file!')
        print('Please add your Discord bot token to .env file')
        exit(1)
    
    bot.run(DISCORD_TOKEN)