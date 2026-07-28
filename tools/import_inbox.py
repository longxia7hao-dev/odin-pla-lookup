#!/usr/bin/env python3
"""收圖工具：掃描下載/桌面/收件匣資料夾，找出檔名＝裝備 id 的圖片並匯入。

用法：
  python3 tools/import_inbox.py            # 掃描並匯入（會先驗證）
  python3 tools/import_inbox.py --dry-run  # 只列出找到什麼，不動任何檔案

搭配網站「儲存／分享給編者」使用：檔名已自動是裝備 id（如 type-052d.jpg），
從手機 AirDrop 到 Mac 後直接跑這支即可。
"""
import json, shutil, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "assets" / "images"
INBOX = ROOT / "圖片收件匣"          # 專用收件匣（自動建立）
SCAN_DIRS = [INBOX, Path.home() / "Downloads", Path.home() / "Desktop"]
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".HEIC"}
MAXPX = 1400
DRY = "--dry-run" in sys.argv


def valid_ids():
    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    arr = json.loads(t[t.index("["):t.rindex("]") + 1])
    return {x["id"]: x for x in arr}


def main():
    INBOX.mkdir(exist_ok=True)
    ids = valid_ids()
    found, skipped = [], []

    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.suffix not in EXTS:
                continue
            stem = p.stem.strip().lower()
            # 允許「type-052d」「type-052d (1)」「type-052d-2」等變形
            base = stem.split(" (")[0].split("(")[0].strip()
            for cand in (base, base.rsplit("-", 1)[0]):
                if cand in ids:
                    found.append((p, cand))
                    break
            else:
                if d == INBOX:
                    skipped.append(p.name)

    if not found:
        print("沒有找到可匯入的圖片。")
        print(f"請把檔案放到：{INBOX}")
        print("（檔名需為裝備 id，例如 type-052d.jpg；用網站的「儲存／分享給編者」就會自動命名好）")
        if skipped:
            print("\n收件匣中檔名對不上的：", ", ".join(skipped[:10]))
        return

    print(f"找到 {len(found)} 張可匯入：")
    staged = {}
    for p, eid in found:
        try:
            im = Image.open(p)
            im.verify()
            im = Image.open(p)
            w, h = im.size
        except Exception as e:
            print(f"  ✗ {p.name}：不是有效圖片（{str(e)[:30]}）")
            continue
        print(f"  ✓ {p.name} → {eid}（{w}×{h}，{ids[eid]['name_zh']}）")
        staged[eid] = p

    if DRY:
        print("\n[--dry-run] 未實際匯入。")
        return

    # 壓縮並寫入 assets/images
    out = ROOT / "data" / "inbox_imported.json"
    log = json.loads(out.read_text()) if out.exists() else {}
    for eid, p in staged.items():
        im = Image.open(p)
        if im.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", im.size, (16, 16, 20))
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if max(im.size) > MAXPX:
            im.thumbnail((MAXPX, MAXPX))
        dest = IMG_DIR / f"{eid}.jpg"
        im.save(dest, "JPEG", quality=88, optimize=True)
        log[eid] = {"path": f"assets/images/{eid}.jpg", "from": p.name, "source": "使用者提供"}
        # 原檔移入收件匣的 已匯入 子資料夾，避免重複處理
        done_dir = INBOX / "已匯入"
        done_dir.mkdir(exist_ok=True)
        try:
            shutil.move(str(p), str(done_dir / p.name))
        except Exception:
            pass
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    # 寫入精修層
    ep = ROOT / "data" / "specs_enrichment.json"
    d = json.loads(ep.read_text(encoding="utf-8"))
    for eid in staged:
        d["items"].setdefault(eid, {})["image"] = f"assets/images/{eid}.jpg"
    ep.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n已匯入 {len(staged)} 張並寫入精修層。")
    print("接著執行：python3 tools/apply_us_authority.py 然後 git push")


if __name__ == "__main__":
    main()
