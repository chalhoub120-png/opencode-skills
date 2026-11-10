(function () {
  "use strict";

  const TOKEN_KEY = "cb-token";
  const views = {
    auth: document.getElementById("auth-view"),
    register: document.getElementById("register-view"),
    chat: document.getElementById("chat-view"),
  };
  const token = localStorage.getItem(TOKEN_KEY);

  function show(viewName) {
    Object.values(views).forEach((v) => v.classList.add("hidden"));
    views[viewName].classList.remove("hidden");
  }

  /* ----- Auth UI ----- */
  document.getElementById("show-register").onclick = () => show("register");
  document.getElementById("show-login").onclick = () => show("auth");
  document.getElementById("logout-btn").onclick = () => {
    localStorage.removeItem(TOKEN_KEY);
    location.reload();
  };

  async function handleAuth(e, endpoint) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd);
    try {
      const res = await fetch(`/api/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Auth failed");
      localStorage.setItem(TOKEN_KEY, data.token);
      show("chat");
      initChat();
    } catch (err) {
      alert(err.message);
    }
  }

  document.getElementById("login-form").onsubmit = (e) =>
    handleAuth(e, "login");
  document.getElementById("register-form").onsubmit = (e) =>
    handleAuth(e, "register");

  if (token) {
    show("chat");
    initChat();
  } else {
    show("auth");
  }

  /* ----- Chat State ----- */
  let currentConvId = null;
  let isSending = false;
  let selectedFile = null;

  const input = document.getElementById("user-input");
  const form = document.getElementById("input-form");
  const sendBtn = document.getElementById("send-btn");
  const messages = document.getElementById("messages");
  const typing = document.getElementById("typing");
  const chatList = document.getElementById("chat-list");
  const fileInput = document.getElementById("file-input");
  const uploadZone = document.getElementById("upload-zone");
  const uploadName = document.getElementById("upload-name");
  const removeFileBtn = document.getElementById("remove-file");
  const attachBtn = document.getElementById("attach-btn");

  /* ----- i18n ----- */
  document
    .getElementById("lang-switcher")
    .querySelectorAll(".lang-btn")
    .forEach((btn) => {
      btn.onclick = () => {
        i18n.set(btn.dataset.lang);
        input.placeholder = i18n.t("placeholder");
        sendBtn.textContent = i18n.t("send");
        uploadName.textContent = i18n.t("noFile");
        removeFileBtn.textContent = i18n.t("remove");
      };
    });

  /* ----- Helpers ----- */
  function scrollBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addMessage(role, content, animate = true) {
    const msg = document.createElement("div");
    msg.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;
    msg.appendChild(bubble);
    messages.appendChild(msg);
    scrollBottom();
    if (animate && role === "ai") typeWriter(bubble, content);
    return msg;
  }

  function typeWriter(el, text, speed = 15) {
    el.textContent = "";
    let i = 0;
    const id = setInterval(() => {
      el.textContent += text.charAt(i++);
      if (i >= text.length) {
        clearInterval(id);
        scrollBottom();
      }
    }, speed);
  }

  function setTyping(show) {
    typing.hidden = !show;
    if (show) scrollBottom();
  }

  async function loadConversations() {
    const res = await fetch("/api/conversations", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const convs = await res.json();
    chatList.innerHTML = "";
    convs.forEach((c) => {
      const div = document.createElement("div");
      div.className = "chat-item";
      div.textContent = c.title;
      div.onclick = () => openConversation(c.id, c.title);
      chatList.appendChild(div);
    });
  }

  async function openConversation(id, title) {
    currentConvId = id;
    document.getElementById("chat-title").textContent = title;
    messages.innerHTML = "";
    const res = await fetch(`/api/conversations/${id}/messages`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const msgs = await res.json();
    msgs.forEach((m) => addMessage(m.role, m.content, false));
    scrollBottom();
  }

  document.getElementById("new-chat").onclick = async () => {
    const res = await fetch("/api/conversations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ title: i18n.t("newChat") }),
    });
    const c = await res.json();
    openConversation(c.id, c.title);
  };

  /* ----- File Upload ----- */
  attachBtn.onclick = () => fileInput.click();
  fileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/upload", {
      headers: { Authorization: `Bearer ${token}` },
      method: "POST",
      body: fd,
    });
    const data = await res.json();
    if (res.ok) {
      selectedFile = data.file_path;
      uploadName.textContent = data.filename;
      uploadZone.hidden = false;
    } else {
      alert(data.error || "Upload failed");
    }
  };
  removeFileBtn.onclick = () => {
    selectedFile = null;
    uploadZone.hidden = true;
    fileInput.value = "";
  };

  /* ----- Streaming Send ----- */
  async function sendMessage() {
    const text = input.value.trim();
    if (!text && !selectedFile) return;
    if (isSending) return;

    isSending = true;
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.textContent = i18n.t("sending");

    addMessage("user", text);
    input.value = "";
    setTyping(true);

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversationId: currentConvId,
          message: text,
          lang: i18n.current,
          model: "default",
          file_path: selectedFile || null,
        }),
      });

      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let aiMsg = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (const part of parts) {
          const line = part.replace(/^data: /, "").trim();
          if (!line || line === "[DONE]") continue;
          try {
            const parsed = JSON.parse(line);
            if (parsed.error) {
              setTyping(false);
              addMessage("ai", i18n.t("errorServer") + parsed.error);
              return;
            }
            if (parsed.message?.content) {
              if (!aiMsg) aiMsg = addMessage("ai", "", false);
              aiMsg.querySelector(".bubble").textContent +=
                parsed.message.content;
              scrollBottom();
            }
          } catch {}
        }
      }

      setTyping(false);
      selectedFile = null;
      uploadZone.hidden = true;
      fileInput.value = "";
    } catch (err) {
      console.error(err);
      setTyping(false);
      addMessage("ai", i18n.t("errorConn"));
    } finally {
      isSending = false;
      input.disabled = false;
      sendBtn.disabled = false;
      sendBtn.textContent = i18n.t("send");
      input.focus();
    }
  }

  form.onsubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };
  input.onkeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  async function initChat() {
    i18n.apply();
    input.placeholder = i18n.t("placeholder");
    sendBtn.textContent = i18n.t("send");

    // Check if user is admin and show admin link
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.user && data.user.role === "admin") {
        const adminLink = document.getElementById("admin-link");
        if (adminLink) adminLink.style.display = "inline-flex";
      }
    } catch (err) {
      console.error("Failed to check admin role:", err);
    }

    await loadConversations();
    if (!currentConvId) {
      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: i18n.t("newChat") }),
      });
      const c = await res.json();
      openConversation(c.id, c.title);
    }
    addMessage("ai", i18n.t("welcome"));
  }
})();
