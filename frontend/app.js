(() => {
  "use strict";
  const API = window.location.origin;
  const $ = (selector) => document.querySelector(selector);
  const els = {
    sidebar: $("#sidebar"), openSidebar: $("#openSidebar"), closeSidebar: $("#closeSidebar"),
    newChat: $("#newChat"), conversationList: $("#conversationList"), refreshSessions: $("#refreshSessions"),
    pageBreadcrumb: $("#pageBreadcrumb"), workspaceGrid: $("#workspaceGrid"), chatColumn: $("#chatColumn"),
    welcomeView: $("#welcomeView"), messagesList: $("#messagesList"), messageInput: $("#messageInput"),
    sendButton: $("#sendButton"), evidencePanel: $("#evidencePanel"), toggleSources: $("#toggleSources"),
    closeEvidence: $("#closeEvidence"), groundingStatus: $("#groundingStatus"),
    evidenceContent: $("#evidenceContent"), sourceCount: $("#sourceCount"), toast: $("#toast"),
    artifactView: $("#artifactView"), artifactText: $("#artifactText"), artifactName: $("#artifactName"),
    artifactWordCount: $("#artifactWordCount"), previewCanvas: $("#previewCanvas"), previewLabel: $("#previewLabel"),
    createArtifact: $("#createArtifact"), downloadArtifact: $("#downloadArtifact"), copyArtifact: $("#copyArtifact"),
    settingsButton: $("#settingsButton"), themeToggle: $("#themeToggle")
  };
  const state = {
    sessionId: null, sessions: [], messages: [], sources: [], grounded: false, lastAnswer: "",
    view: "chat", artifactTab: "markdown", artifactTitle: "Untitled growth brief",
    artifactContent: "", busy: false, toastTimer: null, abortController: null
  };
  const STORE_KEY = "lenny-growth-assistant.workspace.v1";
  const THEME_KEY = "lenny-growth-assistant.theme.v1";

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }
  function safeUrl(value) {
    try {
      const url = new URL(value, window.location.origin);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch { return ""; }
  }
  function markdownToHtml(value, citations = false) {
    let source = String(value ?? "").replace(/\r\n?/g, "\n");
    const codeBlocks = [];
    source = source.replace(/```([\w-]*)\n([\s\S]*?)```/g, (_, language, code) => {
      const token = `@@CODE${codeBlocks.length}@@`;
      codeBlocks.push(`<pre><code class="language-${escapeHtml(language)}">${escapeHtml(code.trimEnd())}</code></pre>`);
      return token;
    });
    source = escapeHtml(source);
    source = source.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
      const safe = safeUrl(url);
      return safe ? `<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label;
    });
    source = source.replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    if (citations) source = source.replace(/\[(\d{1,2})\]/g, '<button class="citation" data-source-index="$1" title="View source $1">[$1]</button>');
    const lines = source.split("\n");
    const output = [];
    let paragraph = [], listType = null, inQuote = false;
    const flushParagraph = () => {
      if (paragraph.length) { output.push(`<p>${paragraph.join("<br>")}</p>`); paragraph = []; }
    };
    const closeList = () => { if (listType) { output.push(`</${listType}>`); listType = null; } };
    const closeQuote = () => { if (inQuote) { output.push("</blockquote>"); inQuote = false; } };
    for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {\n      const line = lines[lineIndex];
      const codeMatch = line.match(/^@@CODE(\d+)@@$/);
      if (codeMatch) { flushParagraph(); closeList(); closeQuote(); output.push(codeBlocks[Number(codeMatch[1])] || ""); continue; }
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (heading) { flushParagraph(); closeList(); closeQuote(); const level = heading[1].length; output.push(`<h${level}>${heading[2]}</h${level}>`); continue; }
      if (unordered || ordered) {
        flushParagraph(); closeQuote(); const type = unordered ? "ul" : "ol";
        if (listType !== type) { closeList(); output.push(`<${type}>`); listType = type; }
        output.push(`<li>${(unordered || ordered)[1]}</li>`); continue;
      }
      if (/^&gt;\s?/.test(line)) {
        flushParagraph(); closeList();
        if (!inQuote) { output.push("<blockquote>"); inQuote = true; }
        output.push(line.replace(/^&gt;\s?/, "") + "<br>"); continue;
      }
      if (!line.trim()) {\n        flushParagraph();\n        const nextLine = lines.slice(lineIndex + 1).find((item) => item.trim());\n        if (listType === "ol" && nextLine && /^\\s*\\d+[.)]\\s+/.test(nextLine)) continue;\n        if (listType === "ul" && nextLine && /^\\s*[-*+]\\s+/.test(nextLine)) continue;\n        closeList(); closeQuote(); continue;\n      }
      closeList(); closeQuote(); paragraph.push(line);
    }
    flushParagraph(); closeList(); closeQuote();
    return output.join("\n");
  }
  function showToast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("show");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2800);
  }
  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
    return payload;
  }
  function persist() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        sessionId: state.sessionId, sessions: state.sessions.slice(0, 40),
        artifactTitle: state.artifactTitle, artifactContent: state.artifactContent, artifactTab: state.artifactTab
      }));
    } catch { /* Storage can be disabled; the current session still works. */ }
  }
  function loadPersisted() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
      state.sessions = Array.isArray(saved.sessions) ? saved.sessions : [];
      state.sessionId = saved.sessionId || null;
      state.artifactTitle = saved.artifactTitle || state.artifactTitle;
      state.artifactContent = saved.artifactContent || "";
      state.artifactTab = saved.artifactTab || "markdown";
    } catch { /* Ignore stale/corrupt browser state. */ }
  }
  function shortTitle(text) {
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    return clean.length > 43 ? clean.slice(0, 40) + "…" : (clean || "New conversation");
  }
  function renderSessions() {
    if (!state.sessions.length) {
      els.conversationList.innerHTML = '<div class="empty-history">Your conversations will appear here.</div>';
      return;
    }
    els.conversationList.innerHTML = state.sessions.map((session) => `
      <button class="history-item ${session.id === state.sessionId ? "active" : ""}" data-session-id="${escapeHtml(session.id)}">
        <span class="history-symbol">◷</span><span class="history-title">${escapeHtml(session.title || "New conversation")}</span><span class="history-dot"></span>
      </button>`).join("");
  }
  function upsertSession(session) {
    const index = state.sessions.findIndex((item) => item.id === session.id);
    if (index >= 0) state.sessions[index] = { ...state.sessions[index], ...session };
    else state.sessions.unshift(session);
    state.sessions.sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    state.sessions = state.sessions.slice(0, 40);
    renderSessions(); persist();
  }
  async function createSession() {
    const session = await api("/api/v1/sessions", { method: "POST", body: JSON.stringify({ title: "New conversation", metadata: { interface: "research-workspace" } }) });
    state.sessionId = session.id;
    state.messages = []; state.sources = []; state.grounded = false; state.lastAnswer = "";
    upsertSession(session); renderMessages(); renderSources([], false); setView("chat");
    return session;
  }
  async function refreshSessionList() {
    // Session listing isn't exposed by the current API; retain sessions known to this browser.
    renderSessions();
  }
  async function selectSession(id) {
    if (!id || state.busy) return;
    try {
      const session = await api("/api/v1/sessions/" + encodeURIComponent(id));
      state.sessionId = session.id;
      state.messages = (session.messages || []).map((item) => ({
        role: item.role, content: item.content, metadata: item.message_metadata || {}, created_at: item.created_at
      }));
      const latestAssistant = [...state.messages].reverse().find((item) => item.role === "assistant");
      state.sources = latestAssistant?.metadata?.sources || [];
      state.grounded = Boolean(latestAssistant?.metadata?.grounded);
      state.lastAnswer = latestAssistant?.content || "";
      upsertSession(session); renderMessages(); renderSources(state.sources, state.grounded); setView("chat");
      els.sidebar.classList.remove("open");
    } catch (error) { showToast(error.message || "Could not open this conversation."); }
  }
  function renderMessages() {
    const hasMessages = state.messages.length > 0;
    els.welcomeView.hidden = hasMessages;
    els.messagesList.innerHTML = state.messages.map((message, index) => renderMessage(message, index)).join("");
    els.messagesList.scrollTop = els.messagesList.scrollHeight;
    if (!hasMessages) els.messagesList.innerHTML = "";
  }
  function renderMessage(message, index) {
    const isUser = message.role === "user";
    const time = message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
    const content = isUser ? escapeHtml(message.content).replace(/\n/g, "<br>") : markdownToHtml(message.content, true);
    const tools = !isUser ? `<div class="message-tools"><button class="mini-action" data-action="copy-answer" data-index="${index}">⧉ Copy</button><button class="mini-action" data-action="make-artifact" data-index="${index}">▤ Create artifact</button></div>` : "";
    return `<article class="message ${isUser ? "user" : "assistant"}" data-message-index="${index}">
      <div class="message-avatar">${isUser ? "Y" : "L."}</div><div class="message-body">
      <div class="message-meta"><strong>${isUser ? "You" : "Lenny Growth Assistant"}</strong>${time ? `<time>${escapeHtml(time)}</time>` : ""}${!isUser && message.metadata?.model ? `<time>· ${escapeHtml(message.metadata.model)}</time>` : ""}</div>
      <div class="message-bubble">${content}</div>${tools}</div></article>`;
  }
  function renderSources(sources, grounded) {
    state.sources = sources || []; state.grounded = Boolean(grounded);
    els.sourceCount.textContent = String(state.sources.length);
    if (state.grounded) {
      els.groundingStatus.innerHTML = '<span class="status-symbol">✓</span><div><strong>Evidence attached</strong><span>Answer includes retrieved transcript passages.</span></div>';
    } else if (state.sources.length === 0 && state.messages.length) {
      els.groundingStatus.innerHTML = '<span class="status-symbol">!</span><div><strong>Limited evidence</strong><span>The assistant did not have supporting passages.</span></div>';
    } else {
      els.groundingStatus.innerHTML = '<span class="status-symbol">⌁</span><div><strong>Ready to research</strong><span>Sources appear with your answer.</span></div>';
    }
    if (!state.sources.length) {
      els.evidenceContent.innerHTML = '<div class="evidence-empty"><div class="empty-icon">⌕</div><strong>Your sources, in context.</strong><p>Ask a question to see the transcript passages used to support the answer.</p></div>';
      return;
    }
    els.evidenceContent.innerHTML = state.sources.map((source, index) => {
      const url = safeUrl(source.url);
      return `<article class="source-card" id="source-${index + 1}"><div class="source-card-head"><span class="source-index">${index + 1}</span><div><div class="source-title">${escapeHtml(source.title || "Untitled episode")}</div><div class="source-guest">${escapeHtml(source.guest || "Lenny podcast")} ${source.publish_date ? "· " + escapeHtml(source.publish_date) : ""}</div></div></div><div class="source-excerpt">${escapeHtml(source.content || "")}</div><div class="source-card-footer"><span class="source-type">${escapeHtml((source.source_type || "SOURCE").toUpperCase())}</span>${url ? `<a class="source-open" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>` : '<span class="source-type">TRANSCRIPT</span>'}</div></article>`;
    }).join("");
  }
  function showTyping() {
    const article = document.createElement("article");
    article.className = "message assistant"; article.id = "typingMessage";
    article.innerHTML = '<div class="message-avatar">L.</div><div class="message-body"><div class="message-meta"><strong>Lenny Growth Assistant</strong></div><div class="typing-indicator"><span></span><span></span><span></span></div></div>';
    els.messagesList.appendChild(article); els.messagesList.scrollTop = els.messagesList.scrollHeight;
  }
  function removeTyping() { $("#typingMessage")?.remove(); }
  function setBusy(value) {
    state.busy = value; els.sendButton.disabled = value; els.newChat.disabled = value;
    els.sendButton.querySelector("span:first-child").textContent = value ? "Thinking" : "Send";
  }
  async function sendMessage(raw) {
    const message = String(raw ?? els.messageInput.value).trim();
    if (!message || state.busy) return;
    if (message.length > 30000) { showToast("Please keep your question under 30,000 characters."); return; }
    if (!state.sessionId) {
      try { await createSession(); } catch (error) { showToast("Could not create a session: " + error.message); return; }
    }
    state.messages.push({ role: "user", content: message, created_at: new Date().toISOString() });
    renderMessages(); els.messageInput.value = ""; resizeInput(); setBusy(true); showTyping();
    try {
      const result = await api("/api/v1/chat", { method: "POST", body: JSON.stringify({ session_id: state.sessionId, message }) });
      removeTyping();
      state.messages.push({ role: "assistant", content: result.answer, metadata: { provider: result.provider, model: result.model, sources: result.sources || [], grounded: result.grounded }, created_at: new Date().toISOString() });
      state.lastAnswer = result.answer || "";
      renderMessages(); renderSources(result.sources || [], result.grounded);
      const session = state.sessions.find((item) => item.id === state.sessionId) || { id: state.sessionId, created_at: new Date().toISOString() };
      upsertSession({ ...session, title: session.title === "New conversation" || !session.title ? shortTitle(message) : session.title, updated_at: new Date().toISOString() });
    } catch (error) {
      removeTyping();
      state.messages.push({ role: "assistant", content: `I couldn't complete that request. **${error.message}**\n\nCheck that FastAPI, PostgreSQL, and Ollama are running, then try again.`, metadata: { error: true }, created_at: new Date().toISOString() });
      renderMessages(); showToast(error.message || "Request failed.");
    } finally { setBusy(false); els.messageInput.focus(); }
  }
  function resizeInput() {
    els.messageInput.style.height = "auto";
    els.messageInput.style.height = Math.min(els.messageInput.scrollHeight, 160) + "px";
  }
  function setView(view) {
    state.view = view;
    els.chatColumn.hidden = view !== "chat";
    els.workspaceGrid.hidden = view !== "chat";
    els.artifactView.hidden = view !== "artifacts";
    els.pageBreadcrumb.textContent = view === "chat" ? "Research chat" : "Artifacts";
    document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
    if (view === "artifacts") { renderArtifact(); }
    persist();
  }
  function setArtifactContent(content, title) {
    state.artifactContent = content || "";
    if (title) state.artifactTitle = title;
    els.artifactText.value = state.artifactContent;
    els.artifactName.textContent = state.artifactTitle;
    renderArtifact(); persist();
  }
  function makeArtifactFromMessage(index) {
    const message = state.messages[index];
    if (!message || message.role !== "assistant") return;
    const content = message.content || "";
    const title = "Growth brief — " + new Date().toLocaleDateString();
    setArtifactContent("# " + title + "\n\n" + content, title);
    setView("artifacts");
    showToast("Answer added to your artifact draft.");
  }
  function renderArtifact() {
    const content = els.artifactText.value;
    state.artifactContent = content;
    els.artifactWordCount.textContent = `${content.trim() ? content.trim().split(/\s+/).length : 0} words`;
    els.artifactName.textContent = state.artifactTitle;
    document.querySelectorAll("[data-artifact-tab]").forEach((button) => button.classList.toggle("active", button.dataset.artifactTab === state.artifactTab));
    els.previewLabel.textContent = state.artifactTab === "html" ? "SANDBOXED HTML PREVIEW" : "MARKDOWN PREVIEW";
    if (!content.trim()) {
      els.previewCanvas.innerHTML = '<div class="preview-placeholder"><div class="empty-icon">✧</div><strong>Your next great idea starts here.</strong><p>Create an artifact from a useful answer to see the preview.</p></div>';
      return;
    }
    if (state.artifactTab === "html") {
      const frame = document.createElement("iframe");
      frame.setAttribute("sandbox", ""); frame.setAttribute("title", "Isolated HTML artifact preview");
      frame.referrerPolicy = "no-referrer";
      // srcdoc is isolated by sandbox (no scripts, same-origin access, forms, or top navigation).
      const documentText = /<html[\s>]/i.test(content) ? content : `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px system-ui;line-height:1.7;max-width:760px;margin:36px auto;padding:0 22px;color:#25261f}h1,h2{line-height:1.25}a{color:#526b2e}img{max-width:100%}</style></head><body>${content}</body></html>`;
      frame.srcdoc = documentText;
      els.previewCanvas.replaceChildren(frame);
    } else {
      els.previewCanvas.innerHTML = `<div class="preview-markdown">${markdownToHtml(content, false)}</div>`;
    }
  }
  async function copyText(value) {
    try { await navigator.clipboard.writeText(value); showToast("Copied to clipboard."); }
    catch { showToast("Clipboard access is unavailable in this browser."); }
  }
  function downloadArtifact() {
    const ext = state.artifactTab === "html" ? "html" : "md";
    const blob = new Blob([els.artifactText.value], { type: ext === "html" ? "text/html;charset=utf-8" : "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = (state.artifactTitle || "growth-brief").replace(/[^a-z0-9-]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() + "." + ext;
    document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  }
  function applyTheme(theme, save = true) {
    const selected = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = selected;
    if (els.themeToggle) {
      const dark = selected === "dark";
      els.themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      els.themeToggle.title = dark ? "Switch to light theme" : "Switch to dark theme";
      els.themeToggle.querySelector(".theme-glyph").textContent = dark ? "☼" : "◐";
      els.themeToggle.querySelector(".theme-label").textContent = dark ? "Light mode" : "Dark mode";
    }
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) metaTheme.content = selected === "dark" ? "#10131b" : "#f6f4ee";
    if (save) {
      try { localStorage.setItem(THEME_KEY, selected); } catch { /* Theme still applies for this page. */ }
    }
  }
  function toggleTheme() {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  }
  function showSettings() {
    showToast("Model: Qwen 2.5 7B · Provider: local Ollama · Sources: PostgreSQL + pgvector");
  }
  function scrollToSource(index) {
    const source = $("#source-" + index);
    if (!source) { showToast("That citation has no matching source in the latest response."); return; }
    els.workspaceGrid.classList.add("show-evidence");
    els.workspaceGrid.classList.remove("evidence-hidden");
    source.scrollIntoView({ behavior: "smooth", block: "center" });
    source.style.borderColor = "#a8c76a";
    setTimeout(() => source.style.removeProperty("border-color"), 1400);
  }

  els.newChat.addEventListener("click", async () => {
    try { await createSession(); els.messageInput.focus(); }
    catch (error) { showToast("Could not create a session: " + error.message); }
  });
  els.sendButton.addEventListener("click", () => sendMessage());
  els.messageInput.addEventListener("input", resizeInput);
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendMessage(); }
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => sendMessage(button.dataset.prompt)));
  els.conversationList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-session-id]");
    if (button) selectSession(button.dataset.sessionId);
  });
  els.refreshSessions.addEventListener("click", refreshSessionList);
  els.messagesList.addEventListener("click", (event) => {
    const citation = event.target.closest("[data-source-index]");
    if (citation) { scrollToSource(Number(citation.dataset.sourceIndex)); return; }
    const action = event.target.closest("[data-action]");
    if (!action) return;
    const index = Number(action.dataset.index);
    if (action.dataset.action === "copy-answer") copyText(state.messages[index]?.content || "");
    if (action.dataset.action === "make-artifact") makeArtifactFromMessage(index);
  });
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
    setView(button.dataset.view); els.sidebar.classList.remove("open");
  }));
  els.toggleSources.addEventListener("click", () => {
    if (window.innerWidth <= 760) els.workspaceGrid.classList.toggle("show-evidence");
    else els.workspaceGrid.classList.toggle("evidence-hidden");
  });
  els.closeEvidence.addEventListener("click", () => {
    if (window.innerWidth <= 760) els.workspaceGrid.classList.remove("show-evidence");
    else els.workspaceGrid.classList.add("evidence-hidden");
  });
  els.openSidebar.addEventListener("click", () => els.sidebar.classList.add("open"));
  els.closeSidebar.addEventListener("click", () => els.sidebar.classList.remove("open"));
  els.settingsButton.addEventListener("click", showSettings);
  els.themeToggle.addEventListener("click", toggleTheme);
  els.createArtifact.addEventListener("click", () => {
    const latest = [...state.messages].reverse().find((message) => message.role === "assistant");
    if (!latest) { showToast("Ask a question first, then turn the answer into a draft."); return; }
    makeArtifactFromMessage(state.messages.lastIndexOf(latest));
  });
  els.artifactText.addEventListener("input", () => { renderArtifact(); persist(); });
  document.querySelectorAll("[data-artifact-tab]").forEach((button) => button.addEventListener("click", () => {
    state.artifactTab = button.dataset.artifactTab; renderArtifact(); persist();
  }));
  els.downloadArtifact.addEventListener("click", downloadArtifact);
  els.copyArtifact.addEventListener("click", () => copyText(els.artifactText.value));
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); els.newChat.click(); }
    if (event.key === "Escape") els.sidebar.classList.remove("open");
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 760) els.workspaceGrid.classList.remove("show-evidence");
  });

  async function init() {
    loadPersisted();
    let savedTheme = "light";
    try { savedTheme = localStorage.getItem(THEME_KEY) || "light"; } catch { /* Use light theme by default. */ }
    applyTheme(savedTheme, false);
    els.artifactText.value = state.artifactContent;
    renderArtifact(); renderSessions(); renderSources([], false);
    if (state.sessionId) {
      try { await selectSession(state.sessionId); }
      catch { state.sessionId = null; }
    }
    if (!state.sessionId) { state.messages = []; renderMessages(); }
    if (state.view === "artifacts") setView("artifacts");
    else setView("chat");
  }
  init();
})();
