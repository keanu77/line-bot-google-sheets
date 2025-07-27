# Zeabur 環境變數設定

## 請直接複製以下環境變數到 Zeabur：

### Line Bot 設定
```
LINE_CHANNEL_SECRET=你的LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_CHANNEL_ACCESS_TOKEN
```

### Google Sheets 設定
```
GOOGLE_SHEET_ID=1UUpQm3SrLo3o5S4MgqdEHifVd2oapde7uuwSR2F1cFI
GOOGLE_SHEET_NAME=Sheet1
```

### Google 服務帳戶認證（使用個別變數方式）
**請將你的 Google 服務帳戶 JSON 檔案中的對應值填入：**

```
GOOGLE_PROJECT_ID=你的project_id
GOOGLE_PRIVATE_KEY=你的private_key（完整的RSA私鑰，包含-----BEGIN PRIVATE KEY-----和-----END PRIVATE KEY-----）
GOOGLE_CLIENT_EMAIL=你的client_email
GOOGLE_PRIVATE_KEY_ID=你的private_key_id
GOOGLE_CLIENT_ID=你的client_id
```

## 設定說明：

1. **LINE_CHANNEL_SECRET** 和 **LINE_CHANNEL_ACCESS_TOKEN**：從 Line Developer Console 取得
2. **GOOGLE_PROJECT_ID**：你的 Google Cloud 專案 ID
3. **GOOGLE_PRIVATE_KEY**：完整的 RSA 私鑰，必須包含換行符號
4. **GOOGLE_CLIENT_EMAIL**：服務帳戶的 email 地址
5. **GOOGLE_PRIVATE_KEY_ID** 和 **GOOGLE_CLIENT_ID**：從服務帳戶 JSON 中取得

## 重要提醒：
- GOOGLE_PRIVATE_KEY 必須包含完整的 RSA 私鑰內容
- 如果私鑰中有 \n，系統會自動轉換為實際的換行符號
- 這種方式避免了 JSON 字串過長被截斷的問題

## 設定完成後：
1. 部署應用程式
2. 設定 Line Bot Webhook URL：`https://你的zeabur域名.zeabur.app/callback`
3. 測試功能是否正常