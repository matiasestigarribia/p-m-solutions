// Progressive enhancement only — the site works without JS.
(function () {
  "use strict";
  var toggle = document.querySelector("[data-nav-toggle]");
  var links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();

(function () {
  "use strict";

  function initChatbot() {
    var launcher = document.getElementById("pm-chat-launcher");
    var modal = document.getElementById("pm-chat");
    var close = document.getElementById("pm-chat-close");
    var form = document.getElementById("pm-chat-form");
    var input = document.getElementById("pm-chat-input");
    var send = document.getElementById("pm-chat-send");
    var messages = document.getElementById("pm-chat-messages");
    var language = document.getElementById("pm-chat-language");
    if (!launcher || !modal || !close || !form || !input || !send || !messages) return;

    var history = [];
    var busy = false;

    function setOpen(open) {
      modal.hidden = !open;
      launcher.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) input.focus();
    }

    function addMessage(text, role) {
      var item = document.createElement("div");
      item.className = "chat-message chat-message--" + role;
      item.textContent = text;
      messages.appendChild(item);
      messages.scrollTop = messages.scrollHeight;
      return item;
    }

    async function sendMessage(event) {
      event.preventDefault();
      var question = input.value.trim();
      if (!question || busy) return;
      busy = true;
      send.disabled = true;
      input.disabled = true;
      addMessage(question, "user");
      input.value = "";
      var replyBubble = addMessage("", "bot");
      try {
        var response = await fetch("/api/v1/chat/stream/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
          body: JSON.stringify({ message: question, language: language.value || "pt", chat_history: history.slice(-8) })
        });
        if (!response.ok || !response.body) throw new Error("chat request failed");
        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";
        var reply = "";
        while (true) {
          var result = await reader.read();
          buffer += decoder.decode(result.value || new Uint8Array(), { stream: !result.done });
          var frames = buffer.split("\n\n");
          buffer = frames.pop();
          frames.forEach(function (frame) {
            var line = frame.split("\n").find(function (part) { return part.indexOf("data:") === 0; });
            if (!line) return;
            var data = line.slice(5).trim();
            if (data === "[DONE]") return;
            if (data.indexOf("[ERROR]") === 0) throw new Error(data.slice(7).trim());
            reply += data.replace(/\\n/g, "\n");
            replyBubble.textContent = reply;
            messages.scrollTop = messages.scrollHeight;
          });
          if (result.done) break;
        }
        if (!reply) replyBubble.textContent = "No response was returned. Please use the contact form.";
        history.push({ role: "user", content: question }, { role: "assistant", content: reply });
      } catch (error) {
        replyBubble.remove();
        addMessage("The chatbot is temporarily unavailable. Please use the contact form.", "error");
      } finally {
        busy = false;
        send.disabled = false;
        input.disabled = false;
        input.focus();
      }
    }

    launcher.addEventListener("click", function () { setOpen(true); });
    close.addEventListener("click", function () { setOpen(false); });
    modal.addEventListener("click", function (event) { if (event.target === modal) setOpen(false); });
    form.addEventListener("submit", sendMessage);
    document.addEventListener("keydown", function (event) { if (event.key === "Escape" && !modal.hidden) setOpen(false); });
  }

  document.addEventListener("DOMContentLoaded", initChatbot);
})();