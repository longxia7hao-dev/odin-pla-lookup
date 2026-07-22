(() => {
  "use strict";

  const CATEGORY_LABELS = {
    weapon: "武器",
    equipment: "裝備",
    vehicle: "載具",
  };

  const SUBCATEGORY_LABELS = {
    assault_rifle: "突擊步槍",
    dmr: "精確射手步槍",
    amr: "反器材步槍",
    mg: "通用機槍",
    hmg: "重機槍",
    agl: "自動榴彈",
    at_rocket: "反裝甲火箭",
    atgm: "反戰車飛彈",
    manpads: "便攜防空飛彈",
    pistol: "手槍",
    smg: "衝鋒槍",
    mortar: "迫擊砲",
    mortar_sp: "自行迫擊砲",
    mbt: "主戰坦克",
    light_tank: "輕型坦克",
    ifv: "步兵戰車",
    apc_wheeled: "輪式裝甲",
    assault_gun: "突擊車",
    sph: "自走砲",
    truck_howitzer: "車載加榴砲",
    mlrs: "多管火箭",
    sam: "防空飛彈系統",
    spaag: "自行高砲",
    aircraft_fighter: "戰鬥機",
    aircraft_strike: "戰鬥轟炸機",
    aircraft_bomber: "轟炸機",
    aircraft_transport: "運輸機",
    aircraft_aew: "預警機",
    helicopter: "通用直升機",
    helicopter_attack: "攻擊直升機",
    uav: "無人機",
    warship: "水面艦艇",
    submarine: "潛艦",
    light_vehicle: "輕型車輛",
    individual: "單兵裝備",
    asm: "反艦飛彈",
    aam: "空對空飛彈",
    ballistic: "彈道飛彈",
    cruise: "巡航飛彈",
    torpedo: "魚雷",
    ciws: "近防系統",
    aircraft_patrol: "巡邏／反潛機",
    aircraft_trainer: "教練機",
    apc_tracked: "履帶裝甲輸送車",
    artillery_towed: "牽引火砲",
    engineer: "工兵載具",
    bomb: "航空炸彈",
  };

  const state = {
    items: [],
    category: "all",
    branch: "all",
    query: "",
    sort: "name",
    selectedId: null,
  };

  const els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function normalize(str) {
    return String(str || "")
      .toLowerCase()
      .normalize("NFKC")
      .replace(/\s+/g, "");
  }

  function loadBaseData() {
    const base = Array.isArray(window.EQUIPMENT_DATA) ? window.EQUIPMENT_DATA : [];
    let custom = [];
    try {
      const raw = localStorage.getItem("odin_pla_custom_items");
      if (raw) custom = JSON.parse(raw);
    } catch (_) {
      custom = [];
    }
    if (!Array.isArray(custom)) custom = [];

    const map = new Map();
    [...base, ...custom].forEach((item) => {
      if (!item || !item.id) return;
      map.set(item.id, normalizeItem(item));
    });
    state.items = Array.from(map.values());
  }

  function normalizeItem(item) {
    return {
      id: String(item.id),
      name_en: item.name_en || item.name || "",
      name_zh: item.name_zh || item.name_tw || item.name || item.name_en || "",
      designation: item.designation || item.id || "",
      aliases: Array.isArray(item.aliases) ? item.aliases : [],
      category: ["weapon", "equipment", "vehicle"].includes(item.category)
        ? item.category
        : "equipment",
      subcategory: item.subcategory || "",
      origin: item.origin || "",
      origin_zh: item.origin_zh || "",
      service: item.service || "",
      service_zh: item.service_zh || "",
      caliber: item.caliber || "—",
      crew: item.crew || "—",
      weight_kg: item.weight_kg || "—",
      length_mm: item.length_mm || "—",
      range_m: item.range_m || "—",
      rate_of_fire: item.rate_of_fire || "—",
      capacity: item.capacity || "—",
      armor: item.armor || "—",
      mobility: item.mobility || "—",
      sensors: item.sensors || "—",
      notes_en: item.notes_en || "",
      notes_zh: item.notes_zh || item.notes || "",
      tags: Array.isArray(item.tags) ? item.tags : [],
      odin_hint: item.odin_hint || "",
      odin_url: item.odin_url || "",
      image: item.image || item.image_url || item.photo || "",
      image_remote: item.image_remote || "",
      wiki: item.wiki || "",
      source: item.source || "built-in",
      us_designation: item.us_designation || "",
      dod_class: item.dod_class || "",
      form_zh: item.form_zh || "",
      form_en: item.form_en || "",
      source_authority: Array.isArray(item.source_authority) ? item.source_authority : [],
      source_tier: item.source_tier || "open_unverified",
      authority_verified: !!item.authority_verified,
      branch: item.branch || "",
      sources: Array.isArray(item.sources) ? item.sources : [],
      data_status: item.data_status || "",
    };
  }

  function placeholderSvg(item) {
    const colors = {
      weapon: "#ef6b6b",
      equipment: "#6bcb8f",
      vehicle: "#f0b429",
    };
    const c = colors[item.category] || "#3d9cfd";
    const label = encodeURIComponent((item.designation || item.name_zh || "?").slice(0, 12));
    return (
      "data:image/svg+xml," +
      encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">
          <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#121a2b"/><stop offset="100%" stop-color="#1c2a42"/>
          </linearGradient></defs>
          <rect width="640" height="400" fill="url(#g)"/>
          <rect x="24" y="24" width="592" height="352" rx="16" fill="none" stroke="${c}" stroke-opacity="0.35" stroke-width="2"/>
          <circle cx="320" cy="170" r="48" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="2"/>
          <text x="320" y="178" text-anchor="middle" fill="${c}" font-family="sans-serif" font-size="22" font-weight="700">PLA</text>
          <text x="320" y="270" text-anchor="middle" fill="#9aadc8" font-family="sans-serif" font-size="20">${label}</text>
          <text x="320" y="304" text-anchor="middle" fill="#6d829f" font-family="sans-serif" font-size="14">暫無公開照片</text>
        </svg>`
      )
    );
  }

  function resolveImageSrc(item) {
    const img = item.image || "";
    if (!img) return "";
    // 本機 assets 路徑
    if (img.startsWith("assets/") || img.startsWith("./assets/")) return img;
    // 遠端 Wikimedia 等
    if (img.startsWith("http://") || img.startsWith("https://")) return img;
    return img;
  }

  function imgHtml(item, cls) {
    const fallback = placeholderSvg(item);
    const src = resolveImageSrc(item) || fallback;
    const alt = escapeAttr(item.name_zh || item.name_en || item.designation);
    const remote = item.image_remote || "";
    // 本機 assets 優先；失敗再試 remote；最後占位圖（勿加 crossorigin，否則本機／部分 CDN 會整批失敗）
    return `<img class="${cls}" src="${escapeAttr(src)}" alt="${alt}" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fallback="${escapeAttr(fallback)}" data-remote="${escapeAttr(remote)}" onerror="if(this.dataset.remote&&!this.dataset.triedRemote){this.dataset.triedRemote=1;this.referrerPolicy='no-referrer';this.src=this.dataset.remote;return;}if(!this.dataset.err){this.dataset.err=1;this.src=this.dataset.fallback;}" />`;
  }

  function searchScore(item, q) {
    if (!q) return 1;
    const nq = normalize(q);
    const fields = [
      [item.designation, 12],
      [item.us_designation, 12],
      [item.name_zh, 10],
      [item.name_en, 8],
      [item.form_zh, 8],
      [item.dod_class, 7],
      [item.aliases.join(" "), 7],
      [item.tags.join(" "), 5],
      [item.caliber, 4],
      [item.subcategory, 3],
      [item.notes_zh, 2],
      [item.notes_en, 1],
      [item.service_zh, 2],
      [item.odin_hint, 2],
      [(item.source_authority || []).join(" "), 2],
    ];

    let score = 0;
    for (const [field, weight] of fields) {
      const nf = normalize(field);
      if (!nf) continue;
      if (nf === nq) score += weight * 3;
      else if (nf.startsWith(nq)) score += weight * 2;
      else if (nf.includes(nq)) score += weight;
    }

    // 多關鍵字 AND
    const tokens = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (tokens.length > 1) {
      const hay = normalize(
        [
          item.designation,
          item.name_zh,
          item.name_en,
          item.aliases.join(" "),
          item.tags.join(" "),
          item.caliber,
          item.notes_zh,
        ].join(" ")
      );
      if (tokens.every((t) => hay.includes(normalize(t)))) score += 5;
      else return 0;
    }

    return score;
  }

  function getFiltered() {
    let list = state.items.filter((item) => {
      if (state.category !== "all" && item.category !== state.category) return false;
      if (state.branch !== "all" && (item.branch || "陸軍") !== state.branch) return false;
      if (!state.query.trim()) return true;
      return searchScore(item, state.query) > 0;
    });

    if (state.query.trim()) {
      list = list
        .map((item) => ({ item, score: searchScore(item, state.query) }))
        .sort((a, b) => b.score - a.score || a.item.name_zh.localeCompare(b.item.name_zh, "zh-Hant"))
        .map((x) => x.item);
    } else {
      list = sortList(list);
    }
    return list;
  }

  function sortList(list) {
    const copy = [...list];
    switch (state.sort) {
      case "category":
        copy.sort((a, b) =>
          a.category.localeCompare(b.category) ||
          a.name_zh.localeCompare(b.name_zh, "zh-Hant")
        );
        break;
      case "designation":
        copy.sort((a, b) =>
          String(a.designation).localeCompare(String(b.designation), "en", { numeric: true })
        );
        break;
      case "name":
      default:
        copy.sort((a, b) => a.name_zh.localeCompare(b.name_zh, "zh-Hant"));
    }
    return copy;
  }

  function renderResults() {
    const list = getFiltered();
    els.resultCount.textContent = `共 ${list.length} 筆`;
    els.totalCount.textContent = String(state.items.length);

    if (!list.length) {
      els.results.innerHTML = `
        <div class="empty">
          <strong>找不到符合的項目</strong>
          試試型號（如 99A、QBZ-191）、中文關鍵字，或切換分類篩選。
        </div>`;
      return;
    }

    els.results.innerHTML = list
      .map((item) => {
        const active = item.id === state.selectedId ? "active" : "";
        const sub = SUBCATEGORY_LABELS[item.subcategory] || item.subcategory || "";
        const tags = (item.tags || [])
          .slice(0, 4)
          .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
          .join("");
        return `
          <button type="button" class="card ${active}" data-id="${escapeAttr(item.id)}">
            <div class="card-thumb-wrap">
              ${imgHtml(item, "card-thumb")}
              <span class="cat-dot ${item.category}"></span>
            </div>
            <div class="card-body">
              <h3>${escapeHtml(item.name_zh)}</h3>
              <div class="en">${escapeHtml(item.name_en)}</div>
              <div class="card-meta">
                <span>${escapeHtml(item.form_zh || sub || CATEGORY_LABELS[item.category])}</span>
                <span>${escapeHtml(item.caliber || "—")}</span>
                <span>${escapeHtml(item.service_zh || item.service || "")}</span>
              </div>
              <div class="tag-list">${
                item.branch
                  ? `<span class="tag branch-tag branch-${escapeAttr(item.branch)}">${escapeHtml(item.branch)}</span>`
                  : ""
              }${tags}${
                item.authority_verified
                  ? '<span class="tag tag-auth">美方核對</span>'
                  : '<span class="tag tag-open">待核對</span>'
              }${
                item.data_status
                  ? `<span class="tag tag-pending-collect">${escapeHtml(item.data_status)}</span>`
                  : ""
              }</div>
            </div>
            <div class="card-side">
              <span class="cat-label ${item.category}">${CATEGORY_LABELS[item.category]}</span>
              <span class="desig">${escapeHtml(item.us_designation || item.designation)}</span>
            </div>
          </button>`;
      })
      .join("");
  }

  function renderDetail(item) {
    if (!item) {
      els.detail.innerHTML = `
        <div class="detail-empty">
          <p>從左側清單選擇一筆裝備，查看規格與說明。</p>
          <span class="hint-key">快捷鍵 / 聚焦搜尋</span>
        </div>`;
      return;
    }

    const sub = SUBCATEGORY_LABELS[item.subcategory] || item.subcategory || "—";
    const formZh = item.form_zh || sub || CATEGORY_LABELS[item.category];
    const aliases = (item.aliases || [])
      .map((a) => `<span>${escapeHtml(a)}</span>`)
      .join("") || "<span>—</span>";

    const authBadge = item.authority_verified
      ? `<span class="auth-badge ok">美方權威核對</span>`
      : `<span class="auth-badge pending">公開來源 · 待美方核對</span>`;

    const sources =
      (item.source_authority || [])
        .map((s) => `<span>${escapeHtml(s)}</span>`)
        .join("") || "<span>—</span>";

    const tierLabel =
      item.source_tier === "US_DoD"
        ? "美國國防部公開報告（高）"
        : item.source_tier === "US_open"
          ? "美方公開軍事文獻（中）"
          : "一般公開來源（待核對）";

    const safeUrl = (u) => (typeof u === "string" && /^https?:\/\//i.test(u) ? u : "");
    const citeBlock =
      item.sources && item.sources.length
        ? item.sources
            .map((s) => {
              const url = safeUrl(s && s.url);
              const label = escapeHtml((s && (s.label || s.title)) || url || "來源");
              return url
                ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${label}</a>`
                : `<span>${label}</span>`;
            })
            .join("")
        : '<span class="muted">尚未附引用連結（諸元精修批次會逐筆補上）</span>';

    const specs = [
      ["軍種", item.branch || "—"],
      ["裝備形式（中）", formZh],
      ["裝備形式（英）", item.form_en || "—"],
      ["美方／NATO 型號", item.us_designation || "—"],
      ["DoD／美軍分類", item.dod_class || "—"],
      ["口徑／主武器", item.caliber],
      ["乘員／操作", item.crew],
      ["重量", formatWeight(item.weight_kg)],
      ["長度", formatLength(item.length_mm)],
      ["射程／距離", item.range_m],
      ["射速", item.rate_of_fire],
      ["彈藥／載量", item.capacity],
      ["防護", item.armor],
      ["機動", item.mobility],
      ["感測／觀瞄", item.sensors],
      ["來源國", item.origin_zh || item.origin],
      ["服役單位", item.service_zh || item.service],
    ];

    const odinBlock = item.odin_url
      ? `<a href="${escapeAttr(item.odin_url)}" target="_blank" rel="noopener">ODIN WEG（美陸軍訓練裝備指南）</a>`
      : item.odin_hint
        ? `WEG 分類提示：${escapeHtml(item.odin_hint)}`
        : "可於匯入資料時填入 odin_url";

    const wikiLink = item.wiki
      ? `<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(item.wiki.replace(/ /g, "_"))}" target="_blank" rel="noopener">維基百科</a>`
      : "";

    els.detail.innerHTML = `
      <div class="detail-photo">
        ${imgHtml(item, "detail-img")}
      </div>
      <div class="detail-header">
        <span class="cat-label ${item.category}">${CATEGORY_LABELS[item.category]} · ${escapeHtml(formZh)}</span>
        ${item.branch ? `<span class="branch-badge branch-${escapeAttr(item.branch)}">${escapeHtml(item.branch)}</span>` : ""}
        ${authBadge}
        ${item.data_status ? `<span class="auth-badge pending-collect">${escapeHtml(item.data_status)}｜資料尚待權威來源核實</span>` : ""}
        <h2>${escapeHtml(item.name_zh)}</h2>
        <div class="en">${escapeHtml(item.name_en)}</div>
        <div class="desig-lg">${escapeHtml(item.designation)}</div>
        ${item.us_designation ? `<div class="us-desig">美方：${escapeHtml(item.us_designation)}</div>` : ""}
      </div>
      <div class="detail-section">
        <h4>規格參數（裝備形式優先 · ODIN／DoD 語彙）</h4>
        <div class="spec-grid">
          ${specs
            .map(
              ([label, value]) => `
            <div class="spec-item">
              <span class="label">${escapeHtml(label)}</span>
              <span class="value">${escapeHtml(value || "—")}</span>
            </div>`
            )
            .join("")}
        </div>
      </div>
      <div class="detail-section">
        <h4>說明（含美方報告語境）</h4>
        <div class="notes">
          <div>${escapeHtml(item.notes_zh || "—")}</div>
          ${item.notes_en ? `<div class="en-note">${escapeHtml(item.notes_en)}</div>` : ""}
        </div>
      </div>
      <div class="detail-section">
        <h4>權威來源</h4>
        <div class="alias-list source-list">${sources}</div>
        <div class="odin-link" style="margin-top:10px">核對層級：<strong>${escapeHtml(tierLabel)}</strong></div>
      </div>
      <div class="detail-section">
        <h4>資料出處（引用）</h4>
        <div class="alias-list source-list cite-list">${citeBlock}</div>
      </div>
      <div class="detail-section">
        <h4>別名／關鍵字</h4>
        <div class="alias-list">${aliases}</div>
      </div>
      <div class="detail-section">
        <h4>ODIN／延伸</h4>
        <div class="odin-link">${odinBlock}</div>
        ${wikiLink ? `<div class="odin-link" style="margin-top:8px">百科參考：${wikiLink}</div>` : ""}
        <div class="odin-link" style="margin-top:8px">正式訓練與引用請以 DoD CMPR、ODIN WEG 原文為準。</div>
      </div>
    `;
  }

  function formatWeight(v) {
    if (!v || v === "—") return "—";
    const s = String(v);
    if (/噸|kg|噸級|約/.test(s)) return s;
    const n = Number(s);
    if (!Number.isNaN(n) && n >= 1000) return `${s} kg（約 ${(n / 1000).toFixed(1)} 噸）`;
    if (!Number.isNaN(n)) return `${s} kg`;
    return s;
  }

  function formatLength(v) {
    if (!v || v === "—") return "—";
    const s = String(v);
    if (/mm|m|約/.test(s)) return s;
    const n = Number(s);
    if (!Number.isNaN(n) && n >= 1000) return `${s} mm（約 ${(n / 1000).toFixed(1)} m）`;
    if (!Number.isNaN(n)) return `${s} mm`;
    return s;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/'/g, "&#39;");
  }

  function selectItem(id) {
    state.selectedId = id;
    const item = state.items.find((x) => x.id === id) || null;
    renderResults();
    renderDetail(item);
  }

  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove("show"), 2200);
  }

  function openModal(id) {
    $(id).classList.add("open");
  }

  function closeModal(id) {
    $(id).classList.remove("open");
  }

  function exportJson() {
    const payload = {
      meta: {
        name: "ODIN PLA Lookup Export",
        exported_at: new Date().toISOString(),
        count: state.items.length,
        note: "公開資料整理＋自訂匯入，僅供訓練參考",
      },
      items: state.items,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pla-equipment-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("已匯出 JSON");
  }

  function importJsonText(text, mode) {
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      throw new Error("JSON 格式錯誤：" + e.message);
    }

    let items = [];
    if (Array.isArray(data)) items = data;
    else if (Array.isArray(data.items)) items = data.items;
    else if (data.id) items = [data];
    else throw new Error("找不到 items 陣列。請使用 { items: [...] } 或直接陣列。");

    if (!items.length) throw new Error("匯入資料為空");

    const normalized = items.map(normalizeItem).filter((x) => x.id && (x.name_zh || x.name_en));
    if (!normalized.length) throw new Error("沒有有效條目（需要 id 與名稱）");

    let custom = [];
    try {
      custom = JSON.parse(localStorage.getItem("odin_pla_custom_items") || "[]");
    } catch (_) {
      custom = [];
    }
    if (!Array.isArray(custom)) custom = [];

    if (mode === "replace") {
      custom = normalized.map((x) => ({ ...x, source: "import" }));
    } else {
      const map = new Map(custom.map((x) => [x.id, x]));
      normalized.forEach((x) => map.set(x.id, { ...x, source: "import" }));
      custom = Array.from(map.values());
    }

    localStorage.setItem("odin_pla_custom_items", JSON.stringify(custom));
    loadBaseData();
    renderResults();
    if (state.selectedId) {
      const still = state.items.find((x) => x.id === state.selectedId);
      renderDetail(still || null);
    }
    toast(`已匯入 ${normalized.length} 筆（模式：${mode === "replace" ? "覆蓋自訂" : "合併"}）`);
  }

  function clearCustom() {
    if (!confirm("確定清除所有「自訂／匯入」資料？內建範例不會刪除。")) return;
    localStorage.removeItem("odin_pla_custom_items");
    loadBaseData();
    state.selectedId = null;
    renderResults();
    renderDetail(null);
    toast("已清除自訂資料");
  }

  function bindEvents() {
    els.searchInput.addEventListener("input", (e) => {
      state.query = e.target.value;
      els.clearBtn.classList.toggle("visible", !!state.query);
      renderResults();
    });

    els.clearBtn.addEventListener("click", () => {
      state.query = "";
      els.searchInput.value = "";
      els.clearBtn.classList.remove("visible");
      els.searchInput.focus();
      renderResults();
    });

    els.filters.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip");
      if (!btn) return;
      state.category = btn.dataset.cat;
      els.filters.querySelectorAll(".chip").forEach((c) => {
        c.classList.toggle("active", c.dataset.cat === state.category);
      });
      renderResults();
    });

    if (els.branchFilters) {
      els.branchFilters.addEventListener("click", (e) => {
        const btn = e.target.closest(".chip");
        if (!btn) return;
        state.branch = btn.dataset.branch;
        els.branchFilters.querySelectorAll(".chip").forEach((c) => {
          c.classList.toggle("active", c.dataset.branch === state.branch);
        });
        renderResults();
      });
    }

    els.sortSelect.addEventListener("change", (e) => {
      state.sort = e.target.value;
      renderResults();
    });

    els.results.addEventListener("click", (e) => {
      const card = e.target.closest(".card");
      if (!card) return;
      selectItem(card.dataset.id);
    });

    $("btnExport").addEventListener("click", exportJson);
    $("btnImport").addEventListener("click", () => openModal("importModal"));
    $("btnHelp").addEventListener("click", () => openModal("helpModal"));
    $("btnClearCustom").addEventListener("click", clearCustom);

    $("importConfirm").addEventListener("click", () => {
      const text = $("importText").value.trim();
      const mode = $("importMode").value;
      if (!text) {
        toast("請貼上 JSON 內容");
        return;
      }
      try {
        importJsonText(text, mode);
        closeModal("importModal");
        $("importText").value = "";
      } catch (err) {
        toast(err.message || "匯入失敗");
      }
    });

    $("importFile").addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const text = await file.text();
      $("importText").value = text;
      toast(`已載入檔案：${file.name}`);
    });

    document.querySelectorAll("[data-close]").forEach((btn) => {
      btn.addEventListener("click", () => closeModal(btn.dataset.close));
    });

    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) backdrop.classList.remove("open");
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== els.searchInput && !e.metaKey && !e.ctrlKey) {
        const tag = document.activeElement && document.activeElement.tagName;
        if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
          e.preventDefault();
          els.searchInput.focus();
          els.searchInput.select();
        }
      }
      if (e.key === "Escape") {
        document.querySelectorAll(".modal-backdrop.open").forEach((m) => m.classList.remove("open"));
      }
    });
  }

  function init() {
    els.searchInput = $("searchInput");
    els.clearBtn = $("clearBtn");
    els.filters = $("filters");
    els.branchFilters = $("branchFilters");
    els.results = $("results");
    els.detail = $("detail");
    els.resultCount = $("resultCount");
    els.totalCount = $("totalCount");
    els.sortSelect = $("sortSelect");
    els.toast = $("toast");

    loadBaseData();
    bindEvents();
    renderResults();
    renderDetail(null);

    // URL hash 深連結 #id
    if (location.hash) {
      const id = decodeURIComponent(location.hash.slice(1));
      if (state.items.some((x) => x.id === id)) selectItem(id);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
