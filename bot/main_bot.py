import asyncio
import threading
import time
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import *
from automation_logic import *
from database import DatabaseUtils, db_manager
import sys

# Configure logging - stdout only (no file writing issues)
handlers = [logging.StreamHandler()]

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL if 'LOG_LEVEL' in dir() else 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Initialize Flask app for API
api_app = Flask(__name__)
CORS(api_app, origins=[WEB_DASHBOARD_URL if 'WEB_DASHBOARD_URL' in dir() else '*'])

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=api_app,
    default_limits=["200 per day", "50 per hour"]
)

class InstagramBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.automation_thread = None
        self.is_running = False
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = """
🤖 **Automated Instagram Account Creator Bot**

**Available Commands:**
/start - Initialize the bot
/start_auto <index> - Start automation from specific index
/stop - Stop current automation process
/status - Check current bot status
/help - Show this help message

**Ready to begin account creation automation!**
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_message = """
📚 **Bot Commands Guide**

**Basic Commands:**
• `/start` - Initialize the bot
• `/help` - Show this help message

**Automation Commands:**
• `/start_auto <index>` - Start automation from specific account index
• `/stop` - Stop current automation process
• `/status` - Check current bot status

**Examples:**
• `/start_auto 0` - Start from first account
• `/start_auto 5` - Start from 6th account
• `/status` - Check current progress

**Note:** The bot will process accounts sequentially and save all data to PostgreSQL.
        """
        await update.message.reply_text(help_message)
    
    async def start_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            state = load_bot_state()
            if state['is_running']:
                await update.message.reply_text("⚠️ Automation is already running! Use /stop to stop it first.")
                return
            
            if context.args and context.args[0].isdigit():
                start_index = int(context.args[0])
            else:
                start_index = 0
            
            accounts = load_gmail_accounts()
            if not accounts:
                await update.message.reply_text("❌ No Gmail accounts found! Please check your configuration.")
                return
            
            if start_index >= len(accounts):
                await update.message.reply_text(f"❌ Starting index {start_index} is out of range. Total accounts: {len(accounts)}")
                return
            
            self.is_running = True
            self.automation_thread = threading.Thread(target=self.run_automation, args=(start_index, update.message.chat_id))
            self.automation_thread.daemon = True
            self.automation_thread.start()
            
            confirmation_message = f"""
🚀 **Automation Started!**

📊 **Configuration Loaded:**
• Starting from index: {start_index}
• Total accounts in queue: {len(accounts)}
• Headless mode: {HEADLESS_MODE if 'HEADLESS_MODE' in dir() else True}

⏳ **Beginning account creation process...**
            """
            await update.message.reply_text(confirmation_message)
            
        except Exception as e:
            logger.error(f"Error starting automation: {e}")
            await update.message.reply_text(f"❌ Error starting automation: {str(e)}")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            state = load_bot_state()
            if not state['is_running']:
                await update.message.reply_text("ℹ️ No automation is currently running.")
                return
            
            state['is_running'] = False
            save_bot_state(state)
            self.is_running = False
            
            stop_message = f"""
🛑 **Automation Stopped!**

📊 **Session Summary:**
• Duration: {self.get_session_duration()}
• Accounts processed: {state['total_processed']}
• Successfully created: {state['successful']}
• Failed: {state['failed']}
• Last processed index: {state['current_index']}

💾 **State saved. Use `/start_auto {state['current_index']}` to resume.**
            """
            await update.message.reply_text(stop_message)
            
        except Exception as e:
            logger.error(f"Error stopping automation: {e}")
            await update.message.reply_text(f"❌ Error stopping automation: {str(e)}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            state = load_bot_state()
            accounts = load_gmail_accounts()
            
            if state['is_running']:
                status_icon = "🔄"
                status_text = "RUNNING"
            else:
                status_icon = "⏸️"
                status_text = "STOPPED"
            
            success_rate = 0
            if state['total_processed'] > 0:
                success_rate = (state['successful'] / state['total_processed']) * 100
            
            status_message = f"""
📊 **Current Automation Status**

{status_icon} **Process:** {status_text}
📅 **Started:** {state.get('started_at', 'N/A')}
✅ **Completed:** {state['successful']} accounts
❌ **Failed:** {state['failed']} accounts
⏳ **Current:** Processing account #{state['current_index'] + 1}
⏰ **ETA:** {self.calculate_eta(state, accounts)}

📈 **Success Rate:** {success_rate:.1f}%
📋 **Total Accounts:** {len(accounts)}
            """
            await update.message.reply_text(status_message)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            await update.message.reply_text(f"❌ Error getting status: {str(e)}")
    
    def run_automation(self, start_index, chat_id):
        try:
            accounts = load_gmail_accounts()
            static_password = load_static_password()
            
            state = load_bot_state()
            state['is_running'] = True
            state['current_index'] = start_index
            state['started_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            save_bot_state(state)
            
            for i in range(start_index, len(accounts)):
                if not state['is_running']:
                    break
                
                account = accounts[i]
                logger.info(f"Processing account {i+1}/{len(accounts)}: {account['email']}")
                
                if chat_id:
                    asyncio.run(self.send_progress_update(chat_id, i+1, len(accounts), account['email']))
                
                account_data = create_instagram_account(account['email'], account['app_password'], static_password)
                
                if account_data:
                    save_to_database(account_data)
                    state['successful'] += 1
                    state['total_processed'] += 1
                    if chat_id:
                        asyncio.run(self.send_success_message(chat_id, i+1, account_data))
                else:
                    state['failed'] += 1
                    state['total_processed'] += 1
                    if chat_id:
                        asyncio.run(self.send_failure_message(chat_id, i+1, account['email']))
                
                state['current_index'] = i + 1
                save_bot_state(state)
                
                if i < len(accounts) - 1 and 'DELAY_BETWEEN_ACCOUNTS' in dir():
                    time.sleep(DELAY_BETWEEN_ACCOUNTS)
                elif i < len(accounts) - 1:
                    time.sleep(60)
            
            if chat_id and state['is_running']:
                asyncio.run(self.send_completion_message(chat_id, state))
            
            state['is_running'] = False
            save_bot_state(state)
            
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")
            if chat_id:
                asyncio.run(self.send_error_message(chat_id, str(e)))
    
    async def send_progress_update(self, chat_id, current, total, email):
        try:
            message = f"""
🔄 **Processing Account #{current} ({current}/{total})**
📧 **Gmail:** {email}
⏰ **Started:** {time.strftime('%H:%M:%S')}
            """
            await self.bot.send_message(chat_id=chat_id, text=message)
        except TelegramError as e:
            logger.error(f"Error sending progress update: {e}")
    
    async def send_success_message(self, chat_id, account_num, account_data):
        try:
            message = f"""
✅ **Account #{account_num} Created Successfully!**

📋 **Account Details:**
• Username: {account_data['username']}
• Temp Email: {account_data['temp_email']}
• Password: **********
• 2FA Key: {account_data.get('secret_key', 'N/A')}
• Status: Active

💾 **Saved to Database**
⏱️ **Processing time:** {account_data.get('processing_time', 'N/A')}
            """
            await self.bot.send_message(chat_id=chat_id, text=message)
        except TelegramError as e:
            logger.error(f"Error sending success message: {e}")
    
    async def send_failure_message(self, chat_id, account_num, email):
        try:
            message = f"""
❌ **Account #{account_num} Failed!**

⚠️ **Error Details:**
• Gmail: {email}
• Error: Account creation failed
• Action: Skipping to next account

📊 **Current Stats:**
• Successful: {load_bot_state()['successful']}
• Failed: {load_bot_state()['failed']}
• Remaining: {len(load_gmail_accounts()) - account_num}
            """
            await self.bot.send_message(chat_id=chat_id, text=message)
        except TelegramError as e:
            logger.error(f"Error sending failure message: {e}")
    
    async def send_completion_message(self, chat_id, state):
        try:
            success_rate = 0
            if state['total_processed'] > 0:
                success_rate = (state['successful'] / state['total_processed']) * 100
            
            message = f"""
🎉 **Automation Complete!**

📊 **Final Report:**
• Total accounts processed: {state['total_processed']}
• Successfully created: {state['successful']} ({success_rate:.1f}%)
• Failed: {state['failed']}
• Total duration: {self.get_session_duration()}

📁 **Data saved to PostgreSQL**
🔄 **Use `/start_auto` to begin new session.**
            """
            await self.bot.send_message(chat_id=chat_id, text=message)
        except TelegramError as e:
            logger.error(f"Error sending completion message: {e}")
    
    async def send_error_message(self, chat_id, error):
        try:
            message = f"""
❌ **Automation Error!**

⚠️ **Error Details:**
{error}

🛑 **Automation stopped. Check logs for more details.**
            """
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        except TelegramError as e:
            logger.error(f"Error sending error message: {e}")
    
    def get_session_duration(self):
        state = load_bot_state()
        if 'started_at' in state and state['started_at'] != 'N/A':
            try:
                start_time = time.strptime(state['started_at'], '%Y-%m-%d %H:%M:%S')
                current_time = time.localtime()
                duration = time.mktime(current_time) - time.mktime(start_time)
                return f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m"
            except:
                return "N/A"
        return "N/A"
    
    def calculate_eta(self, state, accounts):
        if not state['is_running'] or state['current_index'] >= len(accounts):
            return "N/A"
        
        remaining = len(accounts) - state['current_index']
        avg_time_per_account = 5
        eta_minutes = remaining * avg_time_per_account
        
        if eta_minutes < 60:
            return f"{eta_minutes}m"
        else:
            hours = eta_minutes // 60
            minutes = eta_minutes % 60
            return f"{hours}h {minutes}m"
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("start_auto", self.start_auto_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
    
    def run(self):
        """Run the bot with polling mode (simpler for Render)"""
        try:
            self.setup_handlers()
            logger.info("Starting bot with polling mode...")
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Error running bot: {e}")

# API Endpoints for Web Dashboard
@api_app.route('/api/bot/status')
@limiter.limit("10 per minute")
def api_bot_status():
    try:
        state = load_bot_state()
        if db_manager:
            stats = DatabaseUtils.get_statistics()
        else:
            stats = {'total': 0, 'successful': 0, 'failed': 0, 'pending': 0, 'success_rate': 0}
        
        return jsonify({
            'status': 'online' if state['is_running'] else 'offline',
            'is_running': state['is_running'],
            'stats': {
                'total': stats['total'],
                'successful': stats['successful'],
                'failed': stats['failed'],
                'pending': stats['pending'],
                'successRate': stats['success_rate']
            },
            'bot_state': state
        })
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/bot/start', methods=['POST'])
@limiter.limit("5 per hour")
def api_start_bot():
    try:
        data = request.get_json()
        start_index = data.get('startIndex', 0) if data else 0
        
        state = load_bot_state()
        if state['is_running']:
            return jsonify({'error': 'Automation is already running'}), 400
        
        accounts = load_gmail_accounts()
        if start_index >= len(accounts):
            return jsonify({'error': f'Start index {start_index} is out of range. Total accounts: {len(accounts)}'}), 400
        
        bot_instance = InstagramBot()
        bot_instance.automation_thread = threading.Thread(target=bot_instance.run_automation, args=(start_index, None))
        bot_instance.automation_thread.daemon = True
        bot_instance.automation_thread.start()
        
        return jsonify({'success': True, 'message': 'Automation started', 'startIndex': start_index})
    except Exception as e:
        logger.error(f"Error starting automation: {e}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/bot/stop', methods=['POST'])
@limiter.limit("5 per hour")
def api_stop_bot():
    try:
        state = load_bot_state()
        if not state['is_running']:
            return jsonify({'error': 'No automation is currently running'}), 400
        
        if db_manager:
            DatabaseUtils.update_bot_state(is_running=False)
        
        return jsonify({'success': True, 'message': 'Automation stopped'})
    except Exception as e:
        logger.error(f"Error stopping automation: {e}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/accounts')
@limiter.limit("20 per minute")
def api_get_accounts():
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 503
            
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        accounts = DatabaseUtils.get_instagram_accounts(status)
        total = len(accounts)
        accounts = accounts[offset:offset + limit]
        
        accounts_data = []
        for account in accounts:
            accounts_data.append({
                'id': account.id,
                'username': account.username,
                'email': account.email,
                'temp_email': account.temp_email,
                'status': account.status,
                'created_at': account.created_at.strftime('%Y-%m-%d %H:%M:%S') if account.created_at else None,
                'processing_time': account.processing_time,
                'error_message': account.error_message
            })
        
        return jsonify({'accounts': accounts_data, 'total': total, 'limit': limit, 'offset': offset})
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/logs')
@limiter.limit("20 per minute")
def api_get_logs():
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 503
            
        limit = int(request.args.get('limit', 50))
        logs = DatabaseUtils.get_recent_logs(limit)
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'level': log.level,
                'message': log.message,
                'account_id': log.account_id,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else None
            })
        
        return jsonify({'logs': logs_data})
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/')
@api_app.route('/health')
def health_check():
    try:
        db_healthy = False
        if db_manager:
            try:
                db_healthy = db_manager.test_connection()
            except:
                db_healthy = False
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'connected' if db_healthy else 'disconnected',
            'bot_running': load_bot_state()['is_running'],
            'service': 'Instagram Automation Bot'
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

def run_api_server():
    """Run Flask API server on a different port"""
    try:
        # Use a different port for the API server (5000 is standard)
        api_port = 5000
        logger.info(f"Starting API server on port {api_port}...")
        api_app.run(host='0.0.0.0', port=api_port, debug=False)
    except Exception as e:
        logger.error(f"Error running API server: {e}")

# Helper functions
def load_bot_state():
    try:
        if db_manager:
            state = DatabaseUtils.get_bot_state()
            if state:
                return {
                    'is_running': state.is_running,
                    'current_index': state.current_index,
                    'total_processed': state.total_processed,
                    'successful': state.successful_count,
                    'failed': state.failed_count,
                    'started_at': state.started_at.strftime('%Y-%m-%d %H:%M:%S') if state.started_at else 'N/A'
                }
    except:
        pass
    
    state_file = 'bot_state.json'
    default_state = {'is_running': False, 'current_index': 0, 'total_processed': 0, 'successful': 0, 'failed': 0, 'started_at': 'N/A'}
    
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return json.load(f)
    except:
        pass
    
    return default_state

def save_bot_state(state):
    try:
        with open('bot_state.json', 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Error saving bot state: {e}")

def load_gmail_accounts():
    try:
        if db_manager:
            accounts = DatabaseUtils.get_unused_gmail_accounts()
            if accounts:
                return [{'email': acc.email, 'app_password': acc.app_password} for acc in accounts]
    except:
        pass
    
    try:
        with open('gmail_accounts.txt', 'r') as f:
            accounts = []
            for line in f:
                if ':' in line:
                    email, password = line.strip().split(':', 1)
                    accounts.append({'email': email, 'app_password': password})
            return accounts
    except:
        return []

def load_static_password():
    try:
        with open('password.txt', 'r') as f:
            return f.read().strip()
    except:
        return "DefaultPass123!"

def save_to_database(account_data):
    try:
        if db_manager:
            DatabaseUtils.add_instagram_account(
                username=account_data['username'],
                email=account_data['temp_email'],
                temp_email=account_data['temp_email'],
                password=account_data['password'],
                secret_key=account_data.get('secret_key'),
                status='successful',
                processing_time=account_data.get('processing_time')
            )
            return True
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
    return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting Instagram Automation Bot")
    logger.info("=" * 50)
    
    # Initialize database
    try:
        if db_manager and db_manager.test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection not available - some features may be limited")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    # Start Flask API server in a background thread (on port 5000)
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    logger.info("✅ API server thread started")
    
    # Start Telegram bot with polling mode (simpler, no port conflict)
    try:
        bot = InstagramBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
