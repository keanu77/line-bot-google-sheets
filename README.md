# Line Bot with Google Sheets Integration

這是一個完整的 Line Bot 專案，可以接收用戶訊息並自動記錄到 Google Sheets 中，適合部署在 Zeabur 平台。

## 功能特色

- 🤖 接收 Line 用戶的文字訊息
- 📊 自動將訊息資料寫入 Google Sheets（時間戳記、用戶ID、用戶名稱、訊息內容）
- ✅ 回覆用戶確認訊息已記錄
- 🔄 包含重試機制處理 API 失敗
- 🚀 支援 Zeabur 部署
- 🛡️ 完整的錯誤處理和日誌記錄
- 🔒 支援多種憑證管理方式，保護機密資料

## 專案結構

```
├── main.py              # 主應用程式
├── requirements.txt     # Python 依賴套件
├── .env.example        # 環境變數範例
├── .gitignore          # Git 忽略檔案
└── README.md           # 專案說明
```

## 前置準備

### 1. Line Bot 設定

1. 前往 [Line Developers Console](https://developers.line.biz/console/)
2. 建立新的 Provider 和 Messaging API Channel
3. 取得以下資訊：
   - Channel Secret
   - Channel Access Token

### 2. Google Cloud 設定

#### 建立 Google Cloud 專案
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用 Google Sheets API：
   - 前往 APIs & Services > Library
   - 搜尋 "Google Sheets API"
   - 點擊啟用

#### 建立服務帳戶
1. 前往 IAM & Admin > Service Accounts
2. 點擊 "Create Service Account"
3. 填入服務帳戶名稱和描述
4. 點擊 "Create and Continue"
5. 不需要指派角色，點擊 "Continue"
6. 點擊 "Done"

#### 建立服務帳戶金鑰
1. 點擊剛建立的服務帳戶
2. 前往 "Keys" 分頁
3. 點擊 "Add Key" > "Create new key"
4. 選擇 JSON 格式
5. 下載金鑰檔案

#### 設定 Google Sheets
1. 建立一個新的 Google Sheets 文件
2. 從 URL 中複製 Sheet ID（例如：`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`）
3. 將服務帳戶的 email 加入 Sheet 的協作者（編輯權限）
4. 在 Sheet 中建立標題列：
   - A1: 時間
   - B1: 用戶ID
   - C1: 用戶名稱
   - D1: 訊息內容

## 🔒 機密資料安全管理

本專案提供兩種憑證管理方式，讓您可以根據環境選擇最安全的方式：

### 方法 1: 憑證檔案 (推薦用於本地開發)
- 將 Google 服務帳戶 JSON 檔案放在本地目錄
- 憑證檔案不會被提交到 Git 儲存庫
- 使用 `GOOGLE_SHEETS_CREDENTIALS_FILE` 環境變數指定檔案路徑

### 方法 2: 環境變數 (用於部署平台)
- 將 JSON 憑證作為環境變數存儲
- 適合 Zeabur、Heroku 等雲端平台
- 使用 `GOOGLE_SHEETS_CREDENTIALS` 環境變數

### 安全建議
- ✅ **本地開發**: 使用憑證檔案，避免在 `.env` 中存儲完整 JSON
- ✅ **雲端部署**: 使用平台的環境變數功能，避免硬編碼
- ❌ **避免**: 將憑證直接寫在程式碼中或提交到 Git

## 本地開發

### 1. 克隆專案

```bash
git clone <your-repo-url>
cd line-bot-google-sheets
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

複製 `.env.example` 為 `.env`：

```bash
cp .env.example .env
```

#### 🔒 安全方式: 使用憑證檔案 (推薦)

1. 建立 `credentials` 目錄：
```bash
mkdir credentials
```

2. 將下載的 Google 服務帳戶 JSON 檔案放入 `credentials` 目錄：
```bash
mv ~/Downloads/your-service-account-key.json ./credentials/service-account-key.json
```

3. 編輯 `.env` 檔案：
```env
# Line Bot Configuration
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here

# Google Sheets Configuration (使用檔案路徑)
GOOGLE_SHEETS_CREDENTIALS_FILE=./credentials/service-account-key.json
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_SHEET_NAME=Sheet1

# Server Configuration
PORT=5000
```

#### 替代方式: 使用環境變數
如果您仍想使用環境變數方式，可以註解掉 `GOOGLE_SHEETS_CREDENTIALS_FILE` 並使用：
```env
# GOOGLE_SHEETS_CREDENTIALS_FILE=./credentials/service-account-key.json
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}  # 完整的 JSON 字串
```

### 4. 執行應用程式

```bash
python main.py
```

### 5. 設定 Webhook URL

使用 ngrok 或其他工具建立公開 URL：

```bash
ngrok http 5000
```

在 Line Developers Console 中設定 Webhook URL：
`https://your-ngrok-url.ngrok.io/callback`

## Zeabur 部署

### 1. 建立 Zeabur 專案

1. 前往 [Zeabur Dashboard](https://dash.zeabur.com/)
2. 建立新專案
3. 連接你的 GitHub 儲存庫

### 2. 設定環境變數

在 Zeabur 專案設定中加入以下環境變數：

- `LINE_CHANNEL_SECRET`: Line Bot Channel Secret
- `LINE_CHANNEL_ACCESS_TOKEN`: Line Bot Channel Access Token
- `GOOGLE_SHEETS_CREDENTIALS`: Google 服務帳戶 JSON 憑證（完整字串）
- `GOOGLE_SHEET_ID`: Google Sheets 文件 ID
- `GOOGLE_SHEET_NAME`: 工作表名稱（預設為 Sheet1）
- `PORT`: 埠號（Zeabur 會自動設定）

### 3. 部署

1. 推送程式碼到 GitHub
2. Zeabur 會自動偵測並開始部署
3. 部署完成後，複製提供的 URL

### 4. 更新 Line Bot Webhook

在 Line Developers Console 中更新 Webhook URL：
`https://your-zeabur-app.zeabur.app/callback`

## API 端點

- `POST /callback` - Line Bot Webhook 端點
- `GET /health` - 健康檢查端點
- `GET /` - 基本狀態端點

## 錯誤處理

- 自動重試機制（最多 3 次）
- 完整的日誌記錄
- 優雅的錯誤回應
- Webhook 簽名驗證

## 安全性考量

- 環境變數儲存敏感資訊
- Webhook 簽名驗證
- 適當的異常處理
- 不在日誌中記錄敏感資訊

## 疑難排解

### 常見問題

1. **Line Bot 無法接收訊息**
   - 檢查 Webhook URL 是否正確
   - 確認環境變數設定正確
   - 查看應用程式日誌

2. **Google Sheets 寫入失敗**
   - 確認服務帳戶有 Sheet 編輯權限
   - 檢查 Sheet ID 是否正確
   - 確認服務帳戶 JSON 格式正確

3. **部署失敗**
   - 檢查 requirements.txt 是否包含所有依賴
   - 確認環境變數在 Zeabur 中正確設定
   - 查看部署日誌錯誤訊息

### 日誌查看

在 Zeabur 中可以查看即時日誌來診斷問題：

1. 前往專案儀表板
2. 點擊服務
3. 查看 "Logs" 分頁

## 技術架構

- **Web 框架**: Flask
- **Line Bot SDK**: line-bot-sdk
- **Google Sheets**: gspread + google-auth
- **環境變數**: python-dotenv
- **部署平台**: Zeabur

## 授權

MIT License