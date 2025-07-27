import os
import json
import logging
import time
import base64
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Line Bot configuration
channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

if not channel_secret or not channel_access_token:
    logger.error("LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN must be set")
    raise ValueError("Missing required Line Bot credentials")

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# Google Sheets configuration
google_credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
google_credentials_base64 = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_BASE64')
google_credentials_file = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_FILE')
google_sheet_id = os.environ.get('GOOGLE_SHEET_ID')
google_sheet_name = os.environ.get('GOOGLE_SHEET_NAME', 'Sheet1')

if not google_sheet_id:
    logger.error("GOOGLE_SHEET_ID must be set")
    raise ValueError("Missing required Google Sheet ID")

if not google_credentials_json and not google_credentials_base64 and not google_credentials_file:
    logger.error("Either GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_CREDENTIALS_BASE64, or GOOGLE_SHEETS_CREDENTIALS_FILE must be set")
    raise ValueError("Missing required Google Sheets credentials")

# Initialize Google Sheets client
def init_google_sheets():
    try:
        if google_credentials_file:
            # Use credentials file (more secure for local development)
            if not os.path.exists(google_credentials_file):
                raise FileNotFoundError(f"Credentials file not found: {google_credentials_file}")
            credentials = Credentials.from_service_account_file(
                google_credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            logger.info("Using Google credentials from file")
        elif google_credentials_base64:
            # Use BASE64 encoded credentials (recommended for deployment)
            try:
                # Fix BASE64 padding if needed
                base64_str = google_credentials_base64.strip()
                # Add padding if necessary
                missing_padding = len(base64_str) % 4
                if missing_padding:
                    base64_str += '=' * (4 - missing_padding)
                
                # Decode BASE64
                decoded_credentials = base64.b64decode(base64_str).decode('utf-8')
                # Remove any control characters and whitespace
                cleaned_credentials = ''.join(char for char in decoded_credentials if ord(char) >= 32 or char in '\t\n\r')
                # Strip leading/trailing whitespace
                cleaned_credentials = cleaned_credentials.strip()
                
                credentials_dict = json.loads(cleaned_credentials)
                credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                logger.info("Using Google credentials from BASE64 environment variable")
            except base64.binascii.Error as e:
                logger.error(f"Failed to decode BASE64 credentials: {e}")
                logger.error(f"BASE64 string length: {len(google_credentials_base64)}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from BASE64 credentials: {e}")
                logger.error(f"Decoded content preview: {decoded_credentials[:200]}...")
                raise
            except Exception as e:
                logger.error(f"Failed to decode BASE64 credentials: {e}")
                raise
        else:
            # Use credentials from JSON environment variable (fallback)
            credentials_dict = json.loads(google_credentials_json)
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            logger.info("Using Google credentials from JSON environment variable")
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise

google_client = init_google_sheets()

def write_to_google_sheet(timestamp, user_id, user_name, message_text, max_retries=3):
    """Write message data to Google Sheet with retry mechanism"""
    for attempt in range(max_retries):
        try:
            sheet = google_client.open_by_key(google_sheet_id).worksheet(google_sheet_name)
            
            # Prepare row data
            row_data = [timestamp, user_id, user_name, message_text]
            
            # Append row to sheet
            sheet.append_row(row_data)
            logger.info(f"Successfully wrote to Google Sheet: {user_id} - {message_text[:50]}...")
            return True
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to write to Google Sheet: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to write to Google Sheet after {max_retries} attempts: {e}")
                return False
    
    return False

@app.route("/callback", methods=['POST'])
def callback():
    """Handle Line Bot webhook"""
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    logger.info(f"Request body: {body}")

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        abort(500)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handle text messages from Line Bot"""
    try:
        # Get message data
        user_id = event.source.user_id
        message_text = event.message.text
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get user profile
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError as e:
            logger.warning(f"Could not get user profile: {e}")
            user_name = "Unknown"
        
        logger.info(f"Received message from {user_name} ({user_id}): {message_text}")
        
        # Write to Google Sheet
        success = write_to_google_sheet(timestamp, user_id, user_name, message_text)
        
        # Prepare reply message
        if success:
            reply_text = "✅ 您的訊息已成功記錄！"
        else:
            reply_text = "❌ 抱歉，記錄訊息時發生錯誤，請稍後再試。"
        
        # Reply to user
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # Send error message to user
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 處理訊息時發生錯誤，請稍後再試。")
            )
        except Exception as reply_error:
            logger.error(f"Error sending reply: {reply_error}")

@handler.default
def default_handler(event):
    """Handle non-text messages"""
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="📝 目前僅支援文字訊息記錄，請傳送文字訊息。")
        )
    except Exception as e:
        logger.error(f"Error handling non-text message: {e}")

@app.route('/health')
def health_check():
    """Health check endpoint for Zeabur"""
    try:
        # Test Google Sheets connection
        google_client.open_by_key(google_sheet_id)
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}, 500

@app.route('/')
def index():
    """Basic index route"""
    return {'message': 'Line Bot is running', 'timestamp': datetime.now().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Line Bot server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)