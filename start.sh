#!/bin/zsh
# 啟動靜態伺服器（本機 + 區網手機可連）
cd "$(dirname "$0")"
PORT="${PORT:-8877}"
# 0.0.0.0 = 允許區網裝置連入；若只要本機請設 BIND=127.0.0.1
BIND="${BIND:-0.0.0.0}"

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="$(ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')"
fi

if command -v python3 >/dev/null 2>&1; then
  echo "→ 本機：  http://127.0.0.1:${PORT}/"
  if [[ -n "$LAN_IP" && "$BIND" != "127.0.0.1" ]]; then
    echo "→ 手機區網：http://${LAN_IP}:${PORT}/"
    echo "  （手機須與電腦同一 Wi‑Fi）"
  fi
  echo "→ 按 Ctrl+C 結束"
  (sleep 0.6 && open "http://127.0.0.1:${PORT}/") &
  python3 -m http.server "$PORT" --bind "$BIND"
else
  echo "找不到 python3，改為直接開啟 index.html（僅本機）"
  open "index.html"
fi
