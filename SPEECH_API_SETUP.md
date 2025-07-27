# Google Speech-to-Text API 設定指南

## 錯誤解決：401 Authentication Error

如果你遇到 "401 Request had invalid authentication credentials" 錯誤，請按照以下步驟操作：

### 步驟 1：啟用 Speech-to-Text API

1. **前往 Google Cloud Console**：https://console.cloud.google.com/
2. **選擇你的專案** `my-ai-linenote`
3. **啟用 Speech-to-Text API**：
   - 點擊左側選單「API 和服務」→「程式庫」
   - 搜尋 "Cloud Speech-to-Text API"
   - 點擊「Cloud Speech-to-Text API」
   - 點擊「啟用」按鈕

### 步驟 2：確認服務帳戶權限

1. **前往 IAM 頁面**：https://console.cloud.google.com/iam-admin/iam
2. **找到你的服務帳戶**：`ethanwu@my-ai-linenote.iam.gserviceaccount.com`
3. **確認有以下角色**：
   - Cloud Speech Client
   - 或者 Editor（完整權限）

### 步驟 3：檢查 Zeabur 環境變數

確認以下環境變數已正確設定：

```
GOOGLE_PROJECT_ID=my-ai-linenote
GOOGLE_PRIVATE_KEY=你的完整私鑰
GOOGLE_CLIENT_EMAIL=ethanwu@my-ai-linenote.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY_ID=af240e019fb843c49a87f5a3f2f13f3a16514fa9
GOOGLE_CLIENT_ID=108275098064132556022
DISABLE_DRIVE_UPLOAD=true
```

### 步驟 4：重新部署

1. 確認所有 API 都已啟用
2. 在 Zeabur 重新部署應用程式
3. 測試語音訊息功能

## 支援的語言

- **主要語言**：繁體中文 (zh-TW)
- **備用語言**：英文 (en-US)、簡體中文 (zh-CN)

## 支援的音頻格式

Line Bot 會自動嘗試以下格式：
- WEBM_OPUS
- OGG_OPUS  
- LINEAR16
- MP3

## 測試建議

- 錄製清晰的語音（避免背景噪音）
- 語音長度建議 1-30 秒
- 說話速度適中
- 發音清楚

## 故障排除

如果語音轉換仍然失敗，請檢查：
1. Google Cloud Console 中是否所有必要的 API 都已啟用
2. 服務帳戶是否有正確的權限
3. Zeabur 環境變數是否完整設定
4. 語音品質是否清晰