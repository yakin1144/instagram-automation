import time
import json
import imaplib
import email
import re
import requests
import os
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pyotp
from config import *
from database import DatabaseUtils

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_gmail_code(email_address, app_password):
    """Extract 6-digit verification code from Gmail"""
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, app_password)
        mail.select('inbox')
        
        # Search for Instagram verification emails
        status, messages = mail.search(None, 'FROM', 'instagram.com')
        if not messages[0]:
            return None
            
        # Get the latest email
        latest_email_id = messages[0].split()[-1]
        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        
        # Parse email content
        email_body = msg_data[0][1].decode('utf-8')
        msg = email.message_from_string(email_body)
        
        # Extract verification code
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8')
                    code_match = re.search(r'\b\d{6}\b', body)
                    if code_match:
                        mail.close()
                        mail.logout()
                        return code_match.group()
        
        mail.close()
        mail.logout()
        return None
        
    except Exception as e:
        logger.error(f"Error getting Gmail code: {e}")
        return None

def get_temp_email():
    """Get temporary email from mailvn.site"""
    try:
        response = requests.get('https://mailvn.site')
        if response.status_code == 200:
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@mailvn\.site)', response.text)
            if email_match:
                return email_match.group(1)
        return None
    except Exception as e:
        logger.error(f"Error getting temp email: {e}")
        return None

def download_profile_image():
    """Download AI-generated profile image"""
    try:
        response = requests.get('https://thispersondoesnotexist.com/image')
        if response.status_code == 200:
            with open('/tmp/profile.jpg', 'wb') as f:
                f.write(response.content)
            return '/tmp/profile.jpg'
        return None
    except Exception as e:
        logger.error(f"Error downloading profile image: {e}")
        return None

def create_instagram_account(gmail_account, app_password, static_password):
    """Main function to create Instagram account using Chrome"""
    driver = None
    start_time = time.time()
    
    try:
        # Log the start of account creation
        DatabaseUtils.add_automation_log("info", f"Starting Instagram account creation for {gmail_account}")
        
        # Initialize Chrome WebDriver (Render has Chrome pre-installed)
        options = Options()
        if HEADLESS_MODE:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.implicitly_wait(10)
        
        # Step 1: Instagram Signup
        logger.info("Starting Instagram signup process")
        DatabaseUtils.add_automation_log("info", "Navigating to Instagram signup page")
        
        driver.get('https://www.instagram.com/accounts/emailsignup/')
        
        # Fill signup form
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "emailOrPhone"))
        )
        email_field.send_keys(gmail_account)
        
        fullname_field = driver.find_element(By.NAME, "fullName")
        fullname_field.send_keys("John Doe")
        
        username_field = driver.find_element(By.NAME, "username")
        username_field.send_keys(f"user_{int(time.time())}")
        
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(static_password)
        
        # Submit form
        signup_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        signup_button.click()
        
        DatabaseUtils.add_automation_log("info", "Instagram signup form submitted")
        
        # Step 2: Email Verification
        logger.info("Waiting for email verification")
        time.sleep(5)
        
        # Get verification code from Gmail
        verification_code = get_gmail_code(gmail_account, app_password)
        if not verification_code:
            error_msg = "Failed to get verification code from Gmail"
            DatabaseUtils.add_automation_log("error", error_msg)
            raise Exception(error_msg)
        
        DatabaseUtils.add_automation_log("info", f"Retrieved verification code: {verification_code}")
        
        # Enter verification code
        code_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "email_confirmation_code"))
        )
        code_field.send_keys(verification_code)
        
        # Submit verification
        verify_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        verify_button.click()
        
        DatabaseUtils.add_automation_log("info", "Email verification completed")
        
        # Step 3: Profile Setup
        logger.info("Setting up profile")
        time.sleep(5)
        
        # Download and upload profile picture
        profile_image_path = download_profile_image()
        if profile_image_path:
            try:
                # Upload profile picture
                file_input = driver.find_element(By.XPATH, "//input[@type='file']")
                file_input.send_keys(profile_image_path)
                time.sleep(3)
                
                # Click next
                next_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Next')]")
                next_button.click()
                time.sleep(2)
                
                # Skip additional steps
                skip_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Skip')]")
                skip_button.click()
                
                DatabaseUtils.add_automation_log("info", "Profile picture uploaded successfully")
            except Exception as e:
                logger.warning(f"Profile picture upload failed: {e}")
                DatabaseUtils.add_automation_log("warning", f"Profile picture upload failed: {e}")
        
        # Step 4: Get final username
        try:
            final_username = driver.find_element(By.XPATH, "//h2").text
        except:
            final_username = f"user_{int(time.time())}"
        
        DatabaseUtils.add_automation_log("info", f"Instagram username: {final_username}")
        
        # Step 5: Email Replacement
        logger.info("Replacing email with temporary email")
        
        # Get temporary email
        temp_email = get_temp_email()
        if not temp_email:
            temp_email = f"temp_{int(time.time())}@mailvn.site"
            DatabaseUtils.add_automation_log("warning", "Using fallback temporary email")
        
        DatabaseUtils.add_automation_log("info", f"Temporary email: {temp_email}")
        
        # Step 6: 2FA Setup
        logger.info("Setting up 2FA")
        
        try:
            # Navigate to 2FA settings
            driver.get('https://www.instagram.com/accounts/two_factor_authentication/')
            time.sleep(3)
            
            # Enable 2FA with authenticator app
            auth_app_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Authentication App')]")
            auth_app_button.click()
            time.sleep(3)
            
            # Extract 2FA secret key
            secret_key_element = driver.find_element(By.XPATH, "//code")
            secret_key = secret_key_element.text
            
            # Complete 2FA setup
            confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]")
            confirm_button.click()
            
            DatabaseUtils.add_automation_log("info", f"2FA setup completed with key: {secret_key}")
        except Exception as e:
            logger.warning(f"2FA setup failed: {e}")
            secret_key = None
            DatabaseUtils.add_automation_log("warning", f"2FA setup failed: {e}")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Save account data to database
        success = DatabaseUtils.add_instagram_account(
            username=final_username,
            email=gmail_account,
            temp_email=temp_email,
            password=static_password,
            secret_key=secret_key,
            status='successful',
            processing_time=processing_time
        )
        
        if success:
            # Mark Gmail account as used
            DatabaseUtils.mark_gmail_account_used(gmail_account)
            
            # Log success
            DatabaseUtils.add_automation_log("info", f"Account created successfully: {final_username}")
            
            # Return account data
            account_data = {
                'username': final_username,
                'temp_email': temp_email,
                'password': static_password,
                'secret_key': secret_key,
                'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'successful',
                'processing_time': processing_time
            }
            
            logger.info(f"Account created successfully: {final_username}")
            return account_data
        else:
            raise Exception("Failed to save account data to database")
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Error creating Instagram account: {e}"
        logger.error(error_msg)
        
        # Save failed account to database
        DatabaseUtils.add_instagram_account(
            username=f"failed_{int(time.time())}",
            email=gmail_account,
            temp_email=None,
            password=static_password,
            secret_key=None,
            status='failed',
            processing_time=processing_time,
            error_message=str(e)
        )
        
        # Log error
        DatabaseUtils.add_automation_log("error", error_msg)
        
        return None
        
    finally:
        if driver:
            driver.quit()

def save_to_google_sheets(account_data):
    """Save account data to database (Supabase) - Google Sheets removed for Render compatibility"""
    # Data is already saved in database from create_instagram_account
    logger.info(f"Account data for {account_data.get('username')} is already saved in Supabase")
    return True

def load_bot_state():
    """Load bot state from database"""
    try:
        bot_state = DatabaseUtils.get_bot_state()
        if bot_state:
            return {
                'is_running': bot_state.is_running,
                'current_index': bot_state.current_index,
                'total_processed': bot_state.total_processed,
                'successful': bot_state.successful_count,
                'failed': bot_state.failed_count,
                'started_at': bot_state.started_at.strftime('%Y-%m-%d %H:%M:%S') if bot_state.started_at else None,
                'last_updated': bot_state.last_updated.strftime('%Y-%m-%d %H:%M:%S') if bot_state.last_updated else None
            }
        return {
            'is_running': False,
            'current_index': 0,
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'started_at': None,
            'last_updated': None
        }
    except Exception as e:
        logger.error(f"Error loading bot state: {e}")
        return {
            'is_running': False,
            'current_index': 0,
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'started_at': None,
            'last_updated': None
        }

def save_bot_state(state):
    """Save bot state to database"""
    try:
        DatabaseUtils.update_bot_state(
            is_running=state.get('is_running'),
            current_index=state.get('current_index'),
            total_processed=state.get('total_processed'),
            successful_count=state.get('successful'),
            failed_count=state.get('failed'),
            started_at=datetime.strptime(state['started_at'], '%Y-%m-%d %H:%M:%S') if state.get('started_at') else None
        )
    except Exception as e:
        logger.error(f"Error saving bot state: {e}")

def load_gmail_accounts():
    """Load Gmail accounts from database"""
    try:
        accounts = DatabaseUtils.get_unused_gmail_accounts()
        return [{'email': acc.email, 'app_password': acc.app_password} for acc in accounts]
    except Exception as e:
        logger.error(f"Error loading Gmail accounts: {e}")
        return []

def load_static_password():
    """Load static password from configuration"""
    return STATIC_PASSWORD
