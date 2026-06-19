import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import wavelink
from wavelink.ext import spotify
import asyncio
import logging
from config import (
    DISCORD_TOKEN, LAVALINK_NODES, SPOTIFY_CLIENT_ID, 
    SPOTIFY_CLIENT_SECRET, MAX_RETRY, RETRY_DELAY, EMOJIS,
    WEB_PORT, WEB_HOST
)
from web_server import start_web_server, set_bot_instance

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Store autoplay state and channel status per guild
autoplay_state = {}
channel_status = {}
node_retry_count = {}

@bot.event
async def on_ready():
    print(f'{EMOJIS["success"]} Bot connected as {bot.user}')
    print(f'{EMOJIS["music"]} Syncing commands...')
    try:
        synced = await bot.tree.sync()
        print(f'{EMOJIS["success"]} Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'{EMOJIS["error"]} Failed to sync commands: {e}')
    
    check_nodes.start()
    print(f'{EMOJIS["success"]} Bot is ready!')

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'{EMOJIS["success"]} Lavalink node "{node.identifier}" is ready!')
    node_retry_count[node.identifier] = 0

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEvent):
    """Handle track end - trigger autoplay"""
    player: wavelink.Player = payload.player
    
    if not player:
        return
    
    # Check if autoplay is enabled
    if autoplay_state.get(player.guild.id, False):
        if player.queue:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            # Queue empty, try to get recommendations
            try:
                if player.current:
                    recommendations = await get_spotify_recommendations(player.current)
                    if recommendations:
                        for track in recommendations[:5]:
                            await player.queue.put_wait(track)
                        if not player.playing:
                            next_track = player.queue.get()
                            await player.play(next_track)
            except Exception as e:
                logger.error(f"Error in autoplay: {e}")

async def connect_nodes():
    """Connect to Lavalink nodes with retry logic"""
    await bot.wait_until_ready()
    
    for node_config in LAVALINK_NODES:
        retry_count = 0
        while retry_count < MAX_RETRY:
            try:
                node = wavelink.Node(
                    uri=f"http://{node_config['host']}:{node_config['port']}",
                    password=node_config['password'],
                    identifier=node_config['name'],
                    region=node_config['region'],
                )
                
                await wavelink.Pool.connect(nodes=[node], client=bot, cache_enabled=True)
                print(f"{EMOJIS['success']} Connected to {node_config['name']} at {node_config['host']}:{node_config['port']}")
                node_retry_count[node_config['name']] = 0
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Failed to connect to {node_config['name']} (Attempt {retry_count}/{MAX_RETRY}): {e}")
                if retry_count < MAX_RETRY:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to connect to {node_config['name']} after {MAX_RETRY} attempts")
    
    # Setup Spotify if credentials provided
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        try:
            spotify_client = spotify.SpotifyClient(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
            )
            wavelink.Pool.set_spotify_client(spotify_client)
            print(f"{EMOJIS['success']} Spotify support enabled!")
        except Exception as e:
            logger.error(f"Failed to setup Spotify: {e}")

@tasks.loop(minutes=5)
async def check_nodes():
    """Check node health and reconnect if needed"""
    for node in wavelink.Pool.nodes:
        if not node.is_available():
            logger.warning(f"Node {node.identifier} is unavailable, attempting reconnect...")
            try:
                await asyncio.sleep(RETRY_DELAY)
                # Node will auto-reconnect through wavelink
            except Exception as e:
                logger.error(f"Error checking node {node.identifier}: {e}")

async def get_spotify_recommendations(track: wavelink.Playable):
    """Get Spotify recommendations"""
    try:
        spotify_client = wavelink.Pool._spotify_client
        if not spotify_client:
            return None
        
        search_results = await spotify_client.search(
            f"{track.title} {track.author}",
            types=[spotify.SpotifySearchType.track]
        )
        
        if not search_results or not search_results.tracks:
            return None
        
        track_uri = search_results.tracks[0].uri
        recommendations = await spotify_client.get_recommendations(seed_tracks=[track_uri], limit=5)
        
        tracks = []
        for rec in recommendations.tracks:
            search = await spotify_client.search(
                f"{rec.name} {rec.artists[0].name}",
                types=[spotify.SpotifySearchType.track]
            )
            if search.tracks:
                tracks.append(search.tracks[0])
        
        return tracks
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return None

async def get_available_node():
    """Get an available Lavalink node"""
    available_nodes = [n for n in wavelink.Pool.nodes if n.is_available()]
    if not available_nodes:
        return None
    return available_nodes[0]

@bot.tree.command(name="play", description="Play a song")
@app_commands.describe(query="Song name or Spotify URL")
async def play(interaction: discord.Interaction, query: str):
    """Play a song from Spotify"""
    await interaction.response.defer()
    
    if not interaction.user.voice:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} You must be in a voice channel!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check node availability
    node = await get_available_node()
    if not node:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} No Lavalink nodes available! Retrying...",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        try:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        except Exception as e:
            embed = discord.Embed(
                description=f"{EMOJIS['error']} Failed to connect: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
    
    try:
        tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.Spotify)
        
        if not tracks:
            embed = discord.Embed(
                description=f"{EMOJIS['error']} No tracks found for: **{query}**",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        track = tracks[0]
        await player.queue.put_wait(track)
        
        if not player.playing:
            await player.play(player.queue.get())
            embed = discord.Embed(
                title=f"{EMOJIS['play']} Now Playing",
                description=f"**{track.title}** by {track.author}",
                color=discord.Color.green()
            )
            embed.add_field(name="Duration", value=f"{track.length // 60000}:{(track.length % 60000) // 1000:02d}", inline=True)
            embed.add_field(name="Autoplay", value=f"{'✅ ON' if autoplay_state.get(interaction.guild.id, False) else '❌ OFF'}", inline=True)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{EMOJIS['music']} Added to Queue",
                description=f"**{track.title}** by {track.author}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Position", value=f"#{len(player.queue)}", inline=False)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Error searching for track: {e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    """Pause playback"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    if not player.playing:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Nothing is playing!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    await player.pause()
    embed = discord.Embed(
        description=f"{EMOJIS['pause']} Music paused",
        color=discord.Color.orange()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="resume", description="Resume the current song")
async def resume(interaction: discord.Interaction):
    """Resume playback"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    if player.playing:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Already playing!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    await player.resume()
    embed = discord.Embed(
        description=f"{EMOJIS['play']} Music resumed",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="skip", description="Skip to the next song")
async def skip(interaction: discord.Interaction):
    """Skip current track"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    if not player.playing:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Nothing is playing!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    current = player.current
    await player.skip()
    
    embed = discord.Embed(
        title=f"{EMOJIS['skip']} Skipped",
        description=f"Skipped: **{current.title}**",
        color=discord.Color.orange()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="stop", description="Stop playing and clear queue")
async def stop(interaction: discord.Interaction):
    """Stop playback and clear queue"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    await player.stop()
    player.queue.clear()
    autoplay_state[interaction.guild.id] = False
    
    embed = discord.Embed(
        description=f"{EMOJIS['stop']} Music stopped and queue cleared",
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="disconnect", description="Disconnect from voice channel")
async def disconnect(interaction: discord.Interaction):
    """Disconnect from voice"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    await player.disconnect()
    autoplay_state[interaction.guild.id] = False
    channel_status.pop(interaction.guild.id, None)
    
    embed = discord.Embed(
        description=f"{EMOJIS['disconnect']} Disconnected from voice channel",
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    """Join voice channel"""
    await interaction.response.defer()
    
    if not interaction.user.voice:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} You must be in a voice channel!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if player:
        embed = discord.Embed(
            description=f"{EMOJIS['warning']} Already connected to a voice channel!",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed)
        return
    
    try:
        await interaction.user.voice.channel.connect(cls=wavelink.Player)
        channel_status[interaction.guild.id] = interaction.user.voice.channel.id
        
        embed = discord.Embed(
            description=f"{EMOJIS['connect']} Connected to **{interaction.user.voice.channel.name}**",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Failed to connect: {e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="dc", description="Disconnect from voice channel (alias)")
async def dc(interaction: discord.Interaction):
    """Alias for disconnect"""
    await disconnect(interaction)

@bot.tree.command(name="queue", description="View the current queue")
async def queue_cmd(interaction: discord.Interaction):
    """Show queue"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    if not player.queue and not player.playing:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Queue is empty!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    queue_text = ""
    if player.playing:
        queue_text += f"**Now Playing:**\n{EMOJIS['play']} {player.current.title} by {player.current.author}\n\n"
    
    if player.queue:
        queue_text += "**Queue:**\n"
        for i, track in enumerate(list(player.queue)[:10], 1):
            queue_text += f"{i}. {track.title} by {track.author}\n"
        
        if len(player.queue) > 10:
            queue_text += f"\n... and {len(player.queue) - 10} more songs"
    
    embed = discord.Embed(
        title=f"{EMOJIS['queue']} Queue",
        description=queue_text,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Total in queue: {len(player.queue)} | Autoplay: {'✅ ON' if autoplay_state.get(interaction.guild.id, False) else '❌ OFF'}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="autoplay", description="Toggle autoplay mode")
async def autoplay(interaction: discord.Interaction):
    """Toggle autoplay"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Bot not connected!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    current_state = autoplay_state.get(interaction.guild.id, False)
    new_state = not current_state
    autoplay_state[interaction.guild.id] = new_state
    
    if new_state:
        embed = discord.Embed(
            description=f"{EMOJIS['success']} Autoplay **enabled** ✅",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Autoplay **disabled** ❌",
            color=discord.Color.red()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="nowplaying", description="Show currently playing song")
async def nowplaying(interaction: discord.Interaction):
    """Show now playing"""
    await interaction.response.defer()
    
    player: wavelink.Player = interaction.guild.voice_client
    
    if not player or not player.playing:
        embed = discord.Embed(
            description=f"{EMOJIS['error']} Nothing is playing!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    track = player.current
    position = player.position / 1000
    duration = track.length / 1000
    
    progress = int((position / duration) * 20)
    progress_bar = "▰" * progress + "▱" * (20 - progress)
    
    embed = discord.Embed(
        title=f"{EMOJIS['music']} Now Playing",
        description=f"**{track.title}**\nby {track.author}",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Progress",
        value=f"{progress_bar}\n{int(position)}:{int(position % 60):02d} / {int(duration)}:{int(duration % 60):02d}",
        inline=False
    )
    embed.add_field(name="Autoplay", value=f"{'✅ ON' if autoplay_state.get(interaction.guild.id, False) else '❌ OFF'}", inline=True)
    
    await interaction.followup.send(embed=embed)

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print(f"{EMOJIS['error']} ERROR: DISCORD_TOKEN not found!")
        exit(1)
    
    # Start web server
    start_web_server(WEB_PORT, WEB_HOST)
    set_bot_instance(bot)
    
    # Connect to Lavalink
    bot.loop.create_task(connect_nodes())
    
    # Run bot
    bot.run(DISCORD_TOKEN)
