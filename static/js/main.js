// Progressive enhancement for the P&M Solutions site.
(function () {
  "use strict";

  var toggle = document.querySelector("[data-nav-toggle]");
  var links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (event) {
      if (event.target.tagName === "A") {
        links.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();

(function () {
  "use strict";

  var history = [];
  var initialized = false;
  var streaming = false;
  var typewriter = null;

  function getModal() { return document.getElementById("pm-chat-modal"); }
  function getLauncher() { return document.getElementById("pm-chat-launcher"); }

  window.openChat = function () {
    var modal = getModal();
    var launcher = getLauncher();
    if (!modal || typeof window.htmx === "undefined") return;
    var hasFragment = !!modal.querySelector("#pm-chat-modal-inner");
    if (!hasFragment) {
      window.htmx.ajax("GET", "/chat?lang=pt", {
        target: "#pm-chat-modal",
        swap: "innerHTML"
      }).then(function () {
        modal.hidden = false;
        if (launcher) {
          launcher.hidden = true;
          launcher.setAttribute("aria-expanded", "true");
        }
        initChatModal();
      }).catch(function (error) {
        console.error("P&M chat fragment error", error);
        modal.innerHTML = "";
        var errorPanel = document.createElement("div");
        errorPanel.className = "chat-window chat-window--load-error";
        errorPanel.setAttribute("role", "dialog");
        errorPanel.setAttribute("aria-modal", "true");
        var errorText = document.createElement("p");
        errorText.textContent = "Não foi possível abrir o assistente agora. Tente novamente em instantes.";
        var retryClose = document.createElement("button");
        retryClose.type = "button";
        retryClose.className = "chat-window__close chat-window__load-close";
        retryClose.setAttribute("aria-label", "Fechar mensagem de erro");
        retryClose.textContent = "×";
        retryClose.addEventListener("click", window.closeChat);
        errorPanel.appendChild(errorText);
        errorPanel.appendChild(retryClose);
        modal.appendChild(errorPanel);
        modal.hidden = false;
        if (launcher) launcher.hidden = false;
      });
    } else {
      modal.hidden = false;
      if (launcher) {
        launcher.hidden = true;
        launcher.setAttribute("aria-expanded", "true");
      }
      initChatModal();
    }
  };

  window.closeChat = function () {
    var modal = getModal();
    var launcher = getLauncher();
    if (modal) modal.hidden = true;
    if (launcher) {
      launcher.hidden = false;
      launcher.setAttribute("aria-expanded", "false");
    }
  };

  function scrollToBottom() {
    var messages = document.getElementById("pm-chat-messages");
    if (messages) messages.scrollTop = messages.scrollHeight;
  }

  function appendMessage(text, role) {
    var messages = document.getElementById("pm-chat-messages");
    var row = document.createElement("div");
    row.className = "chat-message-row chat-message-row--" + role;
    var group = document.createElement("div");
    group.className = "chat-message-group";
    var bubble = document.createElement("div");
    bubble.className = "chat-message chat-message--" + role;
    bubble.textContent = text;
    group.appendChild(bubble);
    var time = document.createElement("p");
    time.className = "chat-message__time";
    time.textContent = "Agora mesmo";
    group.appendChild(time);
    row.appendChild(group);
    messages.appendChild(row);
    scrollToBottom();
    return { row: row, bubble: bubble };
  }

  function showTypingIndicator() {
    var messages = document.getElementById("pm-chat-messages");
    var row = document.createElement("div");
    row.id = "pm-chat-typing";
    row.className = "chat-message-row chat-message-row--bot";
    row.innerHTML = '<div class="chat-message-group"><div class="chat-message chat-message--bot chat-message--typing"><span></span><span></span><span></span></div></div>';
    messages.appendChild(row);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var indicator = document.getElementById("pm-chat-typing");
    if (indicator) indicator.remove();
  }

  function createStreamingBubble() {
    var result = appendMessage("", "bot");
    result.bubble.classList.add("chat-message--streaming");
    return result.bubble;
  }

  function startTypewriter() {
    var queue = [];
    var running = false;
    var done = false;
    var callback = null;

    function drain() {
      if (!queue.length) {
        running = false;
        if (done && callback) { var finished = callback; callback = null; finished(); }
        return;
      }
      var item = queue.shift();
      item.target.textContent += item.char;
      scrollToBottom();
      window.setTimeout(drain, 18);
    }

    return {
      enqueue: function (text, target) {
        Array.from(text).forEach(function (char) { queue.push({ char: char, target: target }); });
        if (!running) { running = true; drain(); }
      },
      finish: function (fn) {
        done = true;
        callback = fn;
        if (!running && callback) { var finished = callback; callback = null; finished(); }
      }
    };
  }

  function displayError(bubble, message) {
    removeTypingIndicator();
    if (bubble) {
      bubble.hidden = false;
      bubble.classList.add("chat-message--error");
      bubble.textContent = message;
    } else {
      appendMessage(message, "error");
    }
  }

  async function doSendMessage() {
    if (streaming) return;
    var input = document.getElementById("pm-chat-input");
    var send = document.getElementById("pm-chat-send");
    var question = input && input.value.trim();
    if (!question) return;

    streaming = true;
    input.value = "";
    input.disabled = true;
    send.disabled = true;
    appendMessage(question, "user");
    showTypingIndicator();
    var bubble = createStreamingBubble();
    bubble.hidden = true;
    typewriter = startTypewriter();
    var reply = "";
    var firstToken = true;
    var hadError = false;

    try {
      var response = await fetch("/api/v1/chat/stream/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ message: question, language: "auto", chat_history: history.slice(-8) })
      });
      if (!response.ok || !response.body) throw new Error("stream unavailable");

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";
      var processFrame = function (frame) {
        var line = frame.split("\n").find(function (part) { return part.indexOf("data:") === 0; });
        if (!line) return;
        var data = line.slice(5).trim();
        if (data === "[DONE]") return;
        if (data.indexOf("[ERROR]") === 0) {
          hadError = true;
          displayError(bubble, data.slice(7).trim() || "Não foi possível conectar agora. Tente novamente.");
          return;
        }
        if (firstToken) {
          firstToken = false;
          removeTypingIndicator();
          bubble.hidden = false;
        }
        var text = data.replace(/\\n/g, "\n");
        reply += text;
        typewriter.enqueue(text, bubble);
      };

      while (true) {
        var result = await reader.read();
        buffer += decoder.decode(result.value || new Uint8Array(), { stream: !result.done });
        var frames = buffer.split("\n\n");
        buffer = frames.pop();
        frames.forEach(processFrame);
        if (result.done) break;
      }
      if (buffer.trim()) processFrame(buffer);
      if (!reply && !hadError) displayError(bubble, "Não foi possível obter uma resposta agora. Tente novamente ou use o formulário de contato.");
      if (reply) history.push({ role: "user", content: question }, { role: "assistant", content: reply });
    } catch (error) {
      console.error("P&M chat stream error", error);
      displayError(bubble, "Estou com dificuldades para conectar agora. Tente novamente em instantes.");
    } finally {
      typewriter.finish(function () {
        streaming = false;
        input.disabled = false;
        send.disabled = false;
        input.focus();
      });
      if (!reply || hadError) {
        streaming = false;
        input.disabled = false;
        send.disabled = false;
        input.focus();
      }
    }
  }

  window.sendQuickMessage = function (message) {
    var input = document.getElementById("pm-chat-input");
    if (!input) return;
    input.value = message;
    doSendMessage();
  };

  function initChatModal() {
    var modalInner = document.getElementById("pm-chat-modal-inner");
    if (!modalInner || modalInner.dataset.initialized === "true") return;
    modalInner.dataset.initialized = "true";
    var form = document.getElementById("pm-chat-form");
    var close = document.querySelector(".chat-window__close");
    var input = document.getElementById("pm-chat-input");
    if (!form || !input) return;
    form.addEventListener("submit", function (event) { event.preventDefault(); doSendMessage(); });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); doSendMessage(); }
    });
    if (close) close.addEventListener("click", window.closeChat);
    modalInner.addEventListener("click", function (event) {
      if (event.target === modalInner) window.closeChat();
    });
    var modal = getModal();
    if (modal) modal.addEventListener("click", function (event) {
      if (event.target === modal) window.closeChat();
    });
    input.focus();
  }

  document.addEventListener("keydown", function (event) {
    var modal = getModal();
    if (event.key === "Escape" && modal && !modal.hidden) window.closeChat();
  });
})();
