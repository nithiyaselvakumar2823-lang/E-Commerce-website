// ============================================================================
// Fieldstore front end — talks to the Flask REST API defined in app.py.
// No frameworks: plain fetch() + DOM updates, organised by feature.
// ============================================================================

const state = {
  user: null,
  products: [],
  categories: [],
  activeCategory: "All",
  searchTerm: "",
  cart: { items: [], subtotal: 0 },
  currentTab: "products",
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function money(n) {
  return "\u20B9" + Number(n).toFixed(2);
}

function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("toast-error", isError);
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 3200);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    throw new Error(data.error || "Something went wrong. Please try again.");
  }
  return data;
}

// ----------------------------------------------------------------------------
// Navigation
// ----------------------------------------------------------------------------
function setView(name) {
  if (name === "login" || name === "register") { openModal(name); return; }
  if ((name === "orders") && !state.user) { openModal("login"); return; }
  if (name === "admin" && (!state.user || state.user.role !== "admin")) { openModal("login"); return; }

  $$(".view").forEach(v => v.hidden = true);
  const target = $(`#view-${name}`);
  if (target) target.hidden = false;
  $$(".nav-link").forEach(b => b.classList.toggle("active", b.dataset.nav === name));

  if (name === "orders") loadOrders();
  if (name === "admin") loadAdmin();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$$("[data-nav]").forEach(el => {
  el.addEventListener("click", () => {
    if (el.id === "auth-btn" && state.user) return; // handled elsewhere
    setView(el.dataset.nav);
  });
});

// ----------------------------------------------------------------------------
// Auth
// ----------------------------------------------------------------------------
function applyAuthUI() {
  const authBtn = $("#auth-btn");
  const chip = $("#user-chip");
  const navOrders = $("#nav-orders");
  const navAdmin = $("#nav-admin");

  if (state.user) {
    authBtn.hidden = true;
    chip.hidden = false;
    chip.textContent = `${state.user.username} · sign out`;
    navOrders.hidden = false;
    navAdmin.hidden = state.user.role !== "admin";
  } else {
    authBtn.hidden = false;
    chip.hidden = true;
    navOrders.hidden = true;
    navAdmin.hidden = true;
  }
}

$("#user-chip").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  state.user = null;
  state.cart = { items: [], subtotal: 0 };
  updateCartBadge();
  applyAuthUI();
  setView("shop");
  toast("Signed out.");
});

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errEl = $("#login-error");
  errEl.textContent = "";
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
    });
    state.user = data.user;
    applyAuthUI();
    closeModal();
    e.target.reset();
    await refreshCart();
    toast(`Welcome back, ${state.user.username}.`);
  } catch (err) {
    errEl.textContent = err.message;
  }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errEl = $("#register-error");
  errEl.textContent = "";
  try {
    const data = await api("/api/register", {
      method: "POST",
      body: JSON.stringify({
        username: form.get("username"),
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    state.user = data.user;
    applyAuthUI();
    closeModal();
    e.target.reset();
    toast(`Account created. Welcome, ${state.user.username}.`);
  } catch (err) {
    errEl.textContent = err.message;
  }
});

// ----------------------------------------------------------------------------
// Modals
// ----------------------------------------------------------------------------
function openModal(which) {
  $("#modal-overlay").hidden = false;
  $$(".modal", $("#modal-overlay")).forEach(m => m.hidden = true);
  const el = $(`#modal-${which}`);
  if (el) el.hidden = false;
}
function closeModal() {
  $("#modal-overlay").hidden = true;
  $$(".form-error").forEach(e => e.textContent = "");
}
$("#modal-overlay").addEventListener("click", (e) => { if (e.target.id === "modal-overlay") closeModal(); });
$$("[data-close]").forEach(b => b.addEventListener("click", closeModal));
$$("[data-switch]").forEach(b => b.addEventListener("click", () => openModal(b.dataset.switch)));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeModal(); closeCart(); } });

// ----------------------------------------------------------------------------
// Products / catalog
// ----------------------------------------------------------------------------
async function loadProducts() {
  const params = new URLSearchParams();
  if (state.activeCategory !== "All") params.set("category", state.activeCategory);
  if (state.searchTerm) params.set("search", state.searchTerm);
  const data = await api(`/api/products?${params.toString()}`);
  state.products = data.products;
  state.categories = data.categories;
  renderChips();
  renderProducts();
}

function renderChips() {
  const row = $("#category-chips");
  const cats = ["All", ...state.categories];
  row.innerHTML = cats.map(c =>
    `<button class="chip ${c === state.activeCategory ? "active" : ""}" data-cat="${c}">${c}</button>`
  ).join("");
  $$(".chip", row).forEach(b => b.addEventListener("click", () => {
    state.activeCategory = b.dataset.cat;
    loadProducts();
  }));
}

function renderProducts() {
  const grid = $("#product-grid");
  const empty = $("#empty-note");
  if (state.products.length === 0) {
    grid.innerHTML = "";
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  grid.innerHTML = state.products.map(p => {
    const lowStock = p.stock > 0 && p.stock <= 5;
    const outOfStock = p.stock === 0;
    const img = p.image_url || "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600";
    return `
    <article class="product-card">
      <div class="product-media">
        <img src="${escapeHtml(img)}" alt="${escapeHtml(p.name)}" loading="lazy">
        ${outOfStock ? `<span class="stock-badge low">Sold out</span>` :
          lowStock ? `<span class="stock-badge low">Only ${p.stock} left</span>` : ""}
      </div>
      <div class="product-body">
        <div class="product-category">${escapeHtml(p.category)}</div>
        <div class="product-name">${escapeHtml(p.name)}</div>
        <div class="product-desc">${escapeHtml(p.description)}</div>
        <div class="product-footer">
          <span class="price-tag">${money(p.price)}</span>
          <button class="add-btn" data-add="${p.id}" ${outOfStock ? "disabled" : ""} title="Add to cart">+</button>
        </div>
      </div>
    </article>`;
  }).join("");

  $$("[data-add]", grid).forEach(btn => {
    btn.addEventListener("click", () => addToCart(Number(btn.dataset.add)));
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

let searchDebounce;
$("#search-input").addEventListener("input", (e) => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    state.searchTerm = e.target.value.trim();
    loadProducts();
  }, 250);
});

// ----------------------------------------------------------------------------
// Cart
// ----------------------------------------------------------------------------
function updateCartBadge() {
  const count = state.cart.items.reduce((s, i) => s + i.quantity, 0);
  const badge = $("#cart-count");
  badge.hidden = count === 0;
  badge.textContent = count;
}

async function refreshCart() {
  if (!state.user) { state.cart = { items: [], subtotal: 0 }; updateCartBadge(); return; }
  const data = await api("/api/cart");
  state.cart = data;
  updateCartBadge();
}

function renderCartDrawer() {
  const wrap = $("#cart-items");
  if (state.cart.items.length === 0) {
    wrap.innerHTML = `<p class="cart-empty">Your cart is empty. Go find something good.</p>`;
  } else {
    wrap.innerHTML = state.cart.items.map(i => `
      <div class="cart-item">
        <img src="${escapeHtml(i.image_url || "")}" alt="">
        <div class="cart-item-info">
          <div class="name">${escapeHtml(i.name)}</div>
          <div class="price">${money(i.price)}</div>
          <div class="qty-control">
            <button data-qty-down="${i.cart_item_id}">−</button>
            <span>${i.quantity}</span>
            <button data-qty-up="${i.cart_item_id}" ${i.quantity >= i.stock ? "disabled" : ""}>+</button>
          </div>
          <button class="remove-link" data-remove="${i.cart_item_id}">Remove</button>
        </div>
      </div>`).join("");
  }
  $("#cart-subtotal").textContent = money(state.cart.subtotal);

  $$("[data-qty-up]", wrap).forEach(b => b.addEventListener("click", () => changeQty(Number(b.dataset.qtyUp), 1)));
  $$("[data-qty-down]", wrap).forEach(b => b.addEventListener("click", () => changeQty(Number(b.dataset.qtyDown), -1)));
  $$("[data-remove]", wrap).forEach(b => b.addEventListener("click", () => removeCartItem(Number(b.dataset.remove))));
}

async function addToCart(productId) {
  if (!state.user) { openModal("login"); toast("Sign in to add items to your cart.", true); return; }
  try {
    const data = await api("/api/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: 1 }) });
    state.cart = data;
    updateCartBadge();
    renderCartDrawer();
    toast("Added to cart.");
    openCart();
  } catch (err) {
    toast(err.message, true);
  }
}

async function changeQty(cartItemId, delta) {
  const item = state.cart.items.find(i => i.cart_item_id === cartItemId);
  if (!item) return;
  const newQty = item.quantity + delta;
  try {
    const data = await api(`/api/cart/${cartItemId}`, { method: "PUT", body: JSON.stringify({ quantity: newQty }) });
    state.cart = data;
    updateCartBadge();
    renderCartDrawer();
  } catch (err) {
    toast(err.message, true);
  }
}

async function removeCartItem(cartItemId) {
  const data = await api(`/api/cart/${cartItemId}`, { method: "DELETE" });
  state.cart = data;
  updateCartBadge();
  renderCartDrawer();
}

function openCart() {
  renderCartDrawer();
  $("#cart-drawer").classList.add("open");
  $("#drawer-overlay").hidden = false;
}
function closeCart() {
  $("#cart-drawer").classList.remove("open");
  $("#drawer-overlay").hidden = true;
}
$("#cart-toggle").addEventListener("click", openCart);
$("#close-cart").addEventListener("click", closeCart);
$("#drawer-overlay").addEventListener("click", closeCart);

$("#checkout-btn").addEventListener("click", () => {
  if (!state.user) { openModal("login"); return; }
  if (state.cart.items.length === 0) { toast("Your cart is empty.", true); return; }
  $("#checkout-summary").innerHTML = `<span>${state.cart.items.length} item(s)</span><span>${money(state.cart.subtotal)}</span>`;
  closeCart();
  openModal("checkout");
});

$("#checkout-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errEl = $("#checkout-error");
  errEl.textContent = "";
  try {
    const data = await api("/api/orders/checkout", {
      method: "POST",
      body: JSON.stringify({ shipping_address: form.get("shipping_address") }),
    });
    closeModal();
    e.target.reset();
    await refreshCart();
    loadProducts();
    toast(`Order #${data.order.id} placed. Thank you!`);
    setView("orders");
  } catch (err) {
    errEl.textContent = err.message;
  }
});

// ----------------------------------------------------------------------------
// Orders (customer)
// ----------------------------------------------------------------------------
async function loadOrders() {
  const data = await api("/api/orders");
  const list = $("#order-list");
  if (data.orders.length === 0) {
    list.innerHTML = `<div class="empty-state">No orders yet — your first one is one click away.</div>`;
    return;
  }
  list.innerHTML = data.orders.map(o => `
    <div class="order-card" data-order="${o.id}">
      <div class="oc-left">
        <span class="oc-id">Order #${o.id}</span>
        <span class="oc-date">${formatDate(o.created_at)}</span>
      </div>
      <span class="status-pill status-${o.status}">${o.status}</span>
      <span class="oc-total">${money(o.total_amount)}</span>
    </div>`).join("");
  $$("[data-order]", list).forEach(c => c.addEventListener("click", () => openOrderDetail(Number(c.dataset.order))));
}

async function openOrderDetail(orderId) {
  const data = await api(`/api/orders/${orderId}`);
  $("#order-detail-title").textContent = `Order #${data.order.id}`;
  $("#order-detail-body").innerHTML = `
    <p class="cart-item-info price" style="margin-bottom:14px;">
      <span class="status-pill status-${data.order.status}">${data.order.status}</span>
      &nbsp; ${formatDate(data.order.created_at)}
    </p>
    <div style="margin-bottom:14px; font-size:0.86rem; color:var(--ink-soft);">
      Shipping to: ${escapeHtml(data.order.shipping_address)}
    </div>
    ${data.items.map(i => `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="name">${escapeHtml(i.product_name)} × ${i.quantity}</div>
          <div class="price">${money(i.price_at_purchase)} each</div>
        </div>
      </div>`).join("")}
    <div class="cart-subtotal" style="margin-top:14px;">
      <span>Total</span><span>${money(data.order.total_amount)}</span>
    </div>`;
  openModal("order-detail");
}

function formatDate(s) {
  const d = new Date(s.replace(" ", "T") + "Z");
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

// ----------------------------------------------------------------------------
// Admin
// ----------------------------------------------------------------------------
$$(".admin-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    state.currentTab = tab.dataset.tab;
    $$(".admin-tab").forEach(t => t.classList.toggle("active", t === tab));
    $("#admin-products").hidden = state.currentTab !== "products";
    $("#admin-orders").hidden = state.currentTab !== "orders";
    if (state.currentTab === "orders") loadAdminOrders();
  });
});

async function loadAdmin() {
  const stats = await api("/api/admin/stats");
  $("#stat-row").innerHTML = `
    <div class="stat-card"><div class="stat-label">Revenue</div><div class="stat-value">${money(stats.revenue)}</div></div>
    <div class="stat-card"><div class="stat-label">Orders</div><div class="stat-value">${stats.order_count}</div></div>
    <div class="stat-card"><div class="stat-label">Products</div><div class="stat-value">${stats.product_count}</div></div>
    <div class="stat-card"><div class="stat-label">Users</div><div class="stat-value">${stats.user_count}</div></div>
  `;
  await loadAdminProducts();
}

async function loadAdminProducts() {
  const data = await api("/api/products");
  const rows = $("#admin-product-rows");
  rows.innerHTML = data.products.map(p => `
    <tr>
      <td>
        <div class="table-product-cell">
          <img src="${escapeHtml(p.image_url || "")}" alt="">
          <span>${escapeHtml(p.name)}</span>
        </div>
      </td>
      <td>${escapeHtml(p.category)}</td>
      <td>${money(p.price)}</td>
      <td class="${p.stock <= 5 ? "low-stock-flag" : ""}">${p.stock}</td>
      <td><button class="btn btn-ghost btn-small" data-edit="${p.id}">Edit</button></td>
    </tr>`).join("");
  $$("[data-edit]", rows).forEach(b => b.addEventListener("click", () => openProductModal(Number(b.dataset.edit))));
}

async function loadAdminOrders() {
  const data = await api("/api/orders?all=1");
  const rows = $("#admin-order-rows");
  rows.innerHTML = data.orders.map(o => `
    <tr>
      <td>#${o.id}</td>
      <td>${escapeHtml(o.username)}</td>
      <td>${money(o.total_amount)}</td>
      <td>
        <select class="status-select" data-status="${o.id}">
          ${["Pending", "Processing", "Shipped", "Delivered", "Cancelled"].map(s =>
            `<option value="${s}" ${s === o.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
      </td>
      <td>${formatDate(o.created_at)}</td>
      <td><button class="btn btn-ghost btn-small" data-view-order="${o.id}">View</button></td>
    </tr>`).join("");

  $$("[data-status]", rows).forEach(sel => sel.addEventListener("change", async () => {
    try {
      await api(`/api/admin/orders/${sel.dataset.status}/status`, {
        method: "PUT", body: JSON.stringify({ status: sel.value }),
      });
      toast(`Order #${sel.dataset.status} marked ${sel.value}.`);
    } catch (err) { toast(err.message, true); }
  }));
  $$("[data-view-order]", rows).forEach(b => b.addEventListener("click", () => openOrderDetail(Number(b.dataset.viewOrder))));
}

function openProductModal(productId) {
  const form = $("#product-form");
  form.reset();
  $("#product-error").textContent = "";
  $("#delete-product-btn").hidden = !productId;

  if (productId) {
    const p = state.products.find(x => x.id === productId) || {};
    $("#product-modal-tag").textContent = "Edit product";
    $("#product-modal-title").textContent = p.name || "Edit product";
    form.id.value = p.id;
    form.name.value = p.name || "";
    form.description.value = p.description || "";
    form.price.value = p.price ?? "";
    form.stock.value = p.stock ?? "";
    form.category.value = p.category || "";
    form.image_url.value = p.image_url || "";
  } else {
    $("#product-modal-tag").textContent = "Add product";
    $("#product-modal-title").textContent = "New product";
    form.id.value = "";
  }
  openModal("product");
}
$("#new-product-btn").addEventListener("click", () => openProductModal(null));

$("#product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const id = form.get("id");
  const payload = {
    name: form.get("name"),
    description: form.get("description"),
    price: form.get("price"),
    stock: form.get("stock"),
    category: form.get("category"),
    image_url: form.get("image_url"),
  };
  const errEl = $("#product-error");
  errEl.textContent = "";
  try {
    if (id) {
      await api(`/api/products/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("Product updated.");
    } else {
      await api("/api/products", { method: "POST", body: JSON.stringify(payload) });
      toast("Product created.");
    }
    closeModal();
    await loadProducts();
    await loadAdminProducts();
  } catch (err) {
    errEl.textContent = err.message;
  }
});

$("#delete-product-btn").addEventListener("click", async () => {
  const id = $("#product-form").id.value;
  if (!id) return;
  if (!confirm("Delete this product? This cannot be undone.")) return;
  try {
    await api(`/api/products/${id}`, { method: "DELETE" });
    toast("Product deleted.");
    closeModal();
    await loadProducts();
    await loadAdminProducts();
  } catch (err) {
    toast(err.message, true);
  }
});

// ----------------------------------------------------------------------------
// Boot
// ----------------------------------------------------------------------------
async function boot() {
  try {
    const me = await api("/api/me");
    state.user = me.user;
  } catch (e) { state.user = null; }
  applyAuthUI();
  await loadProducts();
  await refreshCart();
  setView("shop");
}
boot();
