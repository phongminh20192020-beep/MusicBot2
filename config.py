import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX', '/')

# Lavalink Nodes Configuration
LAVALINK_NODES = [
    {
        'host': os.getenv('LAVALINK_HOST_1', 'localhost'),
        'port': int(os.getenv('LAVALINK_PORT_1', '2333')),
        'password': os.getenv('LAVALINK_PASSWORD_1', 'youshallnotpass'),
        'region': 'us',
        'name': 'Node-1'
    },
    {
        'host': os.getenv('LAVALINK_HOST_2', 'localhost'),
        'port': int(os.getenv('LAVALINK_PORT_2', '2334')),
        'password': os.getenv('LAVALINK_PASSWORD_2', 'youshallnotpass'),
        'region': 'eu',
        'name': 'Node-2'
    },
    {
        'host': os.getenv('LAVALINK_HOST_3', 'localhost'),
        'port': int(os.getenv('LAVALINK_PORT_3', '2335')),
        'password': os.getenv('LAVALINK_PASSWORD_3', 'youshallnotpass'),
        'region': 'asia',
        'name': 'Node-3'
    },
]

# Spotify
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Web Server
WEB_PORT = int(os.getenv('WEB_PORT', '5000'))
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')

# Settings
MAX_RETRY = int(os.getenv('MAX_RETRY', '5'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))

# Emojis
EMOJIS = {
    'play': '▶️',
    'pause': '⏸️',
    'stop': '⏹️',
    'skip': '⏭️',
    'queue': '📋',
    'connect': '📡',
    'disconnect': '📴',
    'loading': '⏳',
    'error': '❌',
    'success': '✅',
    'warning': '⚠️',
    'music': '🎵',
    'speaker': '🔊',
    'no_sound': '🔇',
}
