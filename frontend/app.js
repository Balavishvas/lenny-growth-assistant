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
    settingsButton: $("#settingsButton"), themeToggle: $("#themeToggle"), modelStatus: $("#modelStatus"), ship30EssayButton: $("#ship30EssayButton")
  };
  const state = {
    sessionId: null, sessions: [], messages: [], sources: [], grounded: false, lastAnswer: "", provider: "ollama", claudeModel: "claude-sonnet-4-20250514",
    view: "chat", artifactTab: "markdown", artifactTitle: "Untitled growth brief",
    artifactContent: "", busy: false, toastTimer: null, artifactPreviewTimer: null, abortController: null
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
    for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      const line = lines[lineIndex];
      const codeMatch = line.match(/^@@CODE(\d+)@@$/);
      if (codeMatch) { flushParagraph(); closeList(); closeQuote(); output.push(codeBlocks[Number(codeMatch[1])] || ""); continue; }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (heading) { flushParagraph(); closeList(); closeQuote(); const level = Math.min(heading[1].length, 6); output.push(`<h${level}>${heading[2]}</h${level}>`); continue; }
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
      if (!line.trim()) {
        flushParagraph();
        const nextLine = lines.slice(lineIndex + 1).find((item) => item.trim());
        if (listType === "ol" && nextLine && /^\s*\d+[.)]\s+/.test(nextLine)) continue;
        if (listType === "ul" && nextLine && /^\s*[-*+]\s+/.test(nextLine)) continue;
        closeList(); closeQuote(); continue;
      }
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
    try {
      const sessions = await api("/api/v1/sessions");
      state.sessions = Array.isArray(sessions) ? sessions : [];
      renderSessions();
      persist();
      showToast(`Loaded ${state.sessions.length} recent conversation${state.sessions.length === 1 ? "" : "s"}.`);
    } catch (error) {
      showToast("Could not refresh conversations: " + error.message);
    }
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
    const requestStarted = performance.now();
    let firstTokenMs = null;
    let assistantIndex = -1;
    let completion = null;
    try {
      const response = await fetch(API + "/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ session_id: state.sessionId, message, provider: state.provider, model: state.provider === "anthropic" ? state.claudeModel : null, api_key: state.provider === "anthropic" ? getClaudeKey() : null })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Request failed (${response.status})`);
      }
      if (!response.body) throw new Error("This browser does not support streamed responses.");
      removeTyping();
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamError = null;
      const handleEvent = (rawEvent) => {
        const data = rawEvent.replace(/\r/g, "").split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
        if (!data) return;
        let event;
        try { event = JSON.parse(data); } catch { return; }
        if (event.type === "token") {
          if (firstTokenMs === null) firstTokenMs = Math.round(performance.now() - requestStarted);
          if (assistantIndex < 0) {
            state.messages.push({ role: "assistant", content: "", metadata: { streaming: true }, created_at: new Date().toISOString() });
            assistantIndex = state.messages.length - 1;
          }
          state.messages[assistantIndex].content += event.text || "";
          renderMessages();
        } else if (event.type === "done") {
          completion = event;
        } else if (event.type === "error") {
          streamError = new Error(event.message || "Streaming generation failed.");
        }
      };
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() || "";
        for (const rawEvent of events) handleEvent(rawEvent);
        if (done) break;
      }
      if (buffer.trim()) handleEvent(buffer);
      if (streamError) throw streamError;
      if (assistantIndex < 0) throw new Error("The stream ended without answer text.");
      const finalMessage = state.messages[assistantIndex];
      finalMessage.metadata = {
        provider: completion?.provider || "ollama",
        model: completion?.model || "qwen2.5:7b",
        sources: completion?.sources || [],
        grounded: Boolean(completion?.grounded),
        quality_issues: completion?.quality_issues || [],
        latency: completion ? { first_token_ms: firstTokenMs, retrieval_ms: completion.retrieval_ms, generation_ms: completion.generation_ms, total_ms: completion.total_ms } : { first_token_ms: firstTokenMs }
      };
      state.lastAnswer = finalMessage.content;
      renderMessages(); renderSources(completion?.sources || [], Boolean(completion?.grounded));
      // Quality flags remain attached to the message for review/export, but do not interrupt the workspace with a prominent warning.
      const session = state.sessions.find((item) => item.id === state.sessionId) || { id: state.sessionId, created_at: new Date().toISOString() };
      upsertSession({ ...session, title: session.title === "New conversation" || !session.title ? shortTitle(message) : session.title, updated_at: new Date().toISOString() });
      if (completion) {
        console.info("[Lenny latency]", { first_token_ms: firstTokenMs, retrieval_ms: completion.retrieval_ms, generation_ms: completion.generation_ms, total_ms: completion.total_ms });
        showToast(`First text ${firstTokenMs} ms · Retrieval ${completion.retrieval_ms} ms · Generation ${completion.generation_ms} ms`);
      }
    } catch (error) {
      removeTyping();
      if (assistantIndex >= 0) state.messages.splice(assistantIndex, 1);
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
    const answer = String(message.content || "").trim();
    const heading = answer.match(/^#{1,2}\s+(.+)$/m);
    const title = (heading?.[1] || "Growth brief").replace(/[*_`]/g, "").trim().slice(0, 100) || "Growth brief";
    const sourceItems = Array.isArray(message.metadata?.sources) ? message.metadata.sources : [];
    const sourceLines = sourceItems.map((source, sourceIndex) => {
      const label = String(source.title || source.episode_title || source.guest || `Source ${sourceIndex + 1}`).replace(/[\[\]\n\r]/g, " ").trim();
      const guest = source.guest ? ` — ${String(source.guest).replace(/[\n\r]/g, " ")}` : "";
      let url = "";
      try {
        const parsed = new URL(String(source.url || source.source_url || ""));
        if (["http:", "https:"].includes(parsed.protocol)) url = parsed.href;
      } catch { /* Keep the source label without an unsafe or invalid link. */ }
      return `- [${sourceIndex + 1}] ${url ? `[${label}](${url})` : label}${guest}`;
    });
    const content = sourceLines.length
      ? `${answer}\n\n## Sources\n\n${sourceLines.join("\n")}\n`
      : answer;
    setArtifactContent(content, title);
    setView("artifacts");
    showToast(sourceLines.length
      ? `Answer added with ${sourceLines.length} source references.`
      : "Answer added to your artifact draft.");
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
    const text = String(value ?? "");
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const helper = document.createElement("textarea");
        helper.value = text; helper.setAttribute("readonly", "");
        helper.style.position = "fixed"; helper.style.opacity = "0"; helper.style.pointerEvents = "none";
        document.body.appendChild(helper); helper.select();
        const copied = document.execCommand("copy"); helper.remove();
        if (!copied) throw new Error("Copy command was rejected");
      }
      showToast("Artifact content copied.");
    } catch {
      showToast("Copy failed. Select the editor text and copy it manually.");
    }
  }
  function downloadArtifact() {
    const content = els.artifactText.value;
    if (!content.trim()) { showToast("Add some content before exporting."); return; }
    const ext = state.artifactTab === "html" ? "html" : "md";
    const mime = ext === "html" ? "text/html;charset=utf-8" : "text/markdown;charset=utf-8";
    let exportContent = content;
    if (ext === "html" && !/<html[\s>]/i.test(content)) {
      exportContent = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(state.artifactTitle || "Growth brief")}</title>
<style>body{font:16px/1.7 system-ui,sans-serif;max-width:760px;margin:36px auto;padding:0 22px;color:#25261f}h1,h2,h3{line-height:1.25}a{color:#294ee8}img{max-width:100%}pre{overflow:auto;padding:12px;background:#f2f2ee}</style>
</head><body>${content}</body></html>`;
    }
    const blob = new Blob(["\ufeff", exportContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const baseName = (state.artifactTitle || "growth-brief")
      .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "growth-brief";
    anchor.href = url; anchor.download = `${baseName}.${ext}`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    // Delay revocation so browsers have time to start reading the generated Blob.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast(`Exported ${ext.toUpperCase()} artifact.`);
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
  function getClaudeKey() {
    try { return sessionStorage.getItem("lenny-growth-assistant.anthropic-key") || ""; }
    catch { return ""; }
  }
  function setProvider(provider) {
    state.provider = provider === "anthropic" ? "anthropic" : "ollama";
    const mode = $("#modelMode");
    if (mode) mode.value = state.provider;
    if (state.provider === "anthropic" && !getClaudeKey()) {
      const key = window.prompt("Enter your Anthropic API key. It stays in this browser tab and is sent only with Claude requests.");
      if (key && key.trim()) {
        try { sessionStorage.setItem("lenny-growth-assistant.anthropic-key", key.trim()); }
        catch { showToast("This browser cannot store the key for this tab."); }
      } else {
        state.provider = "ollama";
        if (mode) mode.value = "ollama";
        showToast("Kept local Ollama selected; Claude needs an API key.");
      }
    }
    try { sessionStorage.setItem("lenny-growth-assistant.provider", state.provider); } catch { /* Provider remains selected for this page. */ }
    if (els.modelStatus) els.modelStatus.innerHTML = state.provider === "anthropic"
      ? '<i class="status-dot"></i> Claude · API'
      : '<i class="status-dot"></i> Local Ollama';
    persist();
  }
  async function loadModelStatus() {
    if (!els.modelStatus) return;
    try {
      const config = await api("/api/v1/config");
      const backendProvider = String(config.provider || "ollama");
      const model = String(config.model || "unknown");
      if (state.provider === "anthropic") {
        els.modelStatus.innerHTML = '<i class="status-dot"></i> Claude · API';
        els.modelStatus.title = "Claude requests use your tab-scoped Anthropic API key.";
      } else {
        const prettyModel = model.replace(/^qwen2\.5:(\d+)b$/i, "Qwen 2.5 $1B");
        els.modelStatus.innerHTML = `<i class="status-dot"></i> ${escapeHtml(backendProvider)} · ${escapeHtml(prettyModel)}`;
        els.modelStatus.title = `Active backend model: ${model}`;
      }
    } catch (error) {
      els.modelStatus.textContent = "Model status unavailable";
      els.modelStatus.title = error.message;
    }
  }
  function showSettings() {
    api("/api/v1/config").then((config) => {
      showToast(`Model: ${config.model} · Provider: ${config.provider} · Sources: PostgreSQL + pgvector`);
    }).catch(() => showToast("Could not read model settings from the backend."));
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
  els.ship30EssayButton?.addEventListener("click", () => {
    if (state.busy) { showToast("Wait for the current response to finish first."); return; }
    // Open an in-app topic composer rather than a browser prompt, so users can type freely.
    const existing = $("#ship30Composer");
    if (existing) { existing.querySelector("textarea")?.focus(); return; }
    const panel = document.createElement("div");
    panel.id = "ship30Composer";
    panel.className = "ship30-composer-backdrop";
    panel.innerHTML = `
      <form class="ship30-composer" role="dialog" aria-modal="true" aria-labelledby="ship30ComposerTitle">
        <div class="ship30-composer-kicker">SHIP 30 FOR 30 · WRITING WORKFLOW</div>
        <h2 id="ship30ComposerTitle">What do you want to write about?</h2>
        <p>Describe your topic, audience, and point of view. The assistant will build a source-grounded essay around your idea.</p>
        <label for="ship30Topic">Essay topic or thesis</label>
        <textarea id="ship30Topic" rows="4" placeholder="e.g. Why product-market fit should come before optimizing activation…" required></textarea>
        <div class="ship30-composer-hint">Target: 1,400 words · Title, sections, takeaways, conclusion, and citations</div>
        <div class="ship30-composer-actions"><button type="button" class="secondary-button" data-ship30-cancel>Cancel</button><button type="submit" class="primary-button">Generate essay ↗</button></div>
      </form>`;
    document.body.appendChild(panel);
    const topicInput = panel.querySelector("#ship30Topic");
    topicInput.focus();
    panel.addEventListener("click", (event) => { if (event.target === panel) panel.remove(); });
    panel.querySelector("[data-ship30-cancel]").addEventListener("click", () => panel.remove());
    panel.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      const topic = topicInput.value.trim();
      if (!topic) { topicInput.focus(); return; }
      panel.remove();
      const request = "Use the Ship 30 for 30 writing skill to write a complete 1,400-word essay about: " + topic +
        ". Aim for 1,300–1,400 words, with a clear thesis, meaningful section headings, practical takeaways, a conclusion, and inline [number] citations tied only to retrieved Lenny transcript sources. Do not invent facts or citations. Return the essay itself, not a search summary.";
      sendMessage(request);
    });
  });
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
  $("#modelMode")?.addEventListener("change", (event) => setProvider(event.target.value));
  els.themeToggle.addEventListener("click", toggleTheme);
  els.createArtifact.addEventListener("click", () => {
    const latest = [...state.messages].reverse().find((message) => message.role === "assistant");
    if (!latest) { showToast("Ask a question first, then turn the answer into a draft."); return; }
    makeArtifactFromMessage(state.messages.lastIndexOf(latest));
  });
  els.artifactText.addEventListener("input", () => {
    state.artifactContent = els.artifactText.value;
    const trimmed = state.artifactContent.trim();
    els.artifactWordCount.textContent = `${trimmed ? trimmed.split(/\\s+/).length : 0} words`;
    persist();
    // Keep typing responsive: update the expensive preview after the user pauses.
    clearTimeout(state.artifactPreviewTimer);
    state.artifactPreviewTimer = setTimeout(() => renderArtifact(), 140);
  });
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
    try { if (sessionStorage.getItem("lenny-growth-assistant.provider") === "anthropic" && getClaudeKey()) state.provider = "anthropic"; } catch { /* Default to local mode. */ }
    if ($("#modelMode")) $("#modelMode").value = state.provider;
    loadModelStatus();
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
