from flask import Flask, jsonify
import threading
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store bot instance globally
bot_instance = None
start_time = datetime.now()

def set_bot_instance(bot):
    """Set the bot instance for web server to use"""
    global bot_instance
    bot_instance = bot

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'uptime': str(datetime.now() - start_time),
        'bot_ready': bot_instance.is_ready() if bot_instance else False
    }), 200

@app.route('/health')
def health():
    """Health check for monitoring"""
    if not bot_instance:
        return jsonify({'status': 'bot_not_ready'}), 503
    
    return jsonify({
        'status': 'healthy',
        'bot_latency': round(bot_instance.latency * 1000),
        'guilds': len(bot_instance.guilds),
        'users': sum(g.member_count for g in bot_instance.guilds if g.member_count),
    }), 200

@app.route('/stats')
def stats():
    """Get bot statistics"""
    if not bot_instance:
        return jsonify({'error': 'Bot not ready'}), 503
    
    total_members = sum(g.member_count for g in bot_instance.guilds if g.member_count)
    
    return jsonify({
        'guilds': len(bot_instance.guilds),
        'users': total_members,
        'uptime': str(datetime.now() - start_time),
        'latency': round(bot_instance.latency * 1000),
        'status': 'online'
    }), 200

@app.route('/nodes')
def nodes_status():
    """Get Lavalink nodes status"""
    if not bot_instance:
        return jsonify({'error': 'Bot not ready'}), 503
    
    import wavelink
    
    nodes_info = []
    for node in wavelink.Pool.nodes:
        nodes_info.append({
            'name': node.identifier,
            'connected': node.is_available(),
            'region': node.region,
            'players': len(node.players) if hasattr(node, 'players') else 0,
        })
    
    return jsonify({
        'nodes': nodes_info,
        'total_players': sum(ni['players'] for ni in nodes_info)
    }), 200

def run_web_server(port=5000, host='0.0.0.0'):
    """Run Flask web server in a separate thread"""
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

def start_web_server(port=5000, host='0.0.0.0'):
    """Start web server in background thread"""
    web_thread = threading.Thread(target=run_web_server, args=(port, host), daemon=True)
    web_thread.start()
    logger.info(f"✅ Web server started in background on {host}:{port}")
