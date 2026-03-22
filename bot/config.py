# Telegram Bot Configuration
import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8651675539:AAHB3Of0D66_PQMoqLYseMoKJBv8ZDP4kKg')
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Alias for backward compatibility

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://instagram_user:o7fYknqmWRdfL62UTq90QBq5pMucWN8b@dpg-d6vndnv5r7bs73etiab0-a/instagram_db_t9mg')

# Google Sheets Configuration
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Instagram Accounts Database')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', 'Accounts')

# Automation Settings
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'False').lower() == 'true'
DELAY_BETWEEN_ACCOUNTS = int(os.getenv('DELAY_BETWEEN_ACCOUNTS', '30'))
STATIC_PASSWORD = os.getenv('STATIC_PASSWORD', 'SecurePassword123!')

# Web Dashboard Configuration
WEB_DASHBOARD_URL = os.getenv('WEB_DASHBOARD_URL', 'https://instaau.netlify.app')

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')  # Changed from /app/logs/bot.log to avoid permission issues

# Database Connection Settings
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
