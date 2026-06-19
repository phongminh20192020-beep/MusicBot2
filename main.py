import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import wavelink
from wavelink.ext import spotify

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX', '!')
LAVALINK_HOST = os.getenv('LAVALINK_HOST', 'localhost')
LAVALINK_PORT = int(os.getenv('LAVALINK_PORT', '2333'))
LAVALINK_PASSWORD = os.getenv('LAVALINK_PASSWORD', 'youshallnotpass')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print('Lavalink Status: Connected' if bot.node else 'Lavalink Status: Connecting...')
    print('------')

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Lavalink node "{node.identifier}" is ready!')

async def connect_nodes():
    """Connect to Lavalink nodes"""
    await bot.wait_until_ready()
    
    node: wavelink.Node = wavelink.Node(
        uri=f'http://{LAVALINK_HOST}:{LAVALINK_PORT}',
        password=LAVALINK_PASSWORD,
        identifier='MAIN',
        region='us',
    )
    
    await wavelink.Pool.connect(nodes=[node], client=bot, cache_enabled=True)
    
    # Optional: Setup Spotify support if credentials provided
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_client = spotify.SpotifyClient(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
        )
        wavelink.Pool.set_spotify_client(spotify_client)
        print("Spotify support enabled!")

@bot.command(name='play')
async def play(ctx, *, query: str):
    """Play a song from YouTube, Spotify, or other sources"""
    
    if not ctx.author.voice:
        await ctx.send("You must be in a voice channel to use this command!")
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except discord.ClientException as e:
            await ctx.send(f"Failed to connect to voice channel: {e}")
            return
    
    # Search for the track
    tracks = await wavelink.Playable.search(query)
    
    if not tracks:
        await ctx.send(f"No tracks found matching: {query}")
        return
    
    track = tracks[0]
    await player.queue.put_wait(track)
    
    # Start playing if not already playing
    if not player.playing:
        await player.play(player.queue.get())
        await ctx.send(f"Now playing: **{track.title}** by {track.author}")
    else:
        await ctx.send(f"Added to queue: **{track.title}** by {track.author}")

@bot.command(name='stop')
async def stop(ctx):
    """Stop the current song and disconnect"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("I'm not connected to a voice channel!")
        return
    
    await player.stop()
    await player.disconnect()
    await ctx.send("Stopped music and disconnected.")

@bot.command(name='pause')
async def pause(ctx):
    """Pause the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("I'm not connected to a voice channel!")
        return
    
    await player.pause()
    await ctx.send("Music paused.")

@bot.command(name='resume')
async def resume(ctx):
    """Resume the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("I'm not connected to a voice channel!")
        return
    
    await player.resume()
    await ctx.send("Music resumed.")

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("I'm not connected to a voice channel!")
        return
    
    if not player.playing:
        await ctx.send("No song is currently playing!")
        return
    
    await player.skip()
    await ctx.send("Skipped to next song.")

@bot.command(name='queue')
async def queue(ctx):
    """Show the current queue"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("I'm not connected to a voice channel!")
        return
    
    if not player.queue:
        await ctx.send("The queue is empty!")
        return
    
    queue_list = "\n".join([f"{i+1}. **{track.title}** by {track.author}" for i, track in enumerate(list(player.queue)[:10])])
    await ctx.send(f"**Queue:**\n{queue_list}")

@bot.command(name='ping')
async def ping(ctx):
    """Check bot response time"""
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

# Run the bot
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_TOKEN not found in .env file!')
        print('Please add your Discord bot token to .env file')
        exit(1)
    
    bot.loop.create_task(connect_nodes())
    bot.run(DISCORD_TOKEN)
