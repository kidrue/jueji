(function () {
  "use strict";
  if (document.body.dataset.page !== "local-reader") return;

  var LIMIT = 20 * 1024 * 1024;
  var fileInput = document.getElementById("old-file");
  var openButton = document.getElementById("open-old-file");
  var status = document.getElementById("old-status");
  var reader = document.getElementById("old-reader");
  var body = document.getElementById("old-chapter-body");
  var title = document.getElementById("old-chapter-title");
  var toc = document.getElementById("old-toc");
  var toggle = document.getElementById("old-toc-toggle");
  var resume = document.getElementById("old-resume");
  var mobile = window.matchMedia("(max-width: 780px)");
  var book = null;
  var entries = [];
  var current = 0;
  var ready = false;
  var requestNumber = 0;
  var saveTimer;
  var dbPromise;

  function message(text, error) {
    status.textContent = text;
    status.dataset.error = String(Boolean(error));
  }

  function database() {
    if (!dbPromise) dbPromise = new Promise(function (resolve, reject) {
      if (!window.indexedDB) { reject(new Error("Storage unavailable")); return; }
      var request = window.indexedDB.open("jueji-old-edition", 1);
      request.onupgradeneeded = function () { request.result.createObjectStore("books"); };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () { reject(request.error); };
      request.onblocked = function () { reject(new Error("Storage blocked")); };
    });
    return dbPromise;
  }

  function storedBook(value) {
    return database().then(function (db) {
      return new Promise(function (resolve, reject) {
        var transaction = db.transaction("books", value ? "readwrite" : "readonly");
        var store = transaction.objectStore("books");
        var request = value ? store.put(value, "current") : store.get("current");
        var result;
        request.onsuccess = function () { result = request.result; };
        transaction.oncomplete = function () { resolve(result); };
        transaction.onerror = transaction.onabort = function () { reject(transaction.error || new Error("Storage failed")); };
      });
    });
  }

  function fingerprint(text) {
    var hash = 2166136261;
    var other = 5381;
    for (var i = 0; i < text.length; i += 1) {
      hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
      other = Math.imul(other, 33) ^ text.charCodeAt(i);
    }
    return text.length + "-" + (hash >>> 0).toString(16) + "-" + (other >>> 0).toString(16);
  }

  function decode(buffer) {
    var bytes = new Uint8Array(buffer);
    if (bytes[0] === 255 && bytes[1] === 254) return new TextDecoder("utf-16le", { fatal: true }).decode(bytes);
    if (bytes[0] === 254 && bytes[1] === 255) return new TextDecoder("utf-16be", { fatal: true }).decode(bytes);
    try { return new TextDecoder("utf-8", { fatal: true }).decode(bytes); }
    catch (error) { return new TextDecoder("gb18030", { fatal: true }).decode(bytes); }
  }

  function splitText(text) {
    var heading = /^[^\S\r\n]*(?:(?:\d+[.、][^\S\r\n]*)?第[零〇一二三四五六七八九十百千两\d]+[章回卷部][^\r\n]{0,80}|(?:序章|楔子|尾声|后记|附录)(?:[ \t:：·、—][^\r\n]{0,80})?)[^\S\r\n]*$/gm;
    var matches = Array.from(text.matchAll(heading));
    if (!matches.length) return [{ title: "全文", body: text }];
    var result = [];
    if (text.slice(0, matches[0].index).trim()) result.push({ title: "书前文字", body: text.slice(0, matches[0].index) });
    matches.forEach(function (match, index) {
      var end = index + 1 < matches.length ? matches[index + 1].index : text.length;
      result.push({ title: match[0].trim(), body: text.slice(match.index + match[0].length, end) });
    });
    return result;
  }

  function readProgress() {
    try {
      var record = JSON.parse(localStorage.getItem("jueji-old-reading-" + book.id));
      if (!record || !Number.isInteger(record.chapter) || record.chapter < 0 || record.chapter >= entries.length ||
          !Number.isFinite(record.position) || record.position < 0 || record.position > 1) return null;
      return record;
    } catch (error) { return null; }
  }

  function position() {
    var rect = body.getBoundingClientRect();
    if (rect.bottom <= innerHeight && rect.top < innerHeight) return 1;
    return Math.max(0, Math.min(1, -rect.top / Math.max(1, rect.height - innerHeight)));
  }

  function saveProgress() {
    if (!ready || !book) return;
    var fraction = position();
    var percent = Math.round(fraction * 100);
    var progress = document.getElementById("old-progress");
    progress.value = percent;
    progress.textContent = percent + "%";
    document.getElementById("old-progress-label").textContent = percent + "%";
    try { localStorage.setItem("jueji-old-reading-" + book.id, JSON.stringify({ chapter: current, position: fraction })); }
    catch (error) { /* The file remains readable when storage is disabled. */ }
  }

  function setToc(open) {
    toc.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector("span").textContent = open ? "收起篇目目录" : "展开篇目目录";
  }

  function render(index, savedPosition, scroll) {
    saveProgress();
    ready = false;
    current = index;
    var entry = entries[index];
    title.textContent = entry.title;
    document.title = entry.title + " · 旧版爵迹";
    document.getElementById("old-chapter-details").textContent = "第 " + (index + 1) + " / " + entries.length + " 篇 · " + entry.body.replace(/\s/g, "").length.toLocaleString() + " 字";
    var fragment = document.createDocumentFragment();
    entry.body.split(/\r\n?|\n/).forEach(function (line) {
      if (!line.trim()) return;
      var paragraph = document.createElement("p");
      paragraph.textContent = line;
      fragment.appendChild(paragraph);
    });
    body.replaceChildren(fragment);
    toc.querySelectorAll("a").forEach(function (link, number) {
      if (number === index) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    ["old-prev", "old-next"].forEach(function (id, direction) {
      var next = index + (direction ? 1 : -1);
      var button = document.getElementById(id);
      button.disabled = next < 0 || next >= entries.length;
      button.querySelector("strong").textContent = entries[next] ? entries[next].title : direction ? "已读至文件末尾" : "已是文件首篇";
    });
    resume.textContent = "继续阅读 · " + entry.title;
    if (mobile.matches) setToc(false);
    requestAnimationFrame(function () {
      if (scroll) {
        var rect = body.getBoundingClientRect();
        var top = savedPosition > 0 ? window.scrollY + rect.top + savedPosition * Math.max(0, rect.height - innerHeight) : window.scrollY + title.getBoundingClientRect().top - 30;
        window.scrollTo({ top: Math.max(0, top), behavior: "instant" });
      }
      ready = true;
      saveProgress();
    });
  }

  function hashIndex() {
    var match = window.location.hash.match(/^#chapter-(\d+)$/);
    var index = match ? Number(match[1]) - 1 : -1;
    return Number.isInteger(index) && index >= 0 && index < entries.length ? index : null;
  }

  function choose(index) {
    if (!book || index < 0 || index >= entries.length) return;
    history.pushState(null, "", "#chapter-" + (index + 1));
    render(index, 0, true);
    title.focus({ preventScroll: true });
  }

  function loadBook(value, restored) {
    saveProgress();
    ready = false;
    book = value;
    entries = splitText(value.text);
    document.getElementById("old-file-name").textContent = value.name;
    document.getElementById("old-entry-count").textContent = entries.length + " 篇";
    var fragment = document.createDocumentFragment();
    entries.forEach(function (entry, index) {
      var link = document.createElement("a");
      link.className = "toc-link";
      link.href = "#chapter-" + (index + 1);
      link.textContent = String(index + 1).padStart(3, "0") + "  " + entry.title;
      link.addEventListener("click", function (event) { event.preventDefault(); choose(index); });
      fragment.appendChild(link);
    });
    toc.replaceChildren(fragment);
    reader.hidden = false;
    openButton.textContent = "更换旧版 TXT ＋";
    resume.hidden = false;
    var saved = readProgress();
    var hash = restored ? hashIndex() : null;
    var index = hash !== null ? hash : saved ? saved.chapter : 0;
    if (!restored) history.replaceState(null, "", "#chapter-" + (index + 1));
    render(index, saved && saved.chapter === index ? saved.position : 0, !restored || hash !== null || Boolean(saved));
    setToc(!mobile.matches);
  }

  openButton.addEventListener("click", function () { fileInput.click(); });
  fileInput.addEventListener("change", async function () {
    var file = fileInput.files[0];
    if (!file) return;
    var request = ++requestNumber;
    fileInput.value = "";
    if (!/\.txt$/i.test(file.name)) { message("请选择 .txt 文本文件。当前阅读内容已保留。", true); return; }
    if (!file.size || file.size > LIMIT) { message("请选择非空、20 MB 以内的 TXT。当前阅读内容已保留。", true); return; }
    message("正在读取本地文件……");
    try {
      var text = decode(await file.arrayBuffer()).replace(/^\uFEFF/, "");
      if (request !== requestNumber) return;
      if (!text.trim() || /[\u0000-\u0008\u000e-\u001f]/.test(text)) throw new Error("Invalid text");
      var value = { name: file.name.slice(0, 240), text: text, id: fingerprint(text) };
      loadBook(value, false);
      try {
        await storedBook(value);
        if (request === requestNumber) message("已导入 " + value.name + "，共 " + entries.length + " 篇。文件已保存在此浏览器，刷新后可继续。浏览器清理数据后需重新导入。");
      } catch (error) {
        if (request === requestNumber) message("已打开 " + value.name + "。浏览器无法保存本次文件，刷新后请重新导入。");
      }
    } catch (error) {
      if (request === requestNumber) message("未能读取该文本。请使用 UTF-8、GB18030 或带标记的 UTF-16 TXT；当前阅读内容已保留。", true);
    }
  });

  resume.addEventListener("click", function (event) { event.preventDefault(); render(current, position(), true); title.focus({ preventScroll: true }); });
  document.getElementById("old-prev").addEventListener("click", function () { choose(current - 1); });
  document.getElementById("old-next").addEventListener("click", function () { choose(current + 1); });
  toggle.addEventListener("click", function () { setToc(toggle.getAttribute("aria-expanded") !== "true"); });
  function syncToc() { setToc(!mobile.matches); }
  if (mobile.addEventListener) mobile.addEventListener("change", syncToc);
  else if (mobile.addListener) mobile.addListener(syncToc);

  function adjustFont(change) {
    var size = Number.parseInt(document.documentElement.style.getPropertyValue("--reading-size"), 10) || 22;
    size = change === 0 ? 22 : Math.max(18, Math.min(28, size + change));
    document.documentElement.style.setProperty("--reading-size", size + "px");
    document.getElementById("font-reset").textContent = String(size);
    document.getElementById("font-reset").setAttribute("aria-label", "当前字号 " + size + " 像素，恢复为默认 22 像素");
    document.getElementById("font-minus").disabled = size <= 18;
    document.getElementById("font-plus").disabled = size >= 28;
    try { localStorage.setItem("jueji-font-size", String(size)); } catch (error) { /* Optional setting. */ }
  }
  document.getElementById("font-minus").addEventListener("click", function () { adjustFont(-2); });
  document.getElementById("font-plus").addEventListener("click", function () { adjustFont(2); });
  document.getElementById("font-reset").addEventListener("click", function () { adjustFont(0); });

  window.addEventListener("scroll", function () { clearTimeout(saveTimer); saveTimer = setTimeout(saveProgress, 150); }, { passive: true });
  window.addEventListener("resize", saveProgress, { passive: true });
  window.addEventListener("pagehide", saveProgress);
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") saveProgress(); });
  window.addEventListener("hashchange", function () { var index = hashIndex(); if (book && index !== null) render(index, 0, true); });
  document.addEventListener("keydown", function (event) {
    if (!book || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.target instanceof Element && (event.target.isContentEditable || event.target.closest("input, textarea, select, button, a, summary, [contenteditable]"))) return;
    event.preventDefault();
    choose(current + (event.key === "ArrowRight" ? 1 : -1));
  });

  var restoreRequest = requestNumber;
  storedBook().then(function (value) {
    if (restoreRequest !== requestNumber || !value) return;
    if (typeof value.text !== "string" || !value.text.trim() || value.text.length > LIMIT || typeof value.name !== "string" || value.id !== fingerprint(value.text)) return;
    loadBook(value, true);
    message("已恢复 " + value.name + "，可继续上次阅读。正文仅保存在当前浏览器。");
  }).catch(function () { message("尚未导入旧版全文。此浏览器无法保存文件，导入后仍可阅读。"); });
}());
