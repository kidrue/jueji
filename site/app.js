(function () {
  "use strict";

  var root = document.documentElement;
  var page = document.body.dataset.page;
  var originalBook = document.body.dataset.book === "original";
  var MIN_CHAPTER = originalBook ? Number(document.body.dataset.minChapter) : 169;
  var MAX_CHAPTER = originalBook ? Number(document.body.dataset.maxChapter) : 193;
  var DEFAULT_SIZE = 22;
  var MIN_SIZE = 18;
  var MAX_SIZE = 28;
  var themeKey = "jueji-theme";
  var fontKey = "jueji-font-size";
  var readingKey = originalBook ? "jueji-original-reading" : "jueji-reading";

  function readStorage(key) {
    try { return window.localStorage.getItem(key); } catch (error) { return null; }
  }

  function writeStorage(key, value) {
    try { window.localStorage.setItem(key, value); } catch (error) { /* Reading also works without browser storage. */ }
  }

  function validChapter(value) {
    return Number.isInteger(value) && value >= MIN_CHAPTER && value <= MAX_CHAPTER;
  }

  function readLastChapter() {
    try {
      var record = JSON.parse(readStorage(readingKey));
      if (!record || !validChapter(record.chapter) || typeof record.title !== "string" || record.title.length > 200) return null;
      if (!Number.isFinite(record.progress) || record.progress < 0 || record.progress > 100) return null;
      if (!Number.isFinite(record.scrollY) || record.scrollY < 0 || record.scrollY > 10000000) return null;
      return record;
    } catch (error) { return null; }
  }

  function validFontSize(value) {
    return Number.isInteger(value) && value >= MIN_SIZE && value <= MAX_SIZE && value % 2 === 0;
  }

  var savedSize = readStorage(fontKey);
  var fontSize = savedSize !== null && /^\d{2}$/.test(savedSize) && validFontSize(Number(savedSize)) ? Number(savedSize) : DEFAULT_SIZE;

  function applyFontSize(size, persist) {
    fontSize = validFontSize(size) ? size : DEFAULT_SIZE;
    root.style.setProperty("--reading-size", fontSize + "px");
    var minus = document.getElementById("font-minus");
    var plus = document.getElementById("font-plus");
    var reset = document.getElementById("font-reset");
    if (minus) minus.disabled = fontSize <= MIN_SIZE;
    if (plus) plus.disabled = fontSize >= MAX_SIZE;
    if (reset) {
      reset.textContent = String(fontSize);
      reset.setAttribute("aria-label", "当前字号 " + fontSize + " 像素，恢复为默认 22 像素");
    }
    if (persist) writeStorage(fontKey, String(fontSize));
  }

  function applyTheme(theme, persist) {
    var nextTheme = theme === "night" ? "night" : "paper";
    root.dataset.theme = nextTheme;
    var button = document.getElementById("theme-toggle");
    if (button) {
      var night = nextTheme === "night";
      button.setAttribute("aria-pressed", String(night));
      button.setAttribute("aria-label", night ? "切换为纸页阅读" : "切换为夜间阅读");
      var label = button.querySelector(".theme-label");
      if (label) label.textContent = night ? "纸页" : "夜读";
    }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = nextTheme === "night" ? "#1e2421" : "#f4f1e8";
    if (persist) writeStorage(themeKey, nextTheme);
  }

  applyTheme(readStorage(themeKey), false);
  applyFontSize(fontSize, false);
  root.classList.add("has-js");

  var themeButton = document.getElementById("theme-toggle");
  if (themeButton) themeButton.addEventListener("click", function () { applyTheme(root.dataset.theme === "night" ? "paper" : "night", true); });

  if (page === "document") {
    document.querySelectorAll(".site-nav a").forEach(function (link) {
      if (new URL(link.href, window.location.href).pathname === window.location.pathname) link.setAttribute("aria-current", "page");
    });
  }

  if (page === "home") {
    var savedReading = readLastChapter();
    var resume = document.getElementById("resume-link");
    var resumeLabel = document.getElementById("resume-label");
    if (savedReading && resume && resumeLabel) {
      resume.href = (originalBook ? "original" : "chapters") + "/chapter-" + savedReading.chapter + ".html";
      resumeLabel.textContent = originalBook ? "续读 · " + savedReading.title : "续读第 " + savedReading.chapter + " 回 · " + Math.round(savedReading.progress) + "%";
      resume.setAttribute("aria-label", "继续阅读，" + savedReading.title + "，上次进度 " + Math.round(savedReading.progress) + "%");
      resume.hidden = false;
    }

    var search = document.getElementById("chapter-search");
    var chapterCards = Array.from(document.querySelectorAll(".chapter-card"));
    var filters = Array.from(document.querySelectorAll("[data-stage-filter]"));
    var count = document.getElementById("chapter-count");
    var empty = document.getElementById("empty-state");
    var clear = document.getElementById("clear-search");
    var stage = "all";
    var allowedStages = ["all", "intro", "rescue", "truth", "ending"];

    function normalized(value) {
      return String(value || "").normalize("NFKC").toLowerCase().replace(/\s+/g, "");
    }

    function filterChapters() {
      var query = normalized(search ? search.value : "");
      var visible = 0;
      chapterCards.forEach(function (card) {
        var searchable = normalized(card.dataset.search || "第" + card.dataset.number + "回" + card.dataset.title);
        var matches = (stage === "all" || card.dataset.stage === stage) && searchable.indexOf(query) !== -1;
        card.hidden = !matches;
        if (matches) visible += 1;
      });
      filters.forEach(function (button) { button.setAttribute("aria-pressed", String(button.dataset.stageFilter === stage)); });
      var unit = originalBook ? " 篇" : " 回";
      if (count) count.textContent = query || stage !== "all" ? "显示 " + visible + " / " + chapterCards.length + unit : "共 " + chapterCards.length + unit;
      if (empty) empty.hidden = visible !== 0;
    }

    if (search) search.addEventListener("input", filterChapters);
    filters.forEach(function (button) {
      button.addEventListener("click", function () {
        if (allowedStages.indexOf(button.dataset.stageFilter) === -1) return;
        stage = button.dataset.stageFilter;
        filterChapters();
      });
    });
    if (clear) clear.addEventListener("click", function () {
      stage = "all";
      if (search) search.value = "";
      filterChapters();
      if (search) search.focus();
    });
    filterChapters();
  }

  if (page !== "chapter") return;

  var chapterNumber = Number(document.body.dataset.chapter);
  var chapterBody = document.getElementById("chapter-body");
  var chapterTitle = document.getElementById("chapter-title");
  var progress = document.getElementById("reading-progress");
  var progressLabel = document.getElementById("progress-label");
  var lastReading = readLastChapter();
  var readingProgress = 0;
  var ready = false;
  var framePending = false;
  var saveTimer = null;

  function saveReading() {
    if (!ready || !validChapter(chapterNumber) || !chapterTitle) return;
    writeStorage(readingKey, JSON.stringify({
      chapter: chapterNumber,
      title: chapterTitle.textContent.trim().slice(0, 200),
      progress: readingProgress,
      scrollY: Math.max(0, Math.min(window.scrollY || 0, 10000000))
    }));
  }

  function updateProgress() {
    framePending = false;
    if (!chapterBody) return;
    var rect = chapterBody.getBoundingClientRect();
    var top = rect.top + window.scrollY;
    var distance = Math.max(1, rect.height - window.innerHeight);
    readingProgress = Math.max(0, Math.min(100, Math.round(((window.scrollY - top) / distance) * 100)));
    if (rect.bottom <= window.innerHeight && rect.top < window.innerHeight) readingProgress = 100;
    if (progress) { progress.value = readingProgress; progress.textContent = readingProgress + "%"; }
    if (progressLabel) progressLabel.textContent = readingProgress + "%";
  }

  function scheduleProgress() {
    if (!framePending) {
      framePending = true;
      window.requestAnimationFrame(updateProgress);
    }
    if (saveTimer !== null) window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(function () { saveReading(); saveTimer = null; }, 300);
  }

  function adjustFont(size) {
    applyFontSize(size, true);
    scheduleProgress();
  }

  var fontMinus = document.getElementById("font-minus");
  var fontPlus = document.getElementById("font-plus");
  var fontReset = document.getElementById("font-reset");
  if (fontMinus) fontMinus.addEventListener("click", function () { adjustFont(fontSize - 2); });
  if (fontPlus) fontPlus.addEventListener("click", function () { adjustFont(fontSize + 2); });
  if (fontReset) fontReset.addEventListener("click", function () { adjustFont(DEFAULT_SIZE); });

  var tocToggle = document.getElementById("toc-toggle");
  var tocPanel = document.getElementById("toc-panel");
  var mobile = window.matchMedia("(max-width: 780px)");

  function setToc(open) {
    if (!tocToggle || !tocPanel) return;
    tocPanel.hidden = !open;
    tocToggle.setAttribute("aria-expanded", String(open));
    var label = tocToggle.querySelector("span:first-child");
    if (label) label.textContent = open ? "收起篇目目录" : "展开篇目目录";
    if (open) {
      var current = tocPanel.querySelector('[aria-current="page"]');
      if (current) tocPanel.scrollTop = Math.max(0, current.offsetTop - tocPanel.offsetTop - tocPanel.clientHeight / 3);
    }
  }

  function syncToc() { setToc(!mobile.matches); }
  if (tocToggle) tocToggle.addEventListener("click", function () { setToc(tocToggle.getAttribute("aria-expanded") !== "true"); });
  if (mobile.addEventListener) mobile.addEventListener("change", syncToc);
  else if (mobile.addListener) mobile.addListener(syncToc);
  syncToc();

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    var target = event.target;
    if (target instanceof Element && (target.isContentEditable || target.closest('input, textarea, select, button, a, summary, [contenteditable], [role="button"], [role="textbox"]'))) return;
    var link = document.getElementById(event.key === "ArrowLeft" ? "prev-chapter" : "next-chapter");
    if (!link) return;
    var url = new URL(link.href, window.location.href);
    var match = url.pathname.match(/\/chapter-(\d+)\.html$/);
    if (!match || !validChapter(Number(match[1])) || url.origin !== window.location.origin) return;
    event.preventDefault();
    saveReading();
    window.location.assign(url.href);
  });

  if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";

  function restoreReadingPosition() {
    if (lastReading && lastReading.chapter === chapterNumber && !window.location.hash && lastReading.scrollY > 0) {
      var maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      var previousBehavior = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";
      window.scrollTo(0, Math.min(lastReading.scrollY, maxScroll));
      root.style.scrollBehavior = previousBehavior;
    }
    ready = true;
    updateProgress();
    saveReading();
  }

  window.addEventListener("scroll", scheduleProgress, { passive: true });
  window.addEventListener("resize", scheduleProgress, { passive: true });
  window.addEventListener("pagehide", function () { updateProgress(); saveReading(); });
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") { updateProgress(); saveReading(); } });
  updateProgress();
  if (document.readyState === "complete") restoreReadingPosition();
  else window.addEventListener("load", restoreReadingPosition, { once: true });
}());
