from flask import Flask, jsonify
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "Bot is running!",
        "message": "Discord DM Broadcast Bot is active",
        "endpoints": {
            "/health": "Health check endpoint",
            "/status": "Bot status information"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "discord-dm-bot"
    })

@app.route('/status')
def status():
    return jsonify({
        "bot_status": "active",
        "service": "Discord DM Broadcast Bot",
        "version": "1.0.0"
    })

def run():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

if __name__ == '__main__':
    run()
