import os
import json
import logging
import time
import base64
import io
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, AudioMessage
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.cloud import speech
from dotenv import load_dotenv
import requests

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

# Support for simple credentials (individual environment variables)
google_project_id = os.environ.get('GOOGLE_PROJECT_ID')
google_private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
google_client_email = os.environ.get('GOOGLE_CLIENT_EMAIL')

google_sheet_id = os.environ.get('GOOGLE_SHEET_ID')
google_sheet_name = os.environ.get('GOOGLE_SHEET_NAME', 'Sheet1')

# Option to disable Google Drive upload (useful when quota is exceeded)
disable_drive_upload = os.environ.get('DISABLE_DRIVE_UPLOAD', 'false').lower() == 'true'

# Option to disable speech-to-text conversion (useful when API has issues)
disable_speech_conversion = os.environ.get('DISABLE_SPEECH_CONVERSION', 'false').lower() == 'true'

if not google_sheet_id:
    logger.error("GOOGLE_SHEET_ID must be set")
    raise ValueError("Missing required Google Sheet ID")

# Check if we have any form of credentials
has_json = google_credentials_json
has_base64 = google_credentials_base64
has_file = google_credentials_file
has_simple = google_project_id and google_private_key and google_client_email

# Debug logging
logger.info(f"Credential detection status:")
logger.info(f"  - JSON: {'Yes' if has_json else 'No'}")
logger.info(f"  - BASE64: {'Yes' if has_base64 else 'No'}")
logger.info(f"  - File: {'Yes' if has_file else 'No'}")
logger.info(f"  - Individual vars: {'Yes' if has_simple else 'No'}")
logger.info(f"  - GOOGLE_PROJECT_ID: {'Set' if google_project_id else 'Not set'}")
logger.info(f"  - GOOGLE_PRIVATE_KEY: {'Set' if google_private_key else 'Not set'}")
logger.info(f"  - GOOGLE_CLIENT_EMAIL: {'Set' if google_client_email else 'Not set'}")

if not (has_json or has_base64 or has_file or has_simple):
    logger.error("Must provide credentials via one of: GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_CREDENTIALS_BASE64, GOOGLE_SHEETS_CREDENTIALS_FILE, or GOOGLE_PROJECT_ID+GOOGLE_PRIVATE_KEY+GOOGLE_CLIENT_EMAIL")
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
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/cloud-platform'
                ]
            )
            logger.info("Using Google credentials from file")
        elif has_simple:
            # Use individual environment variables (best for deployment with long credentials)
            try:
                # Clean and format private key
                private_key = google_private_key.strip()
                
                # Add headers if missing
                if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                    private_key = '-----BEGIN PRIVATE KEY-----\n' + private_key
                if not private_key.endswith('-----END PRIVATE KEY-----'):
                    private_key = private_key + '\n-----END PRIVATE KEY-----'
                
                # Fix newlines in private key - handle both literal \n and actual newlines
                private_key = private_key.replace('\\n', '\n')
                
                logger.info(f"Private key format check - starts with BEGIN: {private_key.startswith('-----BEGIN')}")
                logger.info(f"Private key format check - ends with END: {private_key.endswith('-----END PRIVATE KEY-----')}")
                
                # Construct credentials dictionary
                credentials_dict = {
                    "type": "service_account",
                    "project_id": google_project_id,
                    "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID', ''),
                    "private_key": private_key,
                    "client_email": google_client_email,
                    "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{google_client_email.replace('@', '%40')}"
                }
                
                credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
                )
                logger.info("Using Google credentials from individual environment variables")
            except Exception as e:
                logger.error(f"Failed to create credentials from individual variables: {e}")
                raise
        elif google_credentials_base64:
            # Use BASE64 encoded credentials (fallback method)
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
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
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
        return client, credentials
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise

google_client, google_credentials = init_google_sheets()

# Initialize Google Drive service
def init_google_drive():
    try:
        drive_service = build('drive', 'v3', credentials=google_credentials)
        logger.info("Google Drive service initialized successfully")
        return drive_service
    except Exception as e:
        logger.error(f"Failed to initialize Google Drive service: {e}")
        raise

drive_service = init_google_drive()

# Initialize Google Speech-to-Text service
def init_speech_service():
    try:
        speech_client = speech.SpeechClient(credentials=google_credentials)
        logger.info("Google Speech-to-Text service initialized successfully")
        return speech_client
    except Exception as e:
        logger.error(f"Failed to initialize Google Speech-to-Text service: {e}")
        raise

speech_client = init_speech_service()

def convert_audio_to_text(audio_content):
    """Convert audio content to text using Google Speech-to-Text API"""
    try:
        # Line audio is typically in AAC format, let's try the most common configurations
        configs_to_try = [
            # Try with ENCODING_UNSPECIFIED first (let Google auto-detect)
            speech.RecognitionConfig(
                language_code="zh-TW",
                alternative_language_codes=["en-US", "zh-CN"],
                enable_automatic_punctuation=True,
                model="latest_short"
            ),
            # Try with MP3 (common format)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                language_code="zh-TW",
                alternative_language_codes=["en-US", "zh-CN"],
                enable_automatic_punctuation=True,
                model="latest_short"
            ),
            # Try with FLAC
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
                language_code="zh-TW",
                alternative_language_codes=["en-US", "zh-CN"],
                enable_automatic_punctuation=True,
                model="latest_short"
            ),
            # Try with LINEAR16 at different sample rates  
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="zh-TW",
                alternative_language_codes=["en-US", "zh-CN"],
                enable_automatic_punctuation=True,
                model="latest_short"
            ),
            # Try MULAW (telephony format)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
                sample_rate_hertz=8000,
                language_code="zh-TW",
                alternative_language_codes=["en-US", "zh-CN"],
                enable_automatic_punctuation=True,
                model="latest_short"
            )
        ]
        
        # Create audio object
        audio = speech.RecognitionAudio(content=audio_content)
        logger.info(f"Starting speech recognition for audio of size: {len(audio_content)} bytes")
        
        # Try different configurations
        for i, config in enumerate(configs_to_try):
            try:
                config_name = config.encoding.name if config.encoding else "UNSPECIFIED"
                logger.info(f"Trying recognition config {i+1}/{len(configs_to_try)}: {config_name}")
                
                # Create a new client instance with explicit credentials for each attempt
                client = speech.SpeechClient(credentials=google_credentials)
                response = client.recognize(config=config, audio=audio)
                
                # Extract transcribed text
                if response.results:
                    transcript = ""
                    confidence_scores = []
                    for result in response.results:
                        transcript += result.alternatives[0].transcript + " "
                        confidence_scores.append(result.alternatives[0].confidence)
                    
                    transcript = transcript.strip()
                    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
                    logger.info(f"Speech recognition successful with config {i+1}: confidence={avg_confidence:.2f}")
                    logger.info(f"Transcript: {transcript[:200]}...")
                    return transcript
                else:
                    logger.info(f"No speech detected with config {i+1}")
                    continue
                    
            except Exception as config_error:
                error_msg = str(config_error)
                logger.warning(f"Config {i+1} ({config_name}) failed: {error_msg}")
                
                # Don't continue if it's an authentication error
                if "401" in error_msg or "403" in error_msg:
                    raise config_error
                    
                if i == len(configs_to_try) - 1:  # Last attempt
                    logger.error("All configurations failed")
                continue
        
        logger.warning("All recognition configs failed, no speech detected")
        return None
            
    except Exception as e:
        logger.error(f"Failed to convert audio to text: {e}")
        if "401" in str(e):
            logger.error("Authentication failed. Check if Speech-to-Text API is enabled and credentials are correct.")
        elif "403" in str(e):
            logger.error("Permission denied. Check API permissions and quotas.")
        elif "400" in str(e):
            logger.error("Bad request. Audio format might not be supported.")
        return None

def upload_image_to_drive(image_content, filename, user_id):
    """Upload image to Google Drive and return shareable link"""
    try:
        # Create file metadata - use a specific folder if needed
        file_metadata = {
            'name': f"{user_id}_{filename}",
            'parents': []  # Upload to root folder
        }
        
        # Check image size and log it
        logger.info(f"Image size: {len(image_content)} bytes")
        
        # Create media upload object with non-resumable upload for small files
        media = MediaIoBaseUpload(
            io.BytesIO(image_content),
            mimetype='image/jpeg',
            resumable=False  # Use non-resumable for small files
        )
        
        # Upload file with fields to get more info
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,size,webViewLink'
        ).execute()
        
        file_id = file.get('id')
        file_size = file.get('size', 'unknown')
        logger.info(f"Successfully uploaded image to Google Drive: {file_id}, size: {file_size} bytes")
        
        # Make file publicly readable
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            drive_service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            logger.info(f"Successfully set public permissions for file: {file_id}")
        except Exception as perm_error:
            logger.warning(f"Failed to set public permissions: {perm_error}")
        
        # Generate shareable link
        drive_link = f"https://drive.google.com/file/d/{file_id}/view"
        logger.info(f"Generated Drive link: {drive_link}")
        
        return drive_link
        
    except Exception as e:
        logger.error(f"Failed to upload image to Google Drive: {e}")
        if "403" in str(e):
            if "accessNotConfigured" in str(e):
                logger.error("Google Drive API is not enabled for this project. Please enable it in Google Cloud Console.")
            elif "storageQuotaExceeded" in str(e):
                logger.error("Google Drive storage quota exceeded. Please free up space or upgrade storage.")
            else:
                logger.error(f"Google Drive access denied: {e}")
        return None

def write_to_google_sheet(timestamp, user_id, user_name, message_text, image_link=None, max_retries=3):
    """Write message data to Google Sheet with retry mechanism"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}: Opening Google Sheet with ID: {google_sheet_id}")
            spreadsheet = google_client.open_by_key(google_sheet_id)
            logger.info(f"Successfully opened spreadsheet: {spreadsheet.title}")
            
            # List all worksheets for debugging
            worksheets = spreadsheet.worksheets()
            worksheet_names = [ws.title for ws in worksheets]
            logger.info(f"Available worksheets: {worksheet_names}")
            
            # Always use the first worksheet to avoid naming issues
            sheet = worksheets[0]
            logger.info(f"Using first worksheet: {sheet.title}")
            
            # Prepare row data - include image link if available
            if image_link:
                row_data = [timestamp, user_id, user_name, message_text, image_link]
            else:
                row_data = [timestamp, user_id, user_name, message_text, ""]
            logger.info(f"Prepared row data: {row_data}")
            
            # Append row to sheet
            sheet.append_row(row_data)
            logger.info(f"Successfully wrote to Google Sheet: {user_id} - {message_text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed to write to Google Sheet: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            if hasattr(e, 'response'):
                logger.error(f"Response status: {getattr(e, 'response', {}).get('status', 'N/A')}")
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

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    """Handle image messages from Line Bot"""
    try:
        # Get message data
        user_id = event.source.user_id
        message_id = event.message.id
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get user profile
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError as e:
            logger.warning(f"Could not get user profile: {e}")
            user_name = "Unknown"
        
        logger.info(f"Received image from {user_name} ({user_id}): {message_id}")
        
        # Download image content from Line
        try:
            message_content = line_bot_api.get_message_content(message_id)
            image_content = message_content.content
            logger.info(f"Downloaded image content, size: {len(image_content)} bytes")
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 下載圖片時發生錯誤。")
            )
            return
        
        # Check if Drive upload is disabled or try to upload
        if disable_drive_upload:
            logger.info("Google Drive upload is disabled, recording image info only")
            drive_link = f"圖片已接收 (ID: {message_id}, 大小: {len(image_content)} bytes)"
        else:
            # Try to upload to Google Drive first, fallback to info if failed
            filename = f"{timestamp.replace(':', '-').replace(' ', '_')}.jpg"
            drive_link = upload_image_to_drive(image_content, filename, user_id)
            
            # If Drive upload fails, record image info instead
            if not drive_link:
                logger.info("Drive upload failed, recording image info only")
                drive_link = f"圖片上傳失敗 (ID: {message_id}, 大小: {len(image_content)} bytes)"
        
        # Write to Google Sheet
        success = write_to_google_sheet(timestamp, user_id, user_name, "📷 圖片訊息", drive_link)
        
        if success:
            if "drive.google.com" in drive_link:
                reply_text = f"✅ 您的圖片已成功記錄並上傳到 Google Drive！\n🔗 連結：{drive_link}"
            else:
                reply_text = "✅ 您的圖片已成功記錄！\n📝 註：由於雲端空間限制，圖片已記錄但未上傳到 Drive"
        else:
            reply_text = "❌ 抱歉，記錄圖片時發生錯誤，請稍後再試。"
        
        # Reply to user
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        # Send error message to user
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 處理圖片時發生錯誤，請稍後再試。")
            )
        except Exception as reply_error:
            logger.error(f"Error sending reply: {reply_error}")

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    """Handle audio messages from Line Bot"""
    try:
        # Get message data
        user_id = event.source.user_id
        message_id = event.message.id
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        duration = event.message.duration  # Audio duration in milliseconds
        
        # Get user profile
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError as e:
            logger.warning(f"Could not get user profile: {e}")
            user_name = "Unknown"
        
        logger.info(f"Received audio from {user_name} ({user_id}): {message_id}, duration: {duration}ms")
        
        # Download audio content from Line
        try:
            message_content = line_bot_api.get_message_content(message_id)
            audio_content = message_content.content
            logger.info(f"Downloaded audio content, size: {len(audio_content)} bytes")
        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 下載語音訊息時發生錯誤。")
            )
            return
        
        # Check if speech conversion is disabled or try to convert
        if disable_speech_conversion:
            logger.info("Speech-to-text conversion is disabled, recording audio info only")
            # Record audio message info without conversion
            success = write_to_google_sheet(
                timestamp, 
                user_id, 
                user_name, 
                f"🎤 語音訊息已接收 (時長: {duration}ms, 大小: {len(audio_content)} bytes)"
            )
            reply_text = "✅ 語音訊息已成功記錄！\n📝 註：語音轉文字功能目前停用，僅記錄語音資訊"
        else:
            # Try to convert audio to text
            logger.info("Starting speech-to-text conversion...")
            transcribed_text = convert_audio_to_text(audio_content)
            
            if transcribed_text:
                # Write transcribed text to Google Sheet
                success = write_to_google_sheet(
                    timestamp, 
                    user_id, 
                    user_name, 
                    f"🎤 語音轉文字: {transcribed_text}"
                )
                
                if success:
                    reply_text = f"✅ 語音訊息已成功轉換並記錄！\n\n📝 轉換結果：\n「{transcribed_text}」"
                else:
                    reply_text = f"✅ 語音轉換成功，但記錄時發生錯誤。\n\n📝 轉換結果：\n「{transcribed_text}」"
            else:
                # Even if transcription fails, record that we received an audio message
                success = write_to_google_sheet(
                    timestamp, 
                    user_id, 
                    user_name, 
                    f"🎤 語音訊息 (轉換失敗，時長: {duration}ms, 大小: {len(audio_content)} bytes)"
                )
                reply_text = "❌ 抱歉，無法識別語音內容。請確保語音清晰並重新嘗試。"
        
        # Reply to user
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        
    except Exception as e:
        logger.error(f"Error handling audio: {e}")
        # Send error message to user
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 處理語音訊息時發生錯誤，請稍後再試。")
            )
        except Exception as reply_error:
            logger.error(f"Error sending reply: {reply_error}")

# Remove the problematic default handler for now

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