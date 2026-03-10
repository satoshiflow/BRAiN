/**
 * AXE Widget Runtime Bundle
 *
 * Exposes a mount API consumed by embed.js:
 * window.AXEWidgetRuntime.mount(container, config, bridge)
 */

(function () {
  var LOCAL_HOSTS = {
    localhost: true,
    "127.0.0.1": true,
    "::1": true,
  };

  function inferDefaultBackendUrl() {
    if (typeof window !== "undefined" && LOCAL_HOSTS[window.location.hostname]) {
      return "http://127.0.0.1:8000";
    }

    return "https://api.brain.falklabs.de";
  }

  function resolveBackendBaseUrl(config) {
    var candidate = config && config.backendUrl ? String(config.backendUrl).trim() : "";
    var source = candidate || inferDefaultBackendUrl();

    try {
      return new URL(source).origin;
    } catch (_error) {
      return inferDefaultBackendUrl();
    }
  }

  function getBackendChatUrl(config) {
    return resolveBackendBaseUrl(config) + "/api/axe/chat";
  }

  function createRuntimeWidget(container, config, bridge) {
    const positionMap = {
      "bottom-right": { bottom: "16px", right: "16px" },
      "bottom-left": { bottom: "16px", left: "16px" },
      "top-right": { top: "16px", right: "16px" },
      "top-left": { top: "16px", left: "16px" },
    };

    const position = positionMap[config.position] || positionMap["bottom-right"];
    const positionStyle = Object.entries(position)
      .map(function (entry) {
        return entry[0] + ": " + entry[1];
      })
      .join("; ");

    const primaryColor = (config.branding && config.branding.colors && config.branding.colors.primary) || "#3b82f6";
    const secondaryColor = (config.branding && config.branding.colors && config.branding.colors.secondary) || "#1d4ed8";

    container.innerHTML = ""
      + '<div style="'
      + 'position: fixed; '
      + positionStyle + '; '
      + 'width: 56px; '
      + 'height: 56px; '
      + 'border-radius: 9999px; '
      + 'background: linear-gradient(to bottom right, ' + primaryColor + ', ' + secondaryColor + '); '
      + 'color: white; '
      + 'box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); '
      + 'cursor: pointer; '
      + 'display: flex; '
      + 'align-items: center; '
      + 'justify-content: center; '
      + 'font-size: 24px; '
      + 'z-index: 50; '
      + 'transition: box-shadow 0.2s; '
      + '" id="axe-widget-button" title="Chat with AXE">'
      + ((config.branding && config.branding.logo)
          ? '<img src="' + config.branding.logo + '" style="width: 32px; height: 32px;" alt="AXE" />'
          : "&#128172;")
      + "</div>";

    var isOpen = false;
    var isSending = false;
    var messages = [];
    var button = container.querySelector("#axe-widget-button");

    function renderMessage(content, role) {
      var messagesRoot = document.getElementById("axe-widget-messages");
      if (!messagesRoot) {
        return;
      }

      var wrapper = document.createElement("div");
      wrapper.style.display = "flex";
      wrapper.style.marginBottom = "10px";
      wrapper.style.justifyContent = role === "user" ? "flex-end" : "flex-start";

      var bubble = document.createElement("div");
      bubble.style.maxWidth = "80%";
      bubble.style.padding = "8px 10px";
      bubble.style.borderRadius = "8px";
      bubble.style.fontSize = "13px";
      bubble.style.lineHeight = "1.4";
      bubble.style.whiteSpace = "pre-wrap";
      bubble.style.background = role === "user" ? "#3b82f6" : "#f1f5f9";
      bubble.style.color = role === "user" ? "#ffffff" : "#0f172a";
      bubble.textContent = content;

      wrapper.appendChild(bubble);
      messagesRoot.appendChild(wrapper);
      messagesRoot.scrollTop = messagesRoot.scrollHeight;
    }

    function setSendingState(sending) {
      isSending = sending;
      var input = document.getElementById("axe-panel-input");
      var sendButton = document.getElementById("axe-panel-send");
      if (!input || !sendButton) {
        return;
      }

      input.disabled = sending;
      sendButton.disabled = sending;
      sendButton.style.opacity = sending ? "0.6" : "1";
      sendButton.style.cursor = sending ? "not-allowed" : "pointer";
    }

    function showPanel() {
      var panel = document.getElementById("axe-widget-panel");
      if (!panel) {
        var panelPositionMap = {
          "bottom-right": { bottom: "80px", right: "16px" },
          "bottom-left": { bottom: "80px", left: "16px" },
          "top-right": { top: "80px", right: "16px" },
          "top-left": { top: "80px", left: "16px" },
        };

        var panelPosition = panelPositionMap[config.position] || panelPositionMap["bottom-right"];
        var panelPositionStyle = Object.entries(panelPosition)
          .map(function (entry) {
            return entry[0] + ": " + entry[1];
          })
          .join("; ");

        panel = document.createElement("div");
        panel.id = "axe-widget-panel";
        panel.innerHTML = ""
          + '<div style="'
          + 'position: fixed; '
          + panelPositionStyle + '; '
          + 'width: 320px; '
          + 'height: 384px; '
          + 'border-radius: 8px; '
          + 'box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2); '
          + 'background: white; '
          + 'display: flex; '
          + 'flex-direction: column; '
          + 'z-index: 49; '
          + 'overflow: hidden; '
          + '">'
          + '<div style="display: flex; align-items: center; justify-content: space-between; padding: 16px; background: #f0f9ff; border-bottom: 1px solid #e0f2fe;">'
          + '<h2 style="font-weight: 600; font-size: 14px; margin: 0;">'
          + ((config.branding && config.branding.headerText) || "AXE Chat")
          + "</h2>"
          + '<button id="axe-panel-close" style="background: none; border: none; cursor: pointer; padding: 4px; font-size: 16px;">&times;</button>'
          + "</div>"
          + '<div id="axe-widget-messages" style="flex: 1; overflow-y: auto; padding: 12px; background: #ffffff;">'
          + '<div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">'
          + '<div style="max-width: 80%; padding: 8px 10px; border-radius: 8px; font-size: 13px; line-height: 1.4; background: #f1f5f9; color: #0f172a;">'
          + "Hi! I am AXE. Ask me anything."
          + "</div>"
          + "</div>"
          + "</div>"
          + '<div style="display: flex; gap: 8px; border-top: 1px solid #e2e8f0; padding: 10px; background: #f8fafc;">'
          + '<input id="axe-panel-input" type="text" placeholder="Type a message..." style="flex: 1; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 10px; font-size: 13px; color: #0f172a;" />'
          + '<button id="axe-panel-send" style="border: none; border-radius: 6px; background: #2563eb; color: #ffffff; width: 36px; height: 36px; font-size: 14px;">&#10148;</button>'
          + "</div>"
          + "</div>";

        container.appendChild(panel);

        var closeButton = panel.querySelector("#axe-panel-close");
        if (closeButton) {
          closeButton.addEventListener("click", function () {
            hidePanel();
          });
        }

        var sendButton = panel.querySelector("#axe-panel-send");
        var input = panel.querySelector("#axe-panel-input");

        if (sendButton) {
          sendButton.addEventListener("click", function () {
            if (!input) {
              return;
            }
            sendMessage(input.value);
          });
        }

        if (input) {
          input.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              sendMessage(input.value);
            }
          });
        }
      }

      panel.style.display = "block";
      isOpen = true;
      bridge.emit("open");
    }

    function hidePanel() {
      var panel = document.getElementById("axe-widget-panel");
      if (panel) {
        panel.style.display = "none";
      }
      isOpen = false;
      bridge.emit("close");
    }

    function sendMessage(content) {
      var trimmedContent = (content || "").trim();
      var input = document.getElementById("axe-panel-input");

      if (!trimmedContent || isSending) {
        return;
      }

      messages.push({ role: "user", content: trimmedContent });
      renderMessage(trimmedContent, "user");
      bridge.emit("message-sent", { content: trimmedContent });

      if (input) {
        input.value = "";
      }

      setSendingState(true);

      fetch(getBackendChatUrl(config), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-App-Id": config.appId,
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: messages.map(function (message) {
            return {
              role: message.role,
              content: message.content,
            };
          }),
          temperature: 0.7,
        }),
      })
        .then(function (response) {
          if (!response.ok) {
            return response.text().then(function (text) {
              throw new Error(text || "Backend request failed with status " + response.status);
            });
          }

          return response.json();
        })
        .then(function (payload) {
          var responseText = payload && payload.text ? payload.text : "No response text returned.";
          messages.push({ role: "assistant", content: responseText });
          renderMessage(responseText, "assistant");
          bridge.emit("message-received", { content: responseText });
        })
        .catch(function (error) {
          var message = error instanceof Error ? error.message : "Message delivery failed";
          renderMessage("Request failed: " + message, "assistant");
          bridge.emit("error", {
            code: "BACKEND_UNAVAILABLE",
            message: message,
          });
          bridge.log("error", "Runtime sendMessage failed", { message: message });
        })
        .finally(function () {
          setSendingState(false);
        });
    }

    button.addEventListener("mouseenter", function () {
      button.style.boxShadow = "0 25px 30px -5px rgba(0, 0, 0, 0.15)";
    });

    button.addEventListener("mouseleave", function () {
      button.style.boxShadow = "0 20px 25px -5px rgba(0, 0, 0, 0.1)";
    });

    button.addEventListener("click", function () {
      if (isOpen) {
        hidePanel();
      } else {
        showPanel();
      }
    });

    bridge.log("info", "Real widget runtime mounted", { appId: config.appId });

    return {
      open: showPanel,
      close: hidePanel,
      isOpen: function () {
        return isOpen;
      },
      sendMessage: function (content) {
        if (!isOpen) {
          showPanel();
        }
        sendMessage(content);
      },
      destroy: function () {
        if (container && container.parentNode) {
          container.parentNode.removeChild(container);
        }
      },
    };
  }

  window.AXEWidgetRuntime = {
    mount: createRuntimeWidget,
  };
})();
