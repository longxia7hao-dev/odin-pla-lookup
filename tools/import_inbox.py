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

    # 收件匣中「檔名對不上」的圖 → 產生縮圖總覽供人工辨識對應
    if skipped and "--sheet" in sys.argv:
        from PIL import ImageDraw
        files = [INBOX / n for n in skipped]
        COLS, CW, CH, LBL = 5, 260, 200, 30
        rows = (len(files) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * CW, rows * (CH + LBL)), (20, 20, 24))
        d = ImageDraw.Draw(sheet)
        for i, p in enumerate(files):
            r, c = divmod(i, COLS)
            x, y = c * CW, r * (CH + LBL)
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((CW - 8, CH - 8))
                sheet.paste(im, (x + (CW - im.width) // 2, y + (CH - im.height) // 2))
            except Exception:
                d.text((x + 10, y + CH // 2), "[ERR]", fill=(255, 80, 80))
            d.rectangle([x, y, x + CW - 1, y + CH + LBL - 1], outline=(70, 70, 80))
            d.text((x + 5, y + CH + 8), f"{i+1}. {p.name[:30]}", fill=(255, 255, 120))
        out_sheet = ROOT / "圖片收件匣" / "_待辨識總覽.png"
        sheet.save(out_sheet)
        print(f"\n未命名圖片 {len(files)} 張 → 縮圖總覽：{out_sheet}")
        print("（請 Claude 看過後以 --map id1,id2,... 依序對應）")
        return

    # 依序把未命名圖片對應到指定 id：--map type-032,type-052d,...
    if "--map" in sys.argv and skipped:
        ids_arg = sys.argv[sys.argv.index("--map") + 1].split(",")
        files = [INBOX / n for n in skipped]
        for p, eid in zip(files, ids_arg):
            eid = eid.strip()
            if eid and eid in ids:
                found.append((p, eid))
        print(f"依 --map 對應 {len(found)} 張")

    if not found:
        print("沒有找到可匯入的圖片。")
        print(f"請把檔案放到：{INBOX}")
        print("（檔名為裝備 id 最方便，如 type-052d.jpg；用網站的「儲存／分享給編者」會自動命名好）")
        if skipped:
            print(f"\n收件匣中檔名對不上的 {len(skipped)} 張：", ", ".join(skipped[:8]))
            print("→ 執行 `python3 tools/import_inbox.py --sheet` 產生縮圖總覽，讓 Claude 辨識對應")
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
