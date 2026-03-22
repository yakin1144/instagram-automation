from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
@app.route('/healthcheck')
def health():
    return "Bot is running", 200

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Start health server in a background thread
if not os.environ.get('RENDER'):
    # Only start if not running locally
    pass
