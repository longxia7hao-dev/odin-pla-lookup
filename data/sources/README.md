# 美方權威來源（本專案核對用）

| 檔案／連結 | 說明 |
|-----------|------|
| `cmpr2025.pdf` / `cmpr2025.txt` | 美國國防部 *Military and Security Developments Involving the PRC 2025*（China Military Power Report） |
| `fas-china-2024.pdf` | FAS *Chinese nuclear weapons, 2024*（CSS-x NATO 編號表） |
| [ODIN WEG](https://odin.t2com.army.mil/WEG) | 美陸軍 OE Data Integration Network · Worldwide Equipment Guide（訓練用裝備指南） |
| 美軍艦級公開命名 | Renhai / Luyang / Jiangkai / Yuan / Jin / Shang / Song / Ming 等 |

## 核對原則

1. **裝備形式**（SRBM/MRBM/IRBM/ICBM、DDG、LHD、IFV…）以 DoD 表列分類或美軍慣用語為準。  
2. **射程**優先採用 DoD 報告表格區間，並標註來源。  
3. **NATO/美方型號**（CSS-5、CSS-18、CSS-N-20…）以 FAS 等據美方資料整理為準。  
4. 未核對條目介面標示「待核對」，避免誤當已驗證情報。

重新套用核對：

```bash
python3 tools/apply_us_authority.py
```
