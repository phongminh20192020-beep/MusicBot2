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

# Store autoplay state per guild
autoplay_state = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print('Lavalink Status: Connected' if bot.node else 'Lavalink Status: Connecting...')
    print('------')

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Lavalink node "{node.identifier}" is ready!')

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEvent):
    """Handle track end - trigger autoplay"""
    player: wavelink.Player = payload.player
    
    if not player:
        return
    
    # Check if autoplay is enabled for this guild
    if autoplay_state.get(player.guild.id, False):
        # Queue has songs, play the next one
        if player.queue:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            # No more songs in queue, get a recommendation from the last played track
            if player.current:
                try:
                    recommendations = await get_spotify_recommendations(player.current)
                    if recommendations:
                        for track in recommendations[:5]:  # Add 5 recommendations
                            await player.queue.put_wait(track)
                        if not player.playing:
                            next_track = player.queue.get()
                            await player.play(next_track)
                except Exception as e:
                    print(f"Error getting recommendations: {e}")

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
    
    # Setup Spotify support - REQUIRED for this bot
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_client = spotify.SpotifyClient(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
        )
        wavelink.Pool.set_spotify_client(spotify_client)
        print("✅ Spotify support enabled!")
    else:
        print("⚠️ WARNING: Spotify credentials not found! Some features may not work.")

async def get_spotify_recommendations(track: wavelink.Playable):
    """Get Spotify recommendations based on current track"""
    try:
        # Get Spotify client
        spotify_client = wavelink.Pool._spotify_client
        if not spotify_client:
            return None
        
        # Search for track on Spotify to get its URI
        search_results = await spotify_client.search(f"{track.title} {track.author}", types=[spotify.SpotifySearchType.track])
        
        if not search_results or not search_results.tracks:
            return None
        
        track_uri = search_results.tracks[0].uri
        
        # Get recommendations
        recommendations = await spotify_client.get_recommendations(seed_tracks=[track_uri], limit=5)
        
        # Convert recommendations to wavelink tracks
        tracks = []
        for rec in recommendations.tracks:
            # Search for the recommendation on Spotify
            search = await spotify_client.search(f"{rec.name} {rec.artists[0].name}", types=[spotify.SpotifySearchType.track])
            if search.tracks:
                tracks.append(search.tracks[0])
        
        return tracks
    except Exception as e:
        print(f"Error in get_spotify_recommendations: {e}")
        return None

@bot.command(name='play')
async def play(ctx, *, query: str = None):
    """Play a song from Spotify"""
    
    if not query:
        await ctx.send("Please provide a song name or Spotify URL!\nUsage: `!play <song name>`")
        return
    
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel to use this command!")
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except discord.ClientException as e:
            await ctx.send(f"❌ Failed to connect to voice channel: {e}")
            return
    
    # Search for the track on Spotify
    try:
        tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.Spotify)
        
        if not tracks:
            await ctx.send(f"❌ No tracks found on Spotify matching: **{query}**")
            return
        
        track = tracks[0]
        await player.queue.put_wait(track)
        
        # Start playing if not already playing
        if not player.playing:
            await player.play(player.queue.get())
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{track.title}** by {track.author}",
                color=discord.Color.green()
            )
            embed.add_field(name="Duration", value=f"{track.length // 60000}:{(track.length % 60000) // 1000:02d}", inline=True)
            embed.add_field(name="Autoplay", value="✅ ON" if autoplay_state.get(ctx.guild.id, False) else "❌ OFF", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="➕ Added to Queue",
                description=f"**{track.title}** by {track.author}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Queue Position", value=len(player.queue), inline=False)
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error searching Spotify: {e}")

@bot.command(name='stop')
async def stop(ctx):
    """Stop the current song and disconnect"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    await player.stop()
    await player.disconnect()
    
    # Reset autoplay state
    autoplay_state[ctx.guild.id] = False
    
    await ctx.send("⏹️ Stopped music and disconnected.")

@bot.command(name='pause')
async def pause(ctx):
    """Pause the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    if not player.playing:
        await ctx.send("❌ No song is currently playing!")
        return
    
    await player.pause()
    await ctx.send("⏸️ Music paused.")

@bot.command(name='resume')
async def resume(ctx):
    """Resume the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    if player.playing:
        await ctx.send("❌ Music is already playing!")
        return
    
    await player.resume()
    await ctx.send("▶️ Music resumed.")

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    if not player.playing:
        await ctx.send("❌ No song is currently playing!")
        return
    
    current = player.current
    await player.skip()
    
    if player.queue:
        next_track = player.current
        embed = discord.Embed(
            title="⏭️ Skipped",
            description=f"Skipped: **{current.title}**\n\nNow playing: **{next_track.title}**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"⏭️ Skipped: **{current.title}**")

@bot.command(name='queue')
async def queue(ctx):
    """Show the current queue"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    if not player.queue and not player.playing:
        await ctx.send("❌ The queue is empty!")
        return
    
    queue_list = ""
    if player.playing:
        queue_list += f"**Currently Playing:**\n▶️ {player.current.title} by {player.current.author}\n\n"
    
    if player.queue:
        queue_list += "**Queue:**\n"
        for i, track in enumerate(list(player.queue)[:10], 1):
            queue_list += f"{i}. **{track.title}** by {track.author}\n"
        
        if len(player.queue) > 10:
            queue_list += f"\n... and {len(player.queue) - 10} more songs"
    
    embed = discord.Embed(
        title="🎵 Queue",
        description=queue_list,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Total in queue: {len(player.queue)} | Autoplay: {'✅ ON' if autoplay_state.get(ctx.guild.id, False) else '❌ OFF'}")
    await ctx.send(embed=embed)

@bot.command(name='autoplay')
async def autoplay(ctx):
    """Toggle autoplay mode (automatically plays similar songs)"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player:
        await ctx.send("❌ I'm not connected to a voice channel!")
        return
    
    current_state = autoplay_state.get(ctx.guild.id, False)
    new_state = not current_state
    autoplay_state[ctx.guild.id] = new_state
    
    if new_state:
        embed = discord.Embed(
            title="✅ Autoplay Enabled",
            description="I'll automatically play similar songs when the queue is empty!",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="❌ Autoplay Disabled",
            description="Autoplay has been turned off.",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

@bot.command(name='nowplaying')
async def nowplaying(ctx):
    """Show what's currently playing"""
    
    player: wavelink.Player = ctx.voice_client
    
    if not player or not player.playing:
        await ctx.send("❌ Nothing is currently playing!")
        return
    
    track = player.current
    position = player.position / 1000  # Convert to seconds
    duration = track.length / 1000
    
    # Create progress bar
    progress = int((position / duration) * 20)
    progress_bar = "▰" * progress + "▱" * (20 - progress)
    
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{track.title}**\nby {track.author}",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Progress",
        value=f"{progress_bar}\n{int(position)}:{int(position % 60):02d} / {int(duration)}:{int(duration % 60):02d}",
        inline=False
    )
    embed.add_field(name="Autoplay", value="✅ ON" if autoplay_state.get(ctx.guild.id, False) else "❌ OFF", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    """Check bot response time"""
    await ctx.send(f'🏓 Pong! {round(bot.latency * 1000)}ms')

# Run the bot
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_TOKEN not found in .env file!')
        print('Please add your Discord bot token to .env file')
        exit(1)
    
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print('⚠️ WARNING: Spotify credentials not found!')
        print('Please add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to your .env file')
    
    bot.loop.create_task(connect_nodes())
    bot.run(DISCORD_TOKEN)
