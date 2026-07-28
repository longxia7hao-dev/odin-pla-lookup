#!/bin/bash
# 一鍵嘗試開啟 Chrome「允許 Apple 事件的 JavaScript」
# 使用方式：在 Finder 雙擊此檔，或在終端機執行
set -e
cd "$(dirname "$0")/.."

echo "=========================================="
echo " 開啟 Chrome AppleScript JavaScript"
echo "=========================================="
echo ""
echo "Chrome 安全限制：此開關通常必須由你「親一下選單」才會真正生效。"
echo "腳本會幫你："
echo "  1) 啟動 Chrome"
echo "  2) 自動點：顯示方式 → 開發人員選項 → 允許 Apple 事件的 JavaScript"
echo "  3) 若跳出確認框，請你按「確定／好」"
echo ""
read -r -p "按 Enter 繼續..." _

open -a "Google Chrome"
sleep 2

osascript <<'APPLESCRIPT'
tell application "Google Chrome" to activate
delay 0.8
tell application "System Events"
  tell process "Google Chrome"
    set frontmost to true
    delay 0.3
    click menu item "允許 Apple 事件的 JavaScript" of menu "開發人員選項" of menu item "開發人員選項" of menu "顯示方式" of menu bar 1
  end tell
end tell
display dialog "若已出現黃色／系統確認框，請按「確定」或「好」。

完成後回到此對話框按「測試」。

（繁中 Chrome 路徑：顯示方式 → 開發人員選項 → 允許 Apple 事件的 JavaScript）" buttons {"測試"} default button 1
APPLESCRIPT

RESULT=$(osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  try
    set r to execute (active tab of front window) javascript "'OK-' & (2+2)"
    return r
  on error e
    return "FAIL: " & e
  end try
end tell
APPLESCRIPT
)

echo ""
echo "測試結果：$RESULT"
if [[ "$RESULT" == OK-* ]]; then
  echo "✅ 已成功開啟！可以叫 Grok 繼續用 Chrome 抓百度百科大圖。"
else
  echo "❌ 仍未開啟。請手動操作一次："
  echo "   Chrome 選單列 → 顯示方式 → 開發人員選項 → 允許 Apple 事件的 JavaScript"
  echo "   確認該項目左側出現 ✓ 打勾，並通過確認對話框。"
  echo "   完成後再執行本腳本測試，或直接回訊息給 Grok。"
fi
echo ""
read -r -p "按 Enter 關閉..." _
