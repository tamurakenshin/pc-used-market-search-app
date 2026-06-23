const state = {
  products: [],
  visibleProducts: [],
  category: "すべて",
  partType: "",
  brand: "",
  condition: "",
  query: "",
  sort: "score",
  columns: Number(localStorage.getItem("pcScoutColumns") || 3),
  saved: new Set(JSON.parse(localStorage.getItem("pcScoutSaved") || "[]")),
  selectedSources: new Set(),
  currentProduct: null,
  config: null,
};

const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

const categoryTitles = {
  "すべて": "マーケットを探索",
  "新品BTO": "新品BTOを比較",
  "新品PCパーツ": "新品パーツを探す",
  "新品周辺機器": "新品周辺機器を探す",
  "中古PC": "中古PCを探す",
  "中古PCパーツ": "中古パーツを探す",
  "中古周辺機器": "中古周辺機器を探す",
};

const specLabels = {
  brand: "メーカー", cores: "コア", threads: "スレッド", clock: "周波数", year: "年式",
  tdp: "TDP", codename: "世代", socket: "ソケット", memory: "メモリ", capacity: "容量",
  standard: "規格", speed: "速度", interface: "接続", cpu: "CPU", gpu: "GPU",
  storage: "ストレージ", display: "ディスプレイ", size: "サイズ", resolution: "解像度",
  refresh: "リフレッシュレート", panel: "パネル",
};

function escapeHTML(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function money(value) {
  return `¥${Math.round(Number(value || 0)).toLocaleString("ja-JP")}`;
}

function safeImage(value) {
  const image = String(value || "");
  if (image.startsWith("/assets/") || image.startsWith("https://") || image.startsWith("http://")) return image;
  return "/assets/pc.svg";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function initialize() {
  applyTheme(localStorage.getItem("pcScoutTheme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  setColumns(state.columns);
  bindEvents();
  renderSkeletons();
  try {
    state.config = await api("/api/config");
    renderConnectionState();
    renderSources(state.config.sources || []);
  } catch (error) {
    $("#serverStatus").textContent = "切断";
    $("#serverDot").classList.add("is-error");
    showToast("ローカルサーバーに接続できませんでした");
  }
  await loadProducts();
}

function bindEvents() {
  $$(".nav-item[data-category]").forEach((button) => button.addEventListener("click", () => selectCategory(button.dataset.category)));
  bindChoiceGroup("#partTypeFilter", ".segment", (value) => { state.partType = value; applyFilters(); });
  bindChoiceGroup("#brandFilter", ".chip", (value) => { state.brand = value; applyFilters(); });
  bindChoiceGroup("#conditionFilter", ".grade-option", (value) => { state.condition = value; applyFilters(); });

  $("#applyFilters").addEventListener("click", () => { applyFilters(); closeMobilePanels(); });
  $("#clearFilters").addEventListener("click", resetFilters);
  $("#emptyReset").addEventListener("click", resetFilters);
  $("#sortSelect").addEventListener("change", (event) => { state.sort = event.target.value; applyFilters(); });
  $("#columnSelect").value = String(state.columns);
  $("#columnSelect").addEventListener("change", (event) => setColumns(Number(event.target.value)));
  $("#themeToggle").addEventListener("click", toggleTheme);
  $("#searchForm").addEventListener("submit", runSearch);
  $("#aiResearchButton").addEventListener("click", () => $("#aiModal").showModal());
  $("#aiForm").addEventListener("submit", askAI);
  $$(".ai-suggestions button").forEach((button) => button.addEventListener("click", () => {
    $("#aiQuestion").value = button.textContent;
    $("#aiForm").requestSubmit();
  }));
  $("#settingsButton").addEventListener("click", () => $("#settingsModal").showModal());
  $$('[data-close]').forEach((button) => button.addEventListener("click", () => $("#" + button.dataset.close).close()));
  $$("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }));

  $("#openMenu").addEventListener("click", () => openMobilePanel("primarySidebar"));
  $("#openFilters").addEventListener("click", () => openMobilePanel("filterSidebar"));
  $("#closeFilters").addEventListener("click", closeMobilePanels);
  $("#mobileScrim").addEventListener("click", closeMobilePanels);

  ["priceMin", "priceMax", "coresFilter", "yearFilter", "socketFilter", "freewordFilter", "excludeFilter"]
    .forEach((id) => $("#" + id).addEventListener(id.includes("price") || id.includes("Filter") ? "change" : "input", applyFilters));
  $$(".budget-presets button").forEach((button) => button.addEventListener("click", () => {
    $("#priceMax").value = Number(button.dataset.max).toLocaleString("ja-JP");
    applyFilters();
  }));

  $("#productGrid").addEventListener("click", handleCardAction);
}

function bindChoiceGroup(containerSelector, buttonSelector, callback) {
  const container = $(containerSelector);
  container.addEventListener("click", (event) => {
    const button = event.target.closest(buttonSelector);
    if (!button) return;
    $$(buttonSelector, container).forEach((item) => item.classList.toggle("is-active", item === button));
    callback(button.dataset.value || "");
  });
}

function selectCategory(category) {
  state.category = category;
  $$(".nav-item[data-category]").forEach((item) => item.classList.toggle("is-active", item.dataset.category === category));
  $("#pageTitle").textContent = categoryTitles[category];
  $("#filterTitle").textContent = category === "すべて" ? "すべての商品" : category;
  closeMobilePanels();
  loadProducts();
}

async function loadProducts() {
  renderSkeletons();
  const params = new URLSearchParams();
  if (state.category !== "すべて") params.set("category", state.category);
  if (state.query) params.set("q", state.query);
  try {
    const data = await api(`/api/products?${params}`);
    state.products = data.items || [];
    $("#dataMode").textContent = data.mode.toUpperCase();
    $("#notice").classList.add("is-hidden");
    applyFilters();
  } catch (error) {
    state.products = [];
    applyFilters();
    showToast(error.message);
  }
}

async function runSearch(event) {
  event.preventDefault();
  state.query = $("#searchInput").value.trim();
  renderSkeletons();
  const live = $("#liveToggle").checked;
  try {
    const data = await api("/api/search", {
      method: "POST",
      body: JSON.stringify({ query: state.query, live, sources: [...state.selectedSources] }),
    });
    state.products = data.items || [];
    $("#dataMode").textContent = data.mode.toUpperCase();
    renderNotice(data.warnings || []);
    applyFilters();
    showToast(`${data.total}件のデータを取得しました`);
  } catch (error) {
    state.products = [];
    applyFilters();
    renderNotice([error.message]);
  }
}

function applyFilters() {
  const minPrice = parseNumber($("#priceMin").value) || 0;
  const maxPrice = parseNumber($("#priceMax").value) || Number.MAX_SAFE_INTEGER;
  const minCores = Number($("#coresFilter").value || 0);
  const minYear = Number($("#yearFilter").value || 0);
  const socket = $("#socketFilter").value.trim().toLowerCase();
  const freeword = $("#freewordFilter").value.trim().toLowerCase();
  const excludes = $("#excludeFilter").value.toLowerCase().split(",").map((word) => word.trim()).filter(Boolean);

  state.visibleProducts = state.products.filter((product) => {
    const text = `${product.title} ${product.source} ${JSON.stringify(product.specs || {})}`.toLowerCase();
    const price = Number(product.price || 0);
    if (state.partType && product.part_type !== state.partType) return false;
    if (state.brand && !text.includes(state.brand.toLowerCase())) return false;
    if (state.condition && product.condition !== state.condition) return false;
    if (price < minPrice || price > maxPrice) return false;
    if (minCores && Number(product.specs?.cores || 0) < minCores) return false;
    if (minYear && Number(product.specs?.year || 0) < minYear) return false;
    if (socket && !text.includes(socket)) return false;
    if (freeword && !text.includes(freeword)) return false;
    if (excludes.some((word) => text.includes(word))) return false;
    return true;
  });
  sortProducts();
  renderProducts();
  updateMetrics();
}

function sortProducts() {
  const sorters = {
    score: (a, b) => Number(b.ai?.score || 0) - Number(a.ai?.score || 0),
    priceAsc: (a, b) => Number(a.price) - Number(b.price),
    priceDesc: (a, b) => Number(b.price) - Number(a.price),
    newest: (a, b) => Number(b.specs?.year || 0) - Number(a.specs?.year || 0),
  };
  state.visibleProducts.sort(sorters[state.sort] || sorters.score);
}

function renderProducts() {
  const grid = $("#productGrid");
  $("#resultCount").textContent = `${state.visibleProducts.length}件`;
  $("#emptyState").classList.toggle("is-hidden", state.visibleProducts.length > 0);
  if (!state.visibleProducts.length) {
    grid.innerHTML = "";
    return;
  }
  grid.innerHTML = state.visibleProducts.map(productCard).join("");
  $$("img", grid).forEach((image) => image.addEventListener("error", () => { image.src = "/assets/pc.svg"; }, { once: true }));
}

function productCard(product) {
  const ai = product.ai || { grade: product.condition || "B", score: 70, label: "未評価", market_price: product.price, summary: "詳細画面からAI評価を実行できます。" };
  const gradeClass = ai.grade === "ジャンク" ? "grade-junk" : `grade-${escapeHTML(ai.grade)}`;
  const specs = Object.values(product.specs || {}).slice(0, 4).join(" ・ ") || "詳細情報を取得中";
  const saved = state.saved.has(product.id);
  return `
    <article class="product-card" data-id="${escapeHTML(product.id)}">
      <div class="card-image">
        <img src="${escapeHTML(safeImage(product.image))}" alt="${escapeHTML(product.title)}" loading="lazy">
        <span class="source-badge">${escapeHTML(product.source)}</span>
        <span class="grade-badge ${gradeClass}" title="AI状態評価">${escapeHTML(ai.grade)}</span>
      </div>
      <div class="card-body">
        <div class="card-meta"><span class="part-pill">${escapeHTML(product.part_type)}</span><span>AI SCORE ${Number(ai.score || 0)}</span></div>
        <h3>${escapeHTML(product.title)}</h3>
        <p class="spec-line">${escapeHTML(specs)}</p>
        <div class="price-row"><div class="price">${money(product.price)}<small>税込</small></div><div class="market-price">AI推定相場<b>${money(ai.market_price || product.price)}</b></div></div>
        <div class="ai-insight"><span>✦</span><div><strong>${escapeHTML(ai.label)} · AI評価</strong><p>${escapeHTML(ai.summary)}</p></div></div>
        <div class="card-actions"><button class="view-button" data-action="view">詳しく見る</button><button class="save-button ${saved ? "is-saved" : ""}" data-action="save" aria-label="お気に入り">${saved ? "♥" : "♡"}</button></div>
      </div>
    </article>`;
}

function updateMetrics() {
  const products = state.visibleProducts;
  const prices = products.map((item) => Number(item.price)).filter(Boolean).sort((a, b) => a - b);
  const median = prices.length ? (prices.length % 2 ? prices[(prices.length - 1) / 2] : (prices[prices.length / 2 - 1] + prices[prices.length / 2]) / 2) : 0;
  $("#medianPrice").textContent = median ? money(median) : "—";
  $("#dealCount").textContent = `${products.filter((item) => Number(item.ai?.score || 0) >= 86).length}件`;
  $("#sourceCount").textContent = `${new Set(products.map((item) => item.source)).size}ストア`;
  $("#updatedAt").textContent = `更新 ${new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`;
  $("#resultSummary").textContent = state.query ? `「${state.query}」の検索結果を価格・状態・AI評価で比較しています。` : "複数ストアの価格を比較し、AIが買い時を判定します。";
}

function handleCardAction(event) {
  const button = event.target.closest("[data-action]");
  const card = event.target.closest(".product-card");
  if (!button || !card) return;
  const product = state.products.find((item) => item.id === card.dataset.id);
  if (!product) return;
  if (button.dataset.action === "save") toggleSaved(product.id);
  if (button.dataset.action === "view") openProduct(product);
}

function toggleSaved(id) {
  state.saved.has(id) ? state.saved.delete(id) : state.saved.add(id);
  localStorage.setItem("pcScoutSaved", JSON.stringify([...state.saved]));
  renderProducts();
  showToast(state.saved.has(id) ? "お気に入りに保存しました" : "お気に入りから外しました");
}

function openProduct(product) {
  state.currentProduct = product;
  const ai = product.ai || { grade: product.condition, score: "—", label: "未評価", market_price: product.price, summary: "AI再評価を実行してください。" };
  const specs = Object.entries(product.specs || {}).map(([key, value]) => `<div><small>${escapeHTML(specLabels[key] || key)}</small><b>${escapeHTML(value)}</b></div>`).join("");
  $("#productModalContent").innerHTML = `
    <div class="product-detail-hero">
      <div class="product-detail-image"><img src="${escapeHTML(safeImage(product.image))}" alt="${escapeHTML(product.title)}"></div>
      <div class="product-detail-copy"><span class="detail-grade">AI GRADE ${escapeHTML(ai.grade)} · ${escapeHTML(ai.score)}</span><h2>${escapeHTML(product.title)}</h2><p class="detail-source">${escapeHTML(product.source)} · ${escapeHTML(product.category)}</p><div class="detail-price">${money(product.price)}</div></div>
    </div>
    <div class="spec-table">${specs || "<div><small>仕様</small><b>取得データなし</b></div>"}</div>
    <div class="detail-ai"><strong>✦ ${escapeHTML(ai.label)} · 推定相場 ${money(ai.market_price || product.price)}</strong><p>${escapeHTML(ai.summary)}</p></div>
    <div class="detail-actions"><a href="${escapeHTML(product.url)}" target="_blank" rel="noopener noreferrer">掲載ページを見る ↗</a><button id="reanalyzeButton">AIで再評価</button><button class="accent-action" id="listingButton">出品文を作る</button></div>
    <div class="listing-output is-hidden" id="listingOutput"></div>`;
  $("#productModalContent img").addEventListener("error", (event) => { event.target.src = "/assets/pc.svg"; }, { once: true });
  $("#reanalyzeButton").addEventListener("click", reanalyzeProduct);
  $("#listingButton").addEventListener("click", generateListing);
  $("#productModal").showModal();
}

async function reanalyzeProduct() {
  const button = $("#reanalyzeButton");
  button.disabled = true;
  button.textContent = "評価中…";
  try {
    const analysis = await api("/api/ai/analyze", { method: "POST", body: JSON.stringify({ product: state.currentProduct, comparables: state.products }) });
    state.currentProduct.ai = analysis;
    openProductAfterRefresh(state.currentProduct);
    applyFilters();
    showToast(analysis.mode === "groq" ? "Groq AIで再評価しました" : "ローカル相場ロジックで評価しました");
  } catch (error) {
    showToast(error.message);
    button.disabled = false;
    button.textContent = "AIで再評価";
  }
}

function openProductAfterRefresh(product) {
  $("#productModal").close();
  openProduct(product);
}

async function generateListing() {
  const button = $("#listingButton");
  const output = $("#listingOutput");
  button.disabled = true;
  button.textContent = "生成中…";
  output.classList.remove("is-hidden");
  output.innerHTML = "<h4>出品文を作成しています…</h4>";
  try {
    const listing = await api("/api/ai/listing", { method: "POST", body: JSON.stringify({ product: state.currentProduct }) });
    output.innerHTML = `<h4>${escapeHTML(listing.title)}</h4><pre>${escapeHTML(listing.description)}\n\n注意: ${escapeHTML(listing.caution)}</pre>`;
  } catch (error) {
    output.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "出品文を作る";
  }
}

async function askAI(event) {
  event.preventDefault();
  const question = $("#aiQuestion").value.trim();
  const answer = $("#aiAnswer");
  answer.classList.add("is-loading");
  answer.textContent = "市場データを分析しています…";
  try {
    const result = await api("/api/ai/research", { method: "POST", body: JSON.stringify({ question, products: state.visibleProducts }) });
    answer.textContent = result.answer;
  } catch (error) {
    answer.textContent = error.message;
  } finally {
    answer.classList.remove("is-loading");
  }
}

function renderSources(sources) {
  state.selectedSources = new Set(sources);
  $("#sourceGrid").innerHTML = sources.map((source) => `<label class="source-option"><input type="checkbox" value="${escapeHTML(source)}" checked><span>${escapeHTML(source)}</span></label>`).join("");
  $("#sourceGrid").addEventListener("change", (event) => {
    if (!event.target.matches("input")) return;
    event.target.checked ? state.selectedSources.add(event.target.value) : state.selectedSources.delete(event.target.value);
  });
}

function renderConnectionState() {
  $("#serverDot").classList.add("is-on");
  $("#serverStatus").textContent = "稼働中";
  $("#groqDot").classList.toggle("is-on", state.config.groq_enabled);
  $("#groqStatus").textContent = state.config.groq_enabled ? "接続済" : "ローカル";
  if (!state.config.live_scraping_enabled) {
    $("#liveToggle").addEventListener("change", (event) => {
      if (event.target.checked) showToast("サーバーでLIVE巡回が無効です。検索時はデモ結果にフォールバックします");
    });
  }
}

function renderNotice(messages) {
  const notice = $("#notice");
  notice.textContent = messages.join(" / ");
  notice.classList.toggle("is-hidden", messages.length === 0);
}

function renderSkeletons() {
  $("#emptyState").classList.add("is-hidden");
  $("#productGrid").innerHTML = Array.from({ length: Math.min(state.columns * 2, 8) }, () => '<div class="skeleton"></div>').join("");
}

function resetFilters() {
  state.partType = "";
  state.brand = "";
  state.condition = "";
  ["priceMin", "priceMax", "coresFilter", "yearFilter", "socketFilter", "freewordFilter", "excludeFilter"].forEach((id) => { $("#" + id).value = ""; });
  ["#partTypeFilter", "#brandFilter", "#conditionFilter"].forEach((selector) => {
    $$("button", $(selector)).forEach((button, index) => button.classList.toggle("is-active", index === 0));
  });
  applyFilters();
}

function setColumns(columns) {
  state.columns = Math.max(2, Math.min(4, columns));
  document.documentElement.style.setProperty("--columns", state.columns);
  localStorage.setItem("pcScoutColumns", String(state.columns));
  if ($("#columnSelect")) $("#columnSelect").value = String(state.columns);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("pcScoutTheme", theme);
  const icon = $(".theme-icon");
  if (icon) icon.textContent = theme === "dark" ? "☀" : "☾";
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
}

function openMobilePanel(id) {
  closeMobilePanels();
  $("#" + id).classList.add("is-open");
  $("#mobileScrim").classList.add("is-open");
}

function closeMobilePanels() {
  $("#primarySidebar").classList.remove("is-open");
  $("#filterSidebar").classList.remove("is-open");
  $("#mobileScrim").classList.remove("is-open");
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  $("#toastRegion").append(toast);
  setTimeout(() => toast.remove(), 3500);
}

function parseNumber(value) {
  return Number(String(value || "").replace(/[^0-9]/g, ""));
}

initialize();
