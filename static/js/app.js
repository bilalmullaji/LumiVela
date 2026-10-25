const API_BASE = (window.location.protocol === "file:" || (window.location.port && window.location.port !== "8000"))
  ? "http://127.0.0.1:8000"
  : "";

let currentThreadId = null;
let holdTimerInterval = null;
let catalogProducts = [];
let shopFilter = "all";
let bag = loadBag();

const chatHistory = document.getElementById("chat-history");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const stateSlotsDisplay = document.getElementById("state-slots-display");
const quickChipsContainer = document.getElementById("quick-chips");
const widget = document.getElementById("lumi-widget");
const launcher = document.getElementById("lumi-launcher");

function loadBag() {
  try {
    const next = localStorage.getItem("vela_bag");
    if (next) return JSON.parse(next);
    const legacy = localStorage.getItem("ag_bag");
    if (legacy) {
      const parsed = JSON.parse(legacy);
      localStorage.setItem("vela_bag", legacy);
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

function saveBag() {
  localStorage.setItem("vela_bag", JSON.stringify(bag));
  updateCartCount();
}

function updateCartCount() {
  const el = document.getElementById("cart-count");
  if (el) el.textContent = String(bag.length);
}

function formatPrice(n) {
  return `₹${Number(n || 0).toLocaleString("en-IN")}`;
}

function formatRating(r) {
  if (r == null || Number.isNaN(Number(r))) return null;
  return `★ ${Number(r).toFixed(1)}`;
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function productArt(product) {
  const name = escapeHtml(product.name || "Vela product");
  if (product.image_url) {
    return `<img class="product-photo" src="${escapeHtml(product.image_url)}" alt="${name}" loading="lazy" decoding="async" onerror="this.onerror=null;this.remove()" />`;
  }
  const palettes = {
    tops: ["#E0CAFF", "#7A4CC0"],
    bottoms: ["#C8EED4", "#146C45"],
    outerwear: ["#F8D5E4", "#C45B86"],
    accessories: ["#D6E8FF", "#355C8C"]
  };
  const [bg, fg] = palettes[product.category] || palettes.tops;
  const label = escapeHtml((product.name || "Vela").split(" ").slice(0, 2).join(" "));
  return `
    <svg viewBox="0 0 320 180" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${name}">
      <rect width="320" height="180" fill="${bg}"/>
      <circle cx="250" cy="30" r="48" fill="#FFFFFF" opacity="0.45"/>
      <rect x="108" y="42" width="104" height="96" rx="28" fill="#FFFFFF"/>
      <rect x="128" y="62" width="64" height="56" rx="16" fill="${fg}"/>
      <text x="160" y="162" text-anchor="middle" font-size="12" font-family="Inter, sans-serif" fill="#20202A">${label}</text>
    </svg>`;
}

function productCardHtml(p, index = 0) {
  const details = [p.fit, p.gsm ? `${p.gsm} GSM` : null, (p.sizes || []).join("/")].filter(Boolean).join(" · ");
  const rating = formatRating(p.rating);
  const delay = Math.min(index, 8) * 40;
  return `
    <article class="store-card is-entering" style="animation-delay:${delay}ms">
      <div class="art">${productArt(p)}</div>
      <div class="body">
        <span class="tag-badge">${escapeHtml(p.category || "catalog")}</span>
        <h4 class="product-title">${escapeHtml(p.name)}</h4>
        <p class="price-tag">${formatPrice(p.price_inr)}</p>
        ${rating ? `<p class="product-rating">${rating}</p>` : ""}
        <p class="product-meta">${escapeHtml(details)}</p>
        <div class="card-actions">
          <button type="button" class="btn-card" onclick="viewProduct('${p.id}')">View product</button>
          <button type="button" class="btn-card solid" onclick="addToBag('${p.id}')">Add to cart</button>
        </div>
      </div>
    </article>`;
}

function shortBadge(p) {
  const cat = (p.category || "piece").replace(/s$/, "");
  return cat.charAt(0).toUpperCase() + cat.slice(1);
}

function chatProductCardHtml(p) {
  const details = [p.gsm ? `${p.gsm} GSM` : null].filter(Boolean).join(" · ");
  const rating = formatRating(p.rating);
  return `
    <article class="product-card is-entering">
      <div class="product-art">${productArt(p)}</div>
      <div class="body">
        <div class="product-badge-row">
          <span class="tag-badge">${escapeHtml(shortBadge(p))}</span>
          <span class="price-tag">${formatPrice(p.price_inr)}</span>
        </div>
        <div class="product-title" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</div>
        ${rating ? `<div class="product-rating">${rating}${details ? ` · ${escapeHtml(details)}` : ""}</div>` : ""}
        <div class="card-actions">
          <button type="button" class="btn-card solid" onclick="addToBag('${p.id}', true)">Add to cart</button>
          <button type="button" class="btn-card" onclick="viewProduct('${p.id}')">View</button>
        </div>
      </div>
    </article>`;
}

function buildProductRail(products) {
  const shell = document.createElement("div");
  shell.className = "product-rail-shell";

  const rail = document.createElement("div");
  rail.className = "product-rail";
  products.forEach((p) => {
    const wrap = document.createElement("div");
    wrap.innerHTML = chatProductCardHtml(p);
    rail.appendChild(wrap.firstElementChild);
  });

  const prev = document.createElement("button");
  prev.type = "button";
  prev.className = "rail-nav rail-nav-prev";
  prev.setAttribute("aria-label", "Previous products");
  prev.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>`;

  const next = document.createElement("button");
  next.type = "button";
  next.className = "rail-nav rail-nav-next";
  next.setAttribute("aria-label", "Next products");
  next.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg>`;

  const syncNav = () => {
    const max = rail.scrollWidth - rail.clientWidth - 2;
    const atStart = rail.scrollLeft <= 4;
    const atEnd = rail.scrollLeft >= max;
    const canScroll = max > 8;
    prev.disabled = !canScroll || atStart;
    next.disabled = !canScroll || atEnd;
    shell.classList.toggle("has-overflow", canScroll);
  };

  prev.addEventListener("click", () => {
    rail.scrollBy({ left: -rail.clientWidth * 0.85, behavior: "smooth" });
  });
  next.addEventListener("click", () => {
    rail.scrollBy({ left: rail.clientWidth * 0.85, behavior: "smooth" });
  });
  rail.addEventListener("scroll", syncNav, { passive: true });

  shell.appendChild(prev);
  shell.appendChild(rail);
  shell.appendChild(next);
  requestAnimationFrame(syncNav);
  return shell;
}

function continueShopping() {
  closeModal();
  location.hash = "#shop";
  openLumi();
  sendQuickMessage("continue shopping");
}

async function loadCatalog() {
  try {
    const res = await fetch(`${API_BASE}/api/catalog`);
    if (!res.ok) throw new Error("catalog");
    const data = await res.json();
    catalogProducts = data.products || [];
    updateBackendStatus(true);
  } catch {
    catalogProducts = [];
    updateBackendStatus(false);
  }
  renderHome();
  renderShop();
  renderCart();
}

function renderHome() {
  const grid = document.getElementById("home-grid");
  if (!grid) return;
  const featured = catalogProducts.slice(0, 4);
  if (!featured.length) {
    grid.innerHTML = `<p class="empty-note">Catalog is unavailable right now. Start the backend with python app.py, then refresh.</p>`;
    return;
  }
  grid.innerHTML = featured.map((p, i) => productCardHtml(p, i)).join("");
}

function renderShop() {
  const grid = document.getElementById("shop-grid");
  if (!grid) return;
  const items = catalogProducts.filter((p) => shopFilter === "all" || p.category === shopFilter);
  if (!catalogProducts.length) {
    grid.innerHTML = `<p class="empty-note">No catalog data loaded. Lumi can still chat once the API is online.</p>`;
    return;
  }
  if (!items.length) {
    grid.innerHTML = `<p class="unavailable">No products in this category.</p>`;
    return;
  }
  grid.innerHTML = items.map((p, i) => productCardHtml(p, i)).join("");
}

function renderCart() {
  const wrap = document.getElementById("cart-items");
  const count = document.getElementById("summary-count");
  const total = document.getElementById("summary-total");
  if (!wrap) return;
  if (!bag.length) {
    wrap.innerHTML = `
      <div class="empty-state">
        <p class="empty-title">Your bag is empty</p>
        <p class="empty-copy">Browse the collection or ask Lumi to curate a fit.</p>
        <a class="btn-primary" href="#shop">Continue shopping</a>
      </div>`;
  } else {
    wrap.innerHTML = bag.map((item, idx) => `
      <div class="cart-line">
        <div>
          <p class="product-title">${escapeHtml(item.name)}</p>
          <p class="product-meta">${escapeHtml(item.size || "Size later")} · ${formatPrice(item.price_inr)}</p>
        </div>
        <button type="button" class="btn-secondary" onclick="removeFromBag(${idx})">Remove</button>
      </div>`).join("");
  }
  const sum = bag.reduce((acc, item) => acc + Number(item.price_inr || 0), 0);
  if (count) count.textContent = String(bag.length);
  if (total) total.textContent = formatPrice(sum);
  updateCartCount();
}

function getProduct(id) {
  return catalogProducts.find((p) => p.id === id);
}

function viewProduct(id) {
  const p = getProduct(id);
  const modal = document.getElementById("product-modal");
  const body = document.getElementById("modal-body");
  if (!modal || !body) return;
  if (!p) {
    body.innerHTML = `
      <div class="unavailable">
        <h3 id="modal-title">Product unavailable</h3>
        <p class="product-desc">This item is not in the live catalog, so Lumi will not invent stock or pricing for it.</p>
        <div class="card-actions" style="margin-top:14px;">
          <button type="button" class="btn-card solid" onclick="continueShopping()">Continue shopping</button>
        </div>
      </div>`;
  } else {
    const rating = formatRating(p.rating);
    body.innerHTML = `
      <div class="art">${productArt(p)}</div>
      <h3 id="modal-title">${escapeHtml(p.name)}</h3>
      <p class="price-tag">${formatPrice(p.price_inr)}</p>
      ${rating ? `<p class="product-rating">${rating}</p>` : ""}
      <p class="product-meta">${escapeHtml(p.fit)} · ${escapeHtml((p.sizes || []).join(", "))}</p>
      <p class="product-desc">${escapeHtml(p.description)}</p>
      <p class="product-meta">Fabric: ${escapeHtml(p.fabric)}</p>
      <div class="card-actions" style="margin-top:14px;">
        <button type="button" class="btn-card solid" onclick="addToBag('${p.id}')">Add to cart</button>
        <button type="button" class="btn-card" onclick="askLumiAbout('${p.id}')">Ask Lumi</button>
        <button type="button" class="btn-card" onclick="continueShopping()">Continue shopping</button>
      </div>`;
  }
  openModal();
}

let modalCloseTimer = null;

function openModal() {
  const modal = document.getElementById("product-modal");
  if (!modal) return;
  if (modalCloseTimer) clearTimeout(modalCloseTimer);
  modal.classList.remove("is-closing");
  modal.setAttribute("aria-hidden", "false");
  // Force reflow so open transition always plays
  void modal.offsetWidth;
  modal.classList.add("is-open");
}

function closeModal() {
  const modal = document.getElementById("product-modal");
  if (!modal || !modal.classList.contains("is-open")) return;
  const closeMs = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--modal-close-dur")) || 180;
  modal.classList.remove("is-open");
  modal.classList.add("is-closing");
  modal.setAttribute("aria-hidden", "true");
  if (modalCloseTimer) clearTimeout(modalCloseTimer);
  modalCloseTimer = setTimeout(() => {
    modal.classList.remove("is-closing");
  }, closeMs);
}

function addToBag(id, fromChat = false) {
  const p = getProduct(id);
  if (!p) {
    openLumi();
    appendMessage("assistant", "That product is not in the live catalog, so I can’t add it to your bag.");
    return;
  }
  bag.push({ id: p.id, name: p.name, price_inr: p.price_inr, size: null });
  saveBag();
  renderCart();
  closeModal();
  openLumi();
  selectPiece(p.id);
}

function removeFromBag(idx) {
  bag.splice(idx, 1);
  saveBag();
  renderCart();
}

function askLumiAbout(id) {
  const p = getProduct(id);
  closeModal();
  openLumi();
  if (p) sendMessage(`Tell me more about ${p.name} (${p.id})`);
}

function setRoute(route) {
  document.querySelectorAll(".view").forEach((view) => {
    const active = view.dataset.view === route;
    view.hidden = !active;
    view.classList.toggle("is-visible", active);
  });
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.route === route);
  });
}

function readRoute() {
  const hash = (location.hash || "#home").replace("#", "");
  if (["home", "shop", "cart"].includes(hash)) setRoute(hash);
  else setRoute("home");
}

let lumiCloseTimer = null;

function openLumi() {
  if (!widget) return;
  if (lumiCloseTimer) clearTimeout(lumiCloseTimer);
  widget.classList.remove("is-closing");
  widget.setAttribute("aria-hidden", "false");
  void widget.offsetWidth;
  widget.classList.add("is-open");
  if (launcher) launcher.classList.add("is-hidden");
  requestAnimationFrame(() => {
    chatInput && chatInput.focus();
    updateOverflowFades();
  });
}

function closeLumi() {
  if (!widget || !widget.classList.contains("is-open")) return;
  const closeMs = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--panel-close")) || 220;
  widget.classList.remove("is-open");
  widget.classList.remove("is-fullscreen");
  syncFullscreenButton(false);
  widget.classList.add("is-closing");
  widget.setAttribute("aria-hidden", "true");
  if (lumiCloseTimer) clearTimeout(lumiCloseTimer);
  lumiCloseTimer = setTimeout(() => {
    widget.classList.remove("is-closing");
    if (launcher) launcher.classList.remove("is-hidden");
  }, closeMs);
}

function syncFullscreenButton(isFull) {
  const btn = document.getElementById("btn-fullscreen-lumi");
  if (!btn) return;
  btn.setAttribute("aria-pressed", isFull ? "true" : "false");
  btn.title = isFull ? "Exit fullscreen" : "Toggle fullscreen";
}

function toggleLumiFullscreen() {
  if (!widget || !widget.classList.contains("is-open")) {
    openLumi();
  }
  const next = !widget.classList.contains("is-fullscreen");
  widget.classList.toggle("is-fullscreen", next);
  syncFullscreenButton(next);
  requestAnimationFrame(updateOverflowFades);
}

function updateOverflowFades() {
  const history = document.getElementById("chat-history");
  const historyFade = history?.closest(".chat-scroll-fade");
  if (history && historyFade) {
    const top = history.scrollTop > 4;
    const bottom = history.scrollTop + history.clientHeight < history.scrollHeight - 4;
    historyFade.classList.toggle("can-scroll-up", top);
    historyFade.classList.toggle("can-scroll-down", bottom);
  }

  const chips = document.getElementById("quick-chips");
  const chipsFade = document.getElementById("chips-fade");
  if (chips && chipsFade) {
    const left = chips.scrollLeft > 4;
    const right = chips.scrollLeft + chips.clientWidth < chips.scrollWidth - 4;
    chipsFade.classList.toggle("can-scroll-left", left);
    chipsFade.classList.toggle("can-scroll-right", right);
  }
}

function revealHero() {
  const hero = document.getElementById("hero");
  const stagger = document.getElementById("hero-stagger");
  requestAnimationFrame(() => {
    stagger?.classList.add("is-shown");
    hero?.classList.add("is-shown");
  });
}

function updateBackendStatus(isOnline) {
  const pill = document.getElementById("backend-status");
  if (!pill) return;
  if (isOnline) {
    pill.classList.remove("is-offline");
    pill.innerHTML = `<span class="status-dot" aria-hidden="true"></span> Lumi is online`;
  } else {
    pill.classList.add("is-offline");
    pill.innerHTML = `<span class="status-dot" aria-hidden="true"></span> Backend offline — start app.py`;
  }
}

function wireFaq(id, message) {
  document.getElementById(id)?.addEventListener("click", () => {
    openLumi();
    sendQuickMessage(message);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  readRoute();
  revealHero();
  loadCatalog();
  initSession();

  wireFaq("btn-shipping-faq", "What is your shipping policy and delivery time?");
  wireFaq("btn-returns-faq", "What is your returns and exchange policy?");
  wireFaq("btn-sizing-faq", "How does sizing work for your oversized cuts?");
  wireFaq("btn-shipping-faq-m", "What is your shipping policy and delivery time?");
  wireFaq("btn-returns-faq-m", "What is your returns and exchange policy?");
  wireFaq("btn-sizing-faq-m", "How does sizing work for your oversized cuts?");

  document.getElementById("btn-reset")?.addEventListener("click", resetSession);
  document.getElementById("btn-fullscreen-lumi")?.addEventListener("click", toggleLumiFullscreen);
  document.getElementById("btn-open-lumi")?.addEventListener("click", openLumi);
  document.getElementById("btn-hero-lumi")?.addEventListener("click", openLumi);
  document.getElementById("lumi-launcher")?.addEventListener("click", openLumi);
  document.getElementById("btn-close-lumi")?.addEventListener("click", closeLumi);
  document.getElementById("chat-history")?.addEventListener("scroll", updateOverflowFades, { passive: true });
  document.getElementById("quick-chips")?.addEventListener("scroll", updateOverflowFades, { passive: true });
  window.addEventListener("resize", updateOverflowFades);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && widget?.classList.contains("is-fullscreen")) {
      widget.classList.remove("is-fullscreen");
      syncFullscreenButton(false);
    }
  });
  document.getElementById("btn-checkout-lumi")?.addEventListener("click", () => {
    openLumi();
    sendQuickMessage("head to checkout");
  });
  document.getElementById("shop-filters")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-filter]");
    if (!btn) return;
    shopFilter = btn.dataset.filter;
    document.querySelectorAll("#shop-filters .chip-btn").forEach((el) => {
      el.classList.toggle("is-selected", el === btn);
    });
    renderShop();
  });
  document.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", closeModal);
  });
});

window.addEventListener("hashchange", readRoute);

async function initSession() {
  currentThreadId = "session_" + Math.random().toString(36).substring(2, 9);
  if (chatHistory) chatHistory.innerHTML = "";
  if (stateSlotsDisplay) {
    stateSlotsDisplay.hidden = true;
    stateSlotsDisplay.innerHTML = "";
  }

  showTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/api/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: currentThreadId })
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    removeTypingIndicator();
    updateBackendStatus(true);
    appendMessage("assistant", data.greeting, [], null, data.state);
    updateStateDisplay(data.state);
    renderDynamicChips(data.state, []);
  } catch (err) {
    removeTypingIndicator();
    updateBackendStatus(false);
    appendMessage(
      "assistant",
      `I can’t reach the shopping backend at ${API_BASE || "localhost:8000"}. Start it with \`python app.py\`, then tap **Retry**.`,
      [],
      null,
      { current_step: "error" }
    );
    renderDynamicChips({ current_step: "error" }, []);
  }
}

async function resetSession() {
  if (holdTimerInterval) clearInterval(holdTimerInterval);
  await initSession();
}

function handleChatSubmit(e) {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  sendMessage(text);
}

function sendQuickMessage(text) {
  openLumi();
  sendMessage(text);
}

function selectPiece(productId) {
  sendMessage(`I choose piece ${productId}`);
}

function addAccessory(accId) {
  sendMessage(`Add accessory ${accId} to my fit`);
}

async function sendMessage(text) {
  appendMessage("user", text);
  showTypingIndicator();
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        thread_id: currentThreadId
      })
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    removeTypingIndicator();
    updateBackendStatus(true);
    appendMessage("assistant", data.response, data.recommended_products, data.suggested_accessory, data.state);
    updateStateDisplay(data.state);
    renderDynamicChips(data.state, data.recommended_products);
    if (data.state && data.state.current_step === "review_order") {
      startReservationTimer();
    }
  } catch (err) {
    removeTypingIndicator();
    updateBackendStatus(false);
    const errEl = document.createElement("div");
    errEl.className = "message assistant";
    errEl.innerHTML = `
      <div class="avatar">L</div>
      <div class="message-bubble">
        <div class="error-card">
          <strong>Connection lost</strong>
          <p class="product-desc">Make sure \`python app.py\` is running, then send your message again.</p>
        </div>
      </div>`;
    chatHistory.appendChild(errEl);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

function appendMessage(role, text, products = [], accessory = null, state = {}) {
  const msgEl = document.createElement("div");
  msgEl.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.innerText = role === "assistant" ? "L" : "You";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  if (typeof marked !== "undefined" && marked.parse) {
    bubble.innerHTML = marked.parse(text || "");
  } else {
    bubble.innerText = text || "";
  }

  if (products && products.length > 0) {
    bubble.appendChild(buildProductRail(products));
  } else if (state && state.current_step === "recommending") {
    const empty = document.createElement("div");
    empty.className = "unavailable";
    empty.textContent = "No matching catalog cards were returned for this step.";
    bubble.appendChild(empty);
  }

  if (accessory && state && state.current_step === "product_added_ask_continue") {
    const accCard = document.createElement("div");
    accCard.className = "accessory-highlight";
    accCard.innerHTML = `
      <p class="product-title">${escapeHtml(accessory.name)}</p>
      <p class="product-desc">${escapeHtml(accessory.description)}</p>
      <p class="price-tag">${formatPrice(accessory.price_inr)}</p>
      <div class="card-actions">
        <button type="button" class="btn-card" onclick="viewProduct('${accessory.id}')">View</button>
        <button type="button" class="btn-card solid" onclick="addAccessory('${accessory.id}')">Add accessory</button>
      </div>`;
    bubble.appendChild(accCard);
  }

  if (state && state.current_step === "review_order") {
    const holdCard = document.createElement("div");
    holdCard.className = "hold-card";
    holdCard.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
        <strong>Review & confirm</strong>
        <div class="timer-pill" id="live-timer">15:00 hold</div>
      </div>
      <p class="product-desc">One step left — place the order or keep shopping.</p>
      <div class="card-actions">
        <button type="button" class="checkout-btn" onclick="sendQuickMessage('confirm order')">Confirm order</button>
        <button type="button" class="btn-card" onclick="continueShopping()">Keep shopping</button>
      </div>`;
    bubble.appendChild(holdCard);
  }

  if (state && state.current_step === "product_added_ask_continue") {
    const decisionCard = document.createElement("div");
    decisionCard.className = "hold-card";
    decisionCard.innerHTML = `
      <strong>In your bag</strong>
      <p class="product-desc">Add more, or checkout.</p>
      <div class="card-actions">
        <button type="button" class="btn-card" onclick="continueShopping()">Continue shopping</button>
        <button type="button" class="btn-card solid" onclick="sendQuickMessage('checkout')">Checkout</button>
      </div>`;
    bubble.appendChild(decisionCard);
  }

  if (state && state.current_step === "completed") {
    const doneCard = document.createElement("div");
    doneCard.className = "hold-card";
    doneCard.innerHTML = `
      <strong>Order placed</strong>
      <p class="product-desc">Confirmation #VL-94281 · Express dispatch tomorrow.</p>`;
    bubble.appendChild(doneCard);
  }

  msgEl.appendChild(avatar);
  msgEl.appendChild(bubble);
  chatHistory.appendChild(msgEl);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  requestAnimationFrame(updateOverflowFades);
}

function showTypingIndicator() {
  removeTypingIndicator();
  const typing = document.createElement("div");
  typing.id = "typing-indicator";
  typing.className = "message assistant";
  typing.innerHTML = `
    <div class="avatar">L</div>
    <div class="message-bubble">Lumi is looking through the catalog…</div>
  `;
  chatHistory.appendChild(typing);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function renderDynamicChips(state, products = []) {
  if (!quickChipsContainer) return;
  quickChipsContainer.innerHTML = "";
  const step = (state && state.current_step) ? state.current_step : "greeting";
  const hasOccasion = Boolean(state && state.occasions && state.occasions.length);
  const hasFit = Boolean(state && state.fit_preference);
  const hasBudget = Boolean(state && state.budget_tier);
  let chips = [];

  if (step === "error") {
    chips = [{ label: "Retry connection", msg: "__retry__" }];
  } else if (!hasOccasion || step === "greeting" || step === "asking_occasion" || step === "ooc_informed") {
    if (step === "ooc_informed") {
      chips = [
        { label: "Gym wear", msg: "intense gym workouts and heavy lifting" },
        { label: "Streetwear", msg: "casual urban streetwear" },
        { label: "Browse collection", msg: "all of the examples" }
      ];
    } else {
      chips = [
        { label: "Gym & lifting", msg: "intense gym workouts and heavy lifting" },
        { label: "Streetwear", msg: "casual urban streetwear and night out" },
        { label: "Travel", msg: "airport comfort and travel loungewear" },
        { label: "Full crossover", msg: "all of the examples" }
      ];
    }
  } else if (!hasFit || step === "asking_fit_and_budget") {
    if (!hasFit) {
      chips = [
        { label: "Oversized heavyweight", msg: "oversized heavyweight cuts" },
        { label: "Streamlined athletic", msg: "streamlined athletic cuts" },
        { label: "Clean minimalist", msg: "clean minimalist cuts" }
      ];
    } else if (!hasBudget) {
      chips = [
        { label: "Tier 1 ₹4k–₹7.5k", msg: "Tier 1: ₹4,000 – ₹7,500" },
        { label: "Tier 2 ₹7.5k–₹15k", msg: "Tier 2: ₹7,500 – ₹15,000" },
        { label: "Open budget", msg: "whatever the customer demands" }
      ];
    }
  } else if (!hasBudget || step === "asking_budget") {
    chips = [
      { label: "Tier 1 ₹4k–₹7.5k", msg: "Tier 1: ₹4,000 – ₹7,500" },
      { label: "Tier 2 ₹7.5k–₹15k", msg: "Tier 2: ₹7,500 – ₹15,000" },
      { label: "Open budget", msg: "whatever the customer demands" }
    ];
  } else if (step === "recommending") {
    chips = [{ label: "Lock in full fit", msg: "lock in full fit" }];
    (products || []).slice(0, 2).forEach((p) => {
      chips.push({ label: p.name.split(" ").slice(0, 2).join(" "), msg: `I choose piece ${p.id}` });
    });
  } else if (step === "product_added_ask_continue") {
    chips = [
      { label: "Continue shopping", msg: "continue shopping" },
      { label: "Checkout", msg: "checkout" }
    ];
  } else if (step === "continue_shopping_browse") {
    chips = [
      { label: "Tops", msg: "show me tops" },
      { label: "Bottoms", msg: "show me bottoms" },
      { label: "Outerwear", msg: "show me outerwear" },
      { label: "Checkout", msg: "checkout" }
    ];
  } else if (step === "asking_size") {
    chips = [
      { label: "S", msg: "Small" },
      { label: "M", msg: "Medium" },
      { label: "L", msg: "Large" },
      { label: "XL", msg: "XL" }
    ];
  } else if (step === "review_order") {
    chips = [
      { label: "Confirm order", msg: "confirm order" },
      { label: "Keep shopping", msg: "continue shopping" }
    ];
  } else if (step === "completed") {
    chips = [
      { label: "New session", msg: "Start session" },
      { label: "Shop more", msg: "all of the examples" }
    ];
  } else if (step === "faq_answered") {
    chips = hasBudget
      ? [{ label: "Show picks", msg: "show recommendations" }]
      : hasFit
        ? [
            { label: "Tier 1 ₹4k–₹7.5k", msg: "Tier 1: ₹4,000 – ₹7,500" },
            { label: "Open budget", msg: "whatever the customer demands" }
          ]
        : [
            { label: "Oversized heavyweight", msg: "oversized heavyweight cuts" },
            { label: "Streamlined athletic", msg: "streamlined athletic cuts" }
          ];
  }

  const chipsFade = document.getElementById("chips-fade");
  chips.slice(0, 4).forEach((c) => {
    const btn = document.createElement("button");
    btn.className = "chip-btn";
    btn.type = "button";
    btn.innerText = c.label;
    btn.onclick = () => {
      if (c.msg === "__retry__") resetSession();
      else sendQuickMessage(c.msg);
    };
    quickChipsContainer.appendChild(btn);
  });

  if (chipsFade) chipsFade.hidden = chips.length === 0;
  requestAnimationFrame(updateOverflowFades);
}

function updateStateDisplay(state) {
  if (!stateSlotsDisplay) return;
  if (!state) {
    stateSlotsDisplay.hidden = true;
    stateSlotsDisplay.innerHTML = "";
    return;
  }

  const parts = [];
  if (state.occasions && state.occasions.length) {
    parts.push(`<span>Occasion <strong>${escapeHtml(state.occasions.join(", "))}</strong></span>`);
  }
  if (state.fit_preference) {
    parts.push(`<span>Fit <strong>${escapeHtml(state.fit_preference)}</strong></span>`);
  }
  if (state.budget_tier || state.max_budget_inr) {
    const budget = state.budget_tier || `₹${state.max_budget_inr}`;
    parts.push(`<span>Budget <strong>${escapeHtml(budget)}</strong></span>`);
  }
  if (state.selected_product_ids && state.selected_product_ids.length) {
    parts.push(`<span>Bag <strong>${state.selected_product_ids.length}</strong></span>`);
  }
  if (state.size) {
    parts.push(`<span>Size <strong>${escapeHtml(state.size)}</strong></span>`);
  }

  if (!parts.length) {
    stateSlotsDisplay.hidden = true;
    stateSlotsDisplay.innerHTML = "";
    return;
  }

  stateSlotsDisplay.hidden = false;
  stateSlotsDisplay.innerHTML = parts.join('<span class="session-sep" aria-hidden="true">·</span>');
}

function startReservationTimer() {
  if (holdTimerInterval) clearInterval(holdTimerInterval);
  let secondsLeft = 15 * 60;
  holdTimerInterval = setInterval(() => {
    secondsLeft--;
    const timerEl = document.getElementById("live-timer");
    if (secondsLeft <= 0) {
      clearInterval(holdTimerInterval);
      if (timerEl) timerEl.innerText = "Hold expired";
      return;
    }
    const mins = Math.floor(secondsLeft / 60);
    const secs = secondsLeft % 60;
    const formatted = `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    if (timerEl) timerEl.innerText = `${formatted} remaining`;
  }, 1000);
}
