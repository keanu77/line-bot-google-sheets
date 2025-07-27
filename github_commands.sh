#!/bin/bash
# GitHub 上傳命令
# 請將 YOUR_REPO_URL 替換為您剛建立的 GitHub 儲存庫 URL

echo "正在設定遠端儲存庫..."
git remote add origin https://github.com/keanu77/line-bot-google-sheets.git

echo "正在推送到 GitHub..."
git branch -M main
git push -u origin main

echo "✅ 上傳完成！"
echo "GitHub 儲存庫: https://github.com/keanu77/line-bot-google-sheets"