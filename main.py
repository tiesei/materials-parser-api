<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materials</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --bg: #f0ede8;
    --surface: #faf9f7;
    --border: #ddd9d3;
    --text: #1a1a18;
    --text-muted: #888880;
    --accent: #2d5a3d;
    --accent-light: #e8f0eb;
    --in-stock: #2d5a3d;
    --in-stock-bg: #e8f0eb;
    --out: #8b3a2a;
    --out-bg: #f5ebe8;
    --sold: #7a5c1a;
    --sold-bg: #f5f0e0;
    --mono: 'DM Mono', monospace;
    --sans: 'DM Sans', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* NAV */
  nav {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    height: 48px;
    position: sticky;
    top: 0;
    z-index: 100;
    overflow: hidden;
  }

  .nav-brand {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    letter-spacing: 0.05em;
    text-decoration: none;
  }

  .nav-links { display: flex; gap: 0; }

  .nav-links a {
    font-size: 13px;
    color: var(--text-muted);
    text-decoration: none;
    padding: 0 0.6rem;
    height: 48px;
    display: flex;
    align-items: center;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .nav-links a:hover { color: var(--text); }
  .nav-links a.active { color: var(--text); border-bottom-color: var(--accent); }

  .nav-end { margin-left: auto; display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }

  /* MAIN */
  main { padding: 0.75rem; max-width: 100%; }

  /* ADD BAR */
  .add-bar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.6rem 0.75rem;
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .add-bar input {
    flex: 1;
    font-family: var(--mono);
    font-size: 13px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    color: var(--text);
    outline: none;
    transition: border-color 0.15s;
  }

  .add-bar input:focus { border-color: var(--accent); }
  .add-bar input::placeholder { color: var(--text-muted); }

  .btn {
    font-family: var(--sans);
    font-size: 13px;
    font-weight: 500;
    padding: 0.5rem 1.1rem;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
    white-space: nowrap;
  }

  .btn:active { transform: scale(0.97); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover:not(:disabled) { opacity: 0.88; }

  .btn-ghost {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
  }
  .btn-ghost:hover:not(:disabled) { background: var(--bg); color: var(--text); }

  /* STATUS */
  .status-bar {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-muted);
    padding: 0.4rem 0;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 24px;
  }

  .status-bar.loading { color: var(--accent); }
  .status-bar.error { color: var(--out); }

  .spinner {
    width: 12px; height: 12px;
    border: 1.5px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* TABLE WRAPPER */
  .table-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead { background: var(--bg); }

  th {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.5rem 0.6rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    background: var(--bg);
  }



  td {
    padding: 0.65rem 0.75rem;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
    font-size: 13px;
  }

  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f5f3ef; }

  /* THUMBNAIL */
  .thumb-cell { width: 80px; }

  .thumb {
    width: 72px;
    height: 72px;
    object-fit: cover;
    border-radius: 6px;
    display: block;
    cursor: zoom-in;
    transition: transform 0.2s, box-shadow 0.2s;
    background: var(--bg);
  }

  .thumb:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  }

  .thumb.expanded {
    width: 260px;
    height: 260px;
    cursor: zoom-out;
    position: relative;
    z-index: 10;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  }

  /* TYPE BADGE */
  .type-badge {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.05em;
    padding: 2px 7px;
    border-radius: 4px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text-muted);
    white-space: nowrap;
  }

  /* TITLE */
  .title-cell { min-width: 160px; max-width: 200px; }
  .title-text { font-weight: 500; font-size: 13px; line-height: 1.4; }
  .title-link {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--accent);
    text-decoration: none;
    display: inline-block;
    margin-top: 3px;
    opacity: 0.7;
  }
  .title-link:hover { opacity: 1; text-decoration: underline; }

  /* DESC */
  .desc-cell { min-width: 160px; max-width: 220px; color: var(--text-muted); font-size: 12px; line-height: 1.5; }

  /* NOTES */
  .notes-cell { width: 150px; }
  textarea.notes {
    font-family: var(--sans);
    font-size: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 5px 7px;
    width: 140px;
    height: 52px;
    resize: none;
    color: var(--text);
    outline: none;
    transition: border-color 0.15s;
    line-height: 1.4;
  }
  textarea.notes:focus { border-color: var(--accent); }

  /* COLORS */
  .colors-cell { width: 150px; }

  .color-select-wrap { position: relative; }

  select.color-select {
    font-family: var(--sans);
    font-size: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 4px 6px;
    width: 140px;
    color: var(--text);
    outline: none;
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888880' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 24px;
  }

  select.color-select:focus { border-color: var(--accent); }

  select.options-select {
    font-family: var(--sans);
    font-size: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 4px 6px;
    width: 140px;
    color: var(--text);
    outline: none;
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888880' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 24px;
    margin-top: 4px;
  }

  /* WEIGHT / PRICE */
  .mono-cell {
    font-family: var(--mono);
    font-size: 12px;
    white-space: nowrap;
    color: var(--text);
  }

  /* AVAILABILITY */
  .badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
  }
  .badge.in  { background: var(--in-stock-bg); color: var(--in-stock); }
  .badge.out { background: var(--out-bg); color: var(--out); }
  .badge.sold{ background: var(--sold-bg); color: var(--sold); }
  .badge.check{ background: var(--bg); color: var(--text-muted); border: 1px solid var(--border); }

  /* REPARSE BTN */
  .reparse-btn {
    font-size: 14px;
    background: none;
    border: 1px solid var(--border);
    border-radius: 5px;
    width: 28px;
    height: 28px;
    cursor: pointer;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, border-color 0.15s, transform 0.2s;
  }

  .reparse-btn:hover { color: var(--accent); border-color: var(--accent); }
  .reparse-btn.spinning { animation: spin 0.8s linear infinite; }

  /* EMPTY STATE */
  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
  }

  .empty-state p { font-size: 14px; margin-top: 0.5rem; }

  /* LOADING SKELETON */
  .skeleton {
    background: linear-gradient(90deg, var(--bg) 25%, var(--border) 50%, var(--bg) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.2s infinite;
    border-radius: 4px;
    height: 14px;
  }

  @keyframes shimmer { to { background-position: -200% 0; } }

  /* MOBILE */
  @media (max-width: 768px) {
    main { padding: 1rem; }
    .add-bar { flex-wrap: wrap; }
    .add-bar input { min-width: 0; }
    .desc-cell { display: none; }
    .thumb { width: 56px; height: 56px; }
  }
</style>
</head>
<body>

<nav>
  <span class="nav-brand">⬡ atelier</span>
  <div class="nav-links">
    <a href="index.html" class="active">Materials</a>
    <a href="products.html">Products</a>
    <a href="calculator.html">Calculator</a>
  </div>
  <div class="nav-end">
    <button class="btn btn-ghost" id="loginBtn" onclick="handleLogin()" style="font-size:11px;padding:3px 8px;white-space:nowrap;flex-shrink:0;">sign in</button>
  </div>
</nav>

<main>
  <div class="add-bar">
    <input type="url" id="urlInput" placeholder="Paste product URL from extremtextil.de or adventurexpert.com…" />
    <button class="btn btn-primary" id="addBtn" onclick="addMaterial()">Add material</button>
  </div>

  <div class="status-bar" id="statusBar"></div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Type</th>
          <th class="thumb-cell">Photo</th>
          <th class="title-cell">Title</th>
          <th class="desc-cell">Description</th>
          <th class="notes-cell">Notes</th>
          <th class="colors-cell">Colors / Options</th>
          <th>Weight</th>
          <th>Price</th>
          <th>Stock</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="tbody">
        <tr>
          <td colspan="10">
            <div class="empty-state">
              <div style="font-size:32px;margin-bottom:8px;">⬡</div>
              <p>No materials yet — paste a URL above to add one.</p>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</main>

<script>
const API = "https://materials-parser-api.onrender.com";

// ── STATUS ────────────────────────────────────────────────────────────────────
function setStatus(msg, type = "") {
  const bar = document.getElementById("statusBar");
  bar.className = "status-bar" + (type ? " " + type : "");
  bar.innerHTML = type === "loading"
    ? `<span class="spinner"></span> ${msg}`
    : msg;
}

function clearStatus() {
  document.getElementById("statusBar").innerHTML = "";
  document.getElementById("statusBar").className = "status-bar";
}

// ── AVAILABILITY BADGE ────────────────────────────────────────────────────────
function badge(av) {
  if (!av) return `<span class="badge check">—</span>`;
  const l = av.toLowerCase();
  if (l.includes("in stock"))  return `<span class="badge in">In stock</span>`;
  if (l.includes("sold"))      return `<span class="badge sold">Sold out</span>`;
  if (l.includes("out"))       return `<span class="badge out">Out of stock</span>`;
  return `<span class="badge check">${av}</span>`;
}

// ── RENDER ROW ────────────────────────────────────────────────────────────────
function renderRow(item, idx) {
  const colors = Array.isArray(item.colors) ? item.colors : [];
  const variants = Array.isArray(item.variants) ? item.variants : [];
  const firstImg = colors[0]?.image || "";
  const firstUrl = colors[0]?.url || item.url || "#";
  const savedNote = localStorage.getItem("note_" + (item.url || idx)) || "";

  const tr = document.createElement("tr");
  tr.dataset.url = item.url || "";

  // TYPE
  const tdType = document.createElement("td");
  tdType.innerHTML = `<span class="type-badge">${item.type || "—"}</span>`;

  // PHOTO
  const tdPhoto = document.createElement("td");
  tdPhoto.className = "thumb-cell";
  const img = document.createElement("img");
  img.className = "thumb";
  img.src = firstImg;
  img.alt = item.title || "";
  img.loading = "lazy";
  img.onclick = () => img.classList.toggle("expanded");
  tdPhoto.appendChild(img);

  // TITLE
  const tdTitle = document.createElement("td");
  tdTitle.className = "title-cell";
  tdTitle.innerHTML = `
    <div class="title-text">${item.title || "—"}</div>
    ${item.url ? `<a class="title-link" href="${item.url}" target="_blank">↗ open</a>` : ""}
  `;

  // DESC
  const tdDesc = document.createElement("td");
  tdDesc.className = "desc-cell";
  const desc = item.description || "";
  tdDesc.textContent = desc.length > 100 ? desc.slice(0, 100) + "…" : desc;

  // NOTES
  const tdNotes = document.createElement("td");
  tdNotes.className = "notes-cell";
  const ta = document.createElement("textarea");
  ta.className = "notes";
  ta.placeholder = "Add note…";
  ta.value = savedNote;
  ta.oninput = () => localStorage.setItem("note_" + (item.url || idx), ta.value);
  tdNotes.appendChild(ta);

  // COLORS + OPTIONS
  const tdColors = document.createElement("td");
  tdColors.className = "colors-cell";

  if (colors.length > 0) {
    const colorSel = document.createElement("select");
    colorSel.className = "color-select";
    colors.forEach((c, i) => {
      const opt = document.createElement("option");
      opt.value = i;
      const inStock = !c.availability || c.availability === "In stock";
      opt.textContent = (c.name || `Color ${i+1}`) + (inStock ? "" : " (out of stock)");
      if (!inStock) { opt.style.color = "#bbb"; }
      colorSel.appendChild(opt);
    });
    // Always select first color regardless of stock
    colorSel.value = 0;

    colorSel.onchange = () => {
      const c = colors[parseInt(colorSel.value)];
      if (c?.image) img.src = c.image;
      if (c?.price_per_unit) {
        const priceStr = c.price_per_unit.toFixed(2).replace(".", ",") + " EUR";
        const priceCell = colorSel.closest("tr")?.querySelector(".price-cell");
        if (priceCell) priceCell.textContent = priceStr;
      }
    };

    tdColors.appendChild(colorSel);

    // Options dropdown (variants from adventurexpert or multi-size items)
    if (variants.length > 0 && variants[0].options?.length > 0) {
      const optSel = document.createElement("select");
      optSel.className = "options-select";
      variants[0].options.forEach(o => {
        const opt = document.createElement("option");
        opt.value = o;
        opt.textContent = o;
        optSel.appendChild(opt);
      });
      tdColors.appendChild(optSel);
    }
  } else {
    tdColors.innerHTML = `<span style="color:var(--text-muted);font-size:12px;">—</span>`;
  }

  // WEIGHT
  const tdWeight = document.createElement("td");
  tdWeight.className = "mono-cell";
  tdWeight.textContent = item.weight || "—";

  // PRICE
  const tdPrice = document.createElement("td");
  tdPrice.className = "mono-cell";
  tdPrice.textContent = item.price || "—";

  // STOCK
  const tdStock = document.createElement("td");
  tdStock.innerHTML = badge(item.availability);

  // REPARSE
  const tdAction = document.createElement("td");
  const repBtn = document.createElement("button");
  repBtn.className = "reparse-btn";
  repBtn.title = "Refresh";
  repBtn.textContent = "↻";
  repBtn.onclick = () => reparseMaterial(item.url, tr, repBtn);
  tdAction.appendChild(repBtn);

  tr.appendChild(tdType);
  tr.appendChild(tdPhoto);
  tr.appendChild(tdTitle);
  tr.appendChild(tdDesc);
  tr.appendChild(tdNotes);
  tr.appendChild(tdColors);
  tr.appendChild(tdWeight);
  tr.appendChild(tdPrice);
  tr.appendChild(tdStock);
  tr.appendChild(tdAction);

  return tr;
}

// ── LOAD MATERIALS ────────────────────────────────────────────────────────────
async function loadMaterials() {
  setStatus("Loading…", "loading");
  try {
    const res = await fetch(`${API}/materials`);
    const data = await res.json();
    renderTable(data);
    clearStatus();
  } catch(e) {
    setStatus("Failed to load materials. API may be waking up — try again in 30s.", "error");
  }
}

function renderTable(data) {
  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";

  if (!data || data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10">
      <div class="empty-state">
        <div style="font-size:32px;margin-bottom:8px;">⬡</div>
        <p>No materials yet — paste a URL above to add one.</p>
      </div>
    </td></tr>`;
    return;
  }

  data.forEach((item, idx) => {
    tbody.appendChild(renderRow(item, idx));
  });
}

// ── ADD MATERIAL ──────────────────────────────────────────────────────────────
async function addMaterial() {
  const input = document.getElementById("urlInput");
  const url = input.value.trim();
  if (!url) return;

  const btn = document.getElementById("addBtn");
  btn.disabled = true;
  setStatus("Parsing… this may take 1–2 minutes for products with many colors.", "loading");

  try {
    const res = await fetch(`${API}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Parse failed");
    }

    const data = await res.json();
    input.value = "";

    // Reload full table to get updated order from Sheets
    await loadMaterials();
    setStatus(`✓ Added: ${data.title}`, "");
    setTimeout(clearStatus, 3000);

  } catch(e) {
    setStatus(`Error: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
  }
}

// ── REPARSE ───────────────────────────────────────────────────────────────────
async function reparseMaterial(url, tr, btn) {
  if (!url) return;
  btn.classList.add("spinning");
  btn.disabled = true;
  setStatus("Refreshing…", "loading");

  try {
    const res = await fetch(`${API}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    if (!res.ok) throw new Error("Reparse failed");
    await loadMaterials();
    setStatus("✓ Refreshed", "");
    setTimeout(clearStatus, 2000);
  } catch(e) {
    setStatus(`Error: ${e.message}`, "error");
    btn.classList.remove("spinning");
    btn.disabled = false;
  }
}

// ── LOGIN (placeholder for Google OAuth) ──────────────────────────────────────
function handleLogin() {
  // TODO: implement Google OAuth
  alert("Google login coming soon");
}

// ── ENTER KEY ─────────────────────────────────────────────────────────────────
document.getElementById("urlInput").addEventListener("keydown", e => {
  if (e.key === "Enter") addMaterial();
});

// ── INIT ──────────────────────────────────────────────────────────────────────
loadMaterials();
</script>
</body>
</html>
