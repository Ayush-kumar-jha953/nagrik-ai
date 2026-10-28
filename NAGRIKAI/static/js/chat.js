/**
 * NAGRIK AI - Civic Problem Assistant (UPKAR-LLM Integration)
 * Controls the floating robot icon and civic AI chat drawer
 */

document.addEventListener("DOMContentLoaded", () => {
  const botFloatingBtn = document.getElementById("botFloatingBtn");
  const chatDrawer = document.getElementById("chatDrawer");
  const btnChatClose = document.getElementById("btnChatClose");
  const chatMessages = document.getElementById("chatMessages");
  const chatInput = document.getElementById("chatInput");
  const btnChatSend = document.getElementById("btnChatSend");
  const quickChips = document.querySelectorAll(".chat-chip");

  let isChatOpen = false;

  // Toggle Chat Drawer
  if (botFloatingBtn) {
    botFloatingBtn.addEventListener("click", () => {
      toggleChatDrawer();
    });
  }

  if (btnChatClose) {
    btnChatClose.addEventListener("click", () => {
      closeChatDrawer();
    });
  }

  function toggleChatDrawer() {
    isChatOpen = !isChatOpen;
    if (isChatOpen) {
      chatDrawer.classList.add("open");
      if (chatInput) chatInput.focus();
      scrollChatToBottom();
    } else {
      chatDrawer.classList.remove("open");
    }
  }

  function closeChatDrawer() {
    isChatOpen = false;
    chatDrawer.classList.remove("open");
  }

  // Quick Chips
  quickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-query") || chip.innerText;
      if (chatInput) {
        chatInput.value = text;
        sendMessage();
      }
    });
  });

  // Send Message Event
  if (btnChatSend) {
    btnChatSend.addEventListener("click", () => sendMessage());
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // Append user message bubble
    appendMessage("user", text);
    chatInput.value = "";
    scrollChatToBottom();

    // Show typing placeholder
    const typingId = appendTypingIndicator();
    scrollChatToBottom();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await res.json();
      removeTypingIndicator(typingId);

      if (data.success && data.reply) {
        appendMessage("assistant", data.reply, data.complaint);
      } else {
        appendMessage("assistant", "I encountered a minor issue processing that. Please try rephrasing your civic question.");
      }
    } catch (err) {
      console.error("Chat error:", err);
      removeTypingIndicator(typingId);
      appendMessage("assistant", "Unable to connect to the NAGRIK AI civic assistant right now. Please check your connection.");
    } finally {
      scrollChatToBottom();
    }
  }

  function appendMessage(role, text, complaintData = null) {
    const msgEl = document.createElement("div");
    msgEl.className = `chat-msg ${role}`;
    
    // Format text with basic markdown (bold, bullets, line breaks)
    const formattedHtml = formatMarkdown(text);
    msgEl.innerHTML = formattedHtml;

    if (complaintData && role === "assistant") {
      // Add a nice visual action pill
      const card = document.createElement("div");
      card.style.marginTop = "8px";
      card.style.padding = "8px 12px";
      card.style.background = "#eff6ff";
      card.style.borderRadius = "8px";
      card.style.border = "1px solid #bfdbfe";
      card.style.fontSize = "12px";
      card.innerHTML = `📌 <b>Grievance Saved to SQLite:</b> Ticket <code>#${complaintData.id}</code> registered under <b>${complaintData.category}</b>.`;
      msgEl.appendChild(card);
    }

    chatMessages.appendChild(msgEl);
    return msgEl;
  }

  function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const typingEl = document.createElement("div");
    typingEl.id = id;
    typingEl.className = "chat-msg assistant";
    typingEl.style.fontStyle = "italic";
    typingEl.style.color = "#64748b";
    typingEl.innerHTML = `<span>Thinking & searching civic rules...</span>`;
    chatMessages.appendChild(typingEl);
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollChatToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function formatMarkdown(str) {
    if (!str) return "";
    let s = str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Bold **text**
    s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Code `code`
    s = s.replace(/`([^`]+)`/g, "<code style='background:#f1f5f9; padding:2px 5px; border-radius:4px; font-weight:600;'>$1</code>");

    // Bullet points
    s = s.replace(/^• (.*)$/gm, "<div style='margin-left: 6px; padding: 1px 0;'>• $1</div>");
    s = s.replace(/^- (.*)$/gm, "<div style='margin-left: 6px; padding: 1px 0;'>- $1</div>");

    // Newlines to <br>
    s = s.replace(/\n\n/g, "<div style='height:8px;'></div>");
    s = s.replace(/\n/g, "<br>");

    return s;
  }
});

