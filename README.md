# 🎵 MusicBot2 - Production-Grade Discord Music Bot

A powerful, Rythm-like Discord music bot with multiple Lavalink nodes, autoplay, web dashboard, and production-ready features.

## 🌟 Features

- **Slash Commands** - Modern Discord slash commands interface
- **Multi-Node Lavalink** - 3 redundant Lavalink nodes with automatic failover
- **Auto-Retry** - 5x automatic retry on node connection failure
- **Auto-Debug & Auto-Fix** - Handles common errors automatically
- **Spotify Integration** - Play directly from Spotify with recommendations
- **Autoplay** - Automatically plays similar songs when queue is empty
- **Web Dashboard** - 24/7 web server with monitoring endpoints
- **Health Checks** - Real-time bot and node status monitoring
- **Emoji Feedback** - Beautiful emoji-based command responses
- **Channel Status Tracking** - Monitors bot presence in voice channels
- **Queue Management** - Full queue control and visualization
- **Error Handling** - Comprehensive error messages and logging

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/play <query>` | Play a song from Spotify |
| `/pause` | Pause current playback |
| `/resume` | Resume playback |
| `/skip` | Skip to next track |
| `/stop` | Stop playback and clear queue |
| `/join` | Join your voice channel |
| `/disconnect` or `/dc` | Leave voice channel |
| `/queue` | View current queue |
| `/autoplay` | Toggle autoplay mode |
| `/nowplaying` | Show current track with progress |

## ⚙️ Setup Guide

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Lavalink server(s) running
- Spotify API credentials (optional)

### Local Setup

1. **Clone repository:**
```bash
git clone https://github.com/phongminh20192020-beep/MusicBot2.git
cd MusicBot2
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create `.env` file:**
```bash
cp .env.example .env
```

4. **Configure `.env`:**
```env
DISCORD_TOKEN=your_bot_token_here
LAVALINK_HOST_1=localhost
LAVALINK_PORT_1=2333
LAVALINK_PASSWORD_1=youshallnotpass
SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
```

5. **Run the bot:**
```bash
python main.py
```

## 🚀 Railway Deployment

### Step 1: Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Add Bot user
4. Copy token to `.env`
5. Enable these Intents:
   - Message Content Intent
   - Guild Members Intent
   - Voice States Intent

### Step 2: Setup Lavalink Nodes

**Option A: Use Public Nodes** (Easiest)
- Find nodes at [lavalink.dev](https://lavalink.dev/)
- Add their details to Railway environment variables

**Option B: Self-Host Nodes on Railway**
1. Create 3 new Railway services with Lavalink Docker image
2. Get their Railway URLs
3. Configure in bot environment variables

### Step 3: Railway Configuration

1. Go to [Railway.app](https://railway.app)
2. Create new project from GitHub
3. Connect your repository
4. Add environment variables:

```
DISCORD_TOKEN=your_token_here
LAVALINK_HOST_1=node1.railway.app
LAVALINK_PORT_1=2333
LAVALINK_PASSWORD_1=youshallnotpass
LAVALINK_HOST_2=node2.railway.app
LAVALINK_PORT_2=2333
LAVALINK_PASSWORD_2=youshallnotpass
LAVALINK_HOST_3=node3.railway.app
LAVALINK_PORT_3=2333
LAVALINK_PASSWORD_3=youshallnotpass
SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
WEB_PORT=5000
MAX_RETRY=5
RETRY_DELAY=5
```

5. Railway automatically detects Dockerfile and deploys!

## 📊 Web Dashboard Endpoints

The bot runs a Flask web server for monitoring:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /health` | Bot status with latency |
| `GET /stats` | Bot statistics (guilds, users, uptime) |
| `GET /nodes` | Lavalink nodes status |

### Example Usage:
```bash
curl http://your-bot-url:5000/stats
```

Response:
```json
{
  "guilds": 5,
  "users": 250,
  "uptime": "2:30:45.123456",
  "latency": 45,
  "status": "online"
}
```

## 🔧 Setup Spotify (Optional)

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create new application
3. Accept terms and create
4. Copy Client ID and Client Secret
5. Go to Edit Settings → Add Redirect URI: `http://localhost:8888/callback`
6. Add to `.env`:
```env
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
```

## 🛡️ Error Handling

The bot automatically handles:
- ❌ **Invalid Guild ID** - Auto-detects and recovers
- ❌ **Node Connection Failed** - Retries up to 5 times
- ❌ **No Available Nodes** - Waits and retries connection
- ❌ **Playback Failed** - Attempts to skip and play next
- ❌ **Voice Channel Error** - Auto-reconnect logic
- ❌ **Spotify Search Fail** - Falls back gracefully

## 📈 Performance

- **Multi-Node Failover** - If Node 1 fails, automatically uses Node 2 or 3
- **Health Monitoring** - Checks node status every 5 minutes
- **Memory Efficient** - Uses wavelink caching for better performance
- **Scalable** - Supports unlimited guilds (performance depends on Lavalink resources)

## 📝 Logs

The bot logs all activities to console:
```
✅ Bot connected as MusicBot2#1234
✅ Synced 10 command(s)
✅ Connected to Node-1 at node1.railway.app:2333
✅ Lavalink node "Node-1" is ready!
✅ Spotify support enabled!
✅ Web server started in background on 0.0.0.0:5000
```

## 🐛 Troubleshooting

### Bot not responding
- Check if DISCORD_TOKEN is correct
- Verify bot has permissions in your server
- Run `/help` to sync commands

### No sound in voice channel
- Verify Lavalink nodes are running
- Check node credentials in `.env`
- View `/nodes` endpoint to check node status

### Spotify not working
- Ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set
- Add bot to Spotify application allowed redirect URIs
- Check client credentials are valid

### "Can't find any nodes to connect"
- Ensure at least one Lavalink node is accessible
- Check firewall/port settings
- Verify node host and port in `.env`

### Node connection keeps failing
- Increase MAX_RETRY value
- Increase RETRY_DELAY (in seconds)
- Check node logs for errors

## 🔌 Node Retry Logic

The bot has built-in retry mechanism:
- **Max Retries**: 5 (configurable via MAX_RETRY)
- **Retry Delay**: 5 seconds (configurable via RETRY_DELAY)
- **Behavior**: Retries each node until all are attempted
- **Fallback**: Uses any available node for playing

## 🎯 Future Features

- [ ] Playlist support
- [ ] Volume control
- [ ] Lyrics display
- [ ] Music search with pagination
- [ ] Admin dashboard
- [ ] Song recommendations
- [ ] DJ mode
- [ ] Audio effects

## 📄 License

MIT License - Feel free to use and modify!

## 🤝 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs using `/nodes` endpoint

## 🎉 Credits

Built with:
- [discord.py](https://github.com/Rapptz/discord.py)
- [Wavelink](https://github.com/PythonistaGuild/Wavelink)
- [Lavalink](https://github.com/lavalink-devs/Lavalink)
- [Flask](https://flask.palletsprojects.com/)

---

**Ready to rock? Add this bot to your server and start playing! 🎵**
