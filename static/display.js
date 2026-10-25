"use strict";
let state = null, slides = [], index = 0, timer = null, lastOk = 0, nextAt = 0, wakeUntil = 0, serverOffset = 0;
const stage = document.querySelector("#stage");
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const zonedTime = date => new Intl.DateTimeFormat("hu-HU", {timeZone:"Europe/Budapest", hour:"2-digit", minute:"2-digit", hourCycle:"h23"}).format(date);
function ageText(stamp) {
  if (!stamp) return "Nincs adatkapcsolat";
  const age = Math.max(0, (Date.now() + serverOffset - new Date(stamp).getTime()) / 1000);
  if (age < 60) return "Most frissült";
  if (age < 3600) return `${Math.floor(age / 60)} perce frissült`;
  if (age < 86400) return `${Math.floor(age / 3600)} órája frissült`;
  return `${Math.floor(age / 86400)} napja frissült`;
}
function cardHtml(card) {
  const hasValue = card.value !== null;
  let value = "—";
  if (hasValue) value = card.unit === "number" ? new Intl.NumberFormat("hu-HU", {maximumFractionDigits:2}).format(Number(card.value)) : card.value;
  const stale = hasValue && ["codex","browser"].includes(card.source) && (!card.updated_at || Date.now() + serverOffset - new Date(card.updated_at).getTime() > 600000);
  const source = card.source === "manual" ? "Kézzel megadva" : card.source === "browser" ? "Chrome" : card.source === "codex" ? (hasValue ? "Codex" : "Nincs ilyen keretadat") : "Bekötésre vár";
  let reset = card.resets_at ? `Új keret: ${new Intl.DateTimeFormat("hu-HU",{timeZone:"Europe/Budapest",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}).format(new Date(card.resets_at))}` : "";
  if (card.unit === "percent" && hasValue && !reset) reset = "maradék keret";
  const color = /^#[0-9a-f]{6}$/i.test(card.color) ? card.color : "#b8f28b";
  // Color and width are set through the CSSOM below, to keep the CSP free of inline styles.
  return `<article class="metric${slides[index]?.cards?.length === 1 ? " single" : ""}" data-color="${color}" data-percent="${card.unit === "percent" && hasValue ? Number(card.value) : -1}"><span class="eyebrow">${escapeHtml(card.category)}</span><h2>${escapeHtml(card.label)}</h2><div class="value${String(value).length > 7 ? " small" : ""}">${escapeHtml(value)}${card.unit === "percent" && hasValue ? '<span class="unit">%</span>' : ""}</div>${card.unit === "percent" && hasValue ? '<div class="bar"><span></span></div>' : ""}<div class="detail${stale ? " warn" : ""}">${escapeHtml(stale ? "Régi adat · " + ageText(card.updated_at) : hasValue ? source + " · " + ageText(card.updated_at) : source)}</div><div class="reset">${escapeHtml(reset)}</div></article>`;
}
function applyMetrics() {
  stage.querySelectorAll(".metric").forEach(card => {
    card.style.setProperty("--accent", card.dataset.color);
    const bar = card.querySelector(".bar span");
    if (bar) bar.style.width = Math.min(100, Math.max(0, Number(card.dataset.percent))) + "%";
    const value = card.querySelector(".value");
    // Keep larger numbers readable even with long values or increased text size.
    let size = parseFloat(getComputedStyle(value).fontSize);
    while ((value.scrollWidth > value.clientWidth || value.scrollHeight > value.clientHeight) && size > 20) {
      size -= 1;
      value.style.fontSize = size + "px";
    }
  });
}
function rebuildSlides() {
  const stats = [];
  // Plans with a single quota must not show a second, nonexistent allowance.
  const cards = state.cards.filter(card => !(card.source === "codex" && card.value === null));
  for (let i = 0; i < cards.length; i += 2) stats.push({type:"metrics", cards:cards.slice(i, i + 2)});
  const photos = state.photos.map(photo => ({type:"photo", photo}));
  if (state.settings.mode === "dashboard") slides = stats;
  else if (state.settings.mode === "photos") slides = photos;
  else {
    slides = [];
    for (let i = 0; i < Math.max(stats.length, photos.length); i++) {
      if (stats[i]) slides.push(stats[i]);
      if (photos[i]) slides.push(photos[i]);
    }
  }
  index = index % Math.max(slides.length, 1);
}
function render(schedule = true) {
  if (!state) return;
  document.querySelector("#title").textContent = state.settings.title;
  document.documentElement.style.setProperty("--scale", state.settings.font_scale / 100);
  document.body.classList.toggle("portrait", state.settings.orientation === "portrait");
  if (state.needs_setup && state.setup_code) {
    stage.innerHTML = `<div class="empty"><span class="eyebrow">ÜDV A MINI PI-ON</span><h1>Állítsd be telefonról</h1><div class="setup-code">${escapeHtml(state.setup_code)}</div><p>Egyszer használatos adminbeállítási kód</p><span class="setup-address">${escapeHtml(state.admin_url || "A Pi IP-címe:8080/admin")}</span></div>`;
  } else if (!slides.length) {
    stage.innerHTML = `<div class="empty"><span class="eyebrow">A TE KIJELZŐD</span><h1>${state.settings.mode === "photos" ? "Jöhetnek a képek" : "Készen áll a Mini PI"}</h1><p>${state.settings.mode === "photos" ? "Tölts fel egy fotót az adminban." : "Kapcsolj be egy kártyát az adminban."}</p></div>`;
  } else {
    const slide = slides[index];
    if (slide.type === "metrics") { stage.innerHTML = `<div class="metrics">${slide.cards.map(cardHtml).join("")}</div>`; applyMetrics(); }
    else {
      stage.innerHTML = `<div class="photo"><img alt="${escapeHtml(slide.photo.caption || "Képkeret fotó")}" src="${escapeHtml(slide.photo.url)}">${slide.photo.caption ? `<div class="caption">${escapeHtml(slide.photo.caption)}</div>` : ""}</div>`;
      stage.querySelector("img").style.objectFit = state.settings.photo_fit;
    }
  }
  document.querySelector("#pages").innerHTML = slides.map((_, i) => `<span class="${i === index ? "active" : ""}"></span>`).join("");
  if (schedule) {
    clearTimeout(timer);
    const seconds = slides[index]?.type === "photo" ? state.settings.photo_seconds : state.settings.slide_seconds;
    nextAt = Date.now() + seconds * 1000;
    timer = setTimeout(() => { index = (index + 1) % Math.max(slides.length, 1); render(); }, seconds * 1000);
  }
}
function tick() {
  const date = new Date(Date.now() + serverOffset);
  document.querySelector("#clock").textContent = zonedTime(date);
  document.querySelector("#night time").textContent = zonedTime(date);
  document.querySelector("#date").textContent = new Intl.DateTimeFormat("hu-HU", {timeZone:"Europe/Budapest",month:"short",day:"numeric",weekday:"short"}).format(date);
  document.body.classList.toggle("night-blank", state?.settings.night_mode === "blank");
  const connection = document.querySelector("#connection");
  const offline = !lastOk || Date.now() - lastOk > 20000;
  connection.classList.toggle("offline", offline);
  connection.innerHTML = `<i></i>${offline ? "Kapcsolat szünetel" : "Mini PI · helyi"}`;
  if (state?.settings.night_enabled && !state.needs_setup) {
    const current = zonedTime(date), start = state.settings.night_start, end = state.settings.night_end;
    const asleep = start === end || (start < end ? current >= start && current < end : current >= start || current < end);
    document.body.classList.toggle("sleeping", asleep && Date.now() > wakeUntil);
  } else document.body.classList.remove("sleeping");
}
async function refresh() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    let response;
    try { response = await fetch("/api/display", {cache:"no-store", signal:controller.signal}); }
    finally { clearTimeout(timeout); }
    if (!response.ok) throw new Error("HTTP " + response.status);
    const fresh = await response.json();
    serverOffset = new Date(fresh.server_time).getTime() - Date.now();
    // Cache no credentials or one-time setup code. Only display data and photo URLs are stored.
    const cache = {...fresh, setup_code:null};
    try { localStorage.setItem("mini-pi-cache", JSON.stringify(cache)); } catch (_) {}
    const changed = !state || JSON.stringify({...fresh,server_time:null}) !== JSON.stringify({...state,server_time:null});
    state = fresh; lastOk = Date.now();
    if (changed) { rebuildSlides(); render(); }
    else if (slides[index]?.type === "metrics") render(false);
    tick();
  } catch (_) { tick(); }
}
try { const saved = JSON.parse(localStorage.getItem("mini-pi-cache")); if (saved?.settings) { state=saved; rebuildSlides(); render(); } } catch (_) {}
document.addEventListener("pointerdown", () => {
  if (document.body.classList.contains("sleeping")) { wakeUntil=Date.now()+30000; tick(); }
  else if (slides.length > 1) { index=(index+1)%slides.length; render(); }
});
document.addEventListener("keydown", event => {
  if (["ArrowRight"," ","ArrowLeft"].includes(event.key) && slides.length) { index=(index+(event.key==="ArrowLeft"?-1:1)+slides.length)%slides.length; render(); }
});
refresh(); tick(); setInterval(refresh,5000); setInterval(tick,1000);
