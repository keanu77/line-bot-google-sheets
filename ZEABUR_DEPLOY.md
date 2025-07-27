# 🚀 Zeabur 部署指南

## 準備工作

### 1. Google 服務帳戶設定
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立專案並啟用 Google Sheets API
3. 建立服務帳戶並下載 JSON 金鑰
4. 複製完整的 JSON 內容（整個檔案內容）

### 2. Line Bot 設定
1. 前往 [Line Developers Console](https://developers.line.biz/console/)
2. 建立 Messaging API Channel
3. 取得 Channel Secret 和 Channel Access Token

### 3. Google Sheets 權限
1. 開啟您的 Google Sheet: https://docs.google.com/spreadsheets/d/1UUpQm3SrLo3o5S4MgqdEHifVd2oapde7uuwSR2F1cFI/edit
2. 分享給服務帳戶的 email（在 JSON 中的 `client_email`）
3. 給予編輯權限

## 🌟 Zeabur 部署步驟

### 1. 上傳到 GitHub
```bash
# 初始化 Git（如果還沒有）
git init
git add .
git commit -m "Initial Line Bot commit"

# 推送到 GitHub
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. 在 Zeabur 建立專案
1. 登入 [Zeabur Dashboard](https://dash.zeabur.com/)
2. 點擊 "New Project"
3. 選擇 "Deploy from GitHub"
4. 選擇您的儲存庫

### 3. 設定環境變數
在 Zeabur 專案設定中加入以下環境變數：

| 變數名稱 | 值 | 說明 |
|---------|----|----|
| `LINE_CHANNEL_SECRET` | `您的Line Channel Secret` | Line Bot 通道密鑰 |
| `LINE_CHANNEL_ACCESS_TOKEN` | `您的Line Channel Access Token` | Line Bot 存取權杖 |
| `GOOGLE_SHEETS_CREDENTIALS` | `完整的服務帳戶JSON字串` | Google 服務帳戶憑證 |
| `GOOGLE_SHEET_ID` | `1UUpQm3SrLo3o5S4MgqdEHifVd2oapde7uuwSR2F1cFI` | 已設定 |
| `GOOGLE_SHEET_NAME` | `Sheet1` | 工作表名稱 |

**重要**: `GOOGLE_SHEETS_CREDENTIALS` 需要是完整的 JSON 字串，格式如下：
```json
{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"your-service@your-project.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}
```

### 4. 部署
1. Zeabur 會自動偵測到您的 Python 專案
2. 等待部署完成
3. 記錄您的應用程式 URL（例如：`https://your-app.zeabur.app`）

### 5. 設定 Line Bot Webhook
1. 回到 Line Developers Console
2. 在您的 Channel 設定中找到 "Webhook settings"
3. 設定 Webhook URL: `https://your-app.zeabur.app/callback`
4. 開啟 "Use webhook"

### 6. 測試
1. 用手機加入您的 Line Bot 好友
2. 發送文字訊息測試
3. 檢查 Google Sheets 是否有新增資料

## 🔍 除錯

### 檢查部署狀態
- 在 Zeabur Dashboard 查看部署日誌
- 確認所有環境變數都已正確設定

### 測試健康檢查
訪問：`https://your-app.zeabur.app/health`
應該返回：`{"status": "healthy", "timestamp": "..."}`

### 常見問題
1. **Google Sheets 寫入失敗**: 檢查服務帳戶是否有 Sheet 編輯權限
2. **Line Bot 無回應**: 檢查 Webhook URL 是否正確設定
3. **環境變數錯誤**: 確認 JSON 格式正確，沒有多餘的空格或換行

## 📱 使用方式
- 加入 Line Bot 好友
- 發送任何文字訊息
- Bot 會回覆確認並將訊息記錄到 Google Sheets
- 非文字訊息會收到提示訊息

---

🎉 完成！您的 Line Bot 現在已經在 Zeabur 上運行並連接到 Google Sheets！