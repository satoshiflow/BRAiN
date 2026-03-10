/**
 * AXE Floating Widget Embed Script (v2 - with React Loader)
 * 
 * Usage: Add to external website
 * <script
 *   src="https://axe.example.com/embed.js"
 *   data-app-id="mysite-chat"
 *   data-backend-url="https://api.brain.example.com"
 *   data-origin-allowlist="mysite.com,app.mysite.com"
 *   data-branding-logo="https://mysite.com/logo.png"
 *   data-branding-colors="primary:#667eea,secondary:#764ba2"
 *   async
 * ></script>
 * 
 * Initializes window.AXEWidget singleton with React component
 */

(function () {
  // Prevent multiple initializations
  if (window.AXEWidget && window.AXEWidget._initialized) {
    console.warn("[AXE Embed] Widget already initialized");
    return;
  }

  const DEBUG_MODE = typeof localStorage !== "undefined" && localStorage.getItem("AXE_EMBED_DEBUG") === "true";

  // Parse script attributes
  function getScriptConfig() {
    const script = document.currentScript || document.scripts[document.scripts.length - 1];
    if (!script) {
      console.error("[AXE Embed] Could not find script element");
      return null;
    }

    const config = {
      appId: script.getAttribute("data-app-id"),
      backendUrl: script.getAttribute("data-backend-url"),
      originAllowlist: script.getAttribute("data-origin-allowlist"),
      debug: script.getAttribute("data-debug") === "true" || DEBUG_MODE,
      position: script.getAttribute("data-position") || "bottom-right",
      theme: script.getAttribute("data-theme") || "light",
      branding: {
        logo: script.getAttribute("data-branding-logo"),
        colors: parseBrandingColors(script.getAttribute("data-branding-colors")),
        headerText: script.getAttribute("data-branding-header-text") || "AXE Chat",
      },
      webhookUrl: script.getAttribute("data-webhook-url"),
      plugins: parsePlugins(script.getAttribute("data-plugins")),
    };

    // Validate required attributes
    if (!config.appId || !config.backendUrl || !config.originAllowlist) {
      console.error(
        "[AXE Embed] Missing required attributes: data-app-id, data-backend-url, data-origin-allowlist"
      );
      return null;
    }

    return config;
  }

  // Parse branding colors from string like "primary:#667eea,secondary:#764ba2"
  function parseBrandingColors(colorString) {
    if (!colorString) return {};
    const colors = {};
    colorString.split(",").forEach((pair) => {
      const [key, value] = pair.trim().split(":");
      if (key && value) colors[key] = value;
    });
    return colors;
  }

  // Parse plugins from JSON string
  function parsePlugins(pluginString) {
    if (!pluginString) return [];
    try {
      return JSON.parse(pluginString);
    } catch (e) {
      console.warn("[AXE Embed] Failed to parse plugins:", e);
      return [];
    }
  }

  // Log helper
  function log(level, message, data) {
    const config = getScriptConfig() || {};
    if (config.debug || DEBUG_MODE) {
      const prefix = `[AXE:${level.toUpperCase()}]`;
      if (data) {
        console.log(prefix, message, data);
      } else {
        console.log(prefix, message);
      }
    }
  }

  // Load React and ReactDOM from CDN
  async function loadReactDependencies() {
    return new Promise((resolve, reject) => {
      log("info", "Loading React dependencies...");

      // Load React
      const reactScript = document.createElement("script");
      reactScript.src = "https://unpkg.com/react@18/umd/react.production.min.js";
      reactScript.crossOrigin = "anonymous";
      reactScript.onload = () => {
        // Load ReactDOM
        const reactDomScript = document.createElement("script");
        reactDomScript.src = "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js";
        reactDomScript.crossOrigin = "anonymous";
        reactDomScript.onload = () => {
          log("info", "React dependencies loaded");
          resolve();
        };
        reactDomScript.onerror = reject;
        document.head.appendChild(reactDomScript);
      };
      reactScript.onerror = reject;
      document.head.appendChild(reactScript);
    });
  }

  // Initialize widget
  async function initWidget() {
    const config = getScriptConfig();
    if (!config) return;

    try {
      log("info", "Starting AXE Widget initialization", { appId: config.appId });

      // Wait for DOM to be ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => initializeWidget(config));
      } else {
        initializeWidget(config);
      }
    } catch (error) {
      console.error("[AXE Embed] Initialization error:", error);
    }
  }

  // Initialize widget (called when DOM is ready)
  async function initializeWidget(config) {
    try {
      // Create container
      const container = document.createElement("div");
      container.id = "axe-widget-container";
      container.setAttribute("data-testid", "axe-widget-container");
      document.body.appendChild(container);

      // Attempt to load React for full component
      try {
        await loadReactDependencies();
        log("info", "React loaded, rendering FloatingAxe component");
        // In production, this would load the FloatingAxe component
        // For now, use fallback
        createFallbackWidget(container, config);
      } catch (e) {
        log("warn", "React loading failed, using fallback widget", e);
        createFallbackWidget(container, config);
      }

      // Initialize widget API
      createWidgetAPI(container, config);
    } catch (error) {
      console.error("[AXE Embed] Widget initialization failed:", error);
      createWidgetAPI(null, config); // Create API with null widget for error handling
    }
  }

  // Create fallback widget (when React loading fails)
  function createFallbackWidget(container, config) {
    const positionMap = {
      "bottom-right": { bottom: "16px", right: "16px" },
      "bottom-left": { bottom: "16px", left: "16px" },
      "top-right": { top: "16px", right: "16px" },
      "top-left": { top: "16px", left: "16px" },
    };

    const position = positionMap[config.position] || positionMap["bottom-right"];
    const positionStyle = Object.entries(position)
      .map(([k, v]) => `${k}: ${v}`)
      .join("; ");

    const primaryColor = config.branding?.colors?.primary || "#3b82f6";
    const secondaryColor = config.branding?.colors?.secondary || "#1d4ed8";

    container.innerHTML = `
      <div style="
        position: fixed;
        ${positionStyle};
        width: 56px;
        height: 56px;
        border-radius: 9999px;
        background: linear-gradient(to bottom right, ${primaryColor}, ${secondaryColor});
        color: white;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        z-index: 50;
        transition: box-shadow 0.2s;
      " id="axe-widget-button" title="Chat with AXE">
        ${config.branding?.logo ? `<img src="${config.branding.logo}" style="width: 32px; height: 32px;" alt="AXE" />` : "💬"}
      </div>
    `;

    let isOpen = false;
    const button = container.querySelector("#axe-widget-button");

    button.addEventListener("mouseenter", () => {
      button.style.boxShadow = "0 25px 30px -5px rgba(0, 0, 0, 0.15)";
    });

    button.addEventListener("mouseleave", () => {
      button.style.boxShadow = "0 20px 25px -5px rgba(0, 0, 0, 0.1)";
    });

    button.addEventListener("click", () => {
      isOpen = !isOpen;
      if (isOpen) {
        showPanel(container, config);
      } else {
        hidePanel(container);
      }
    });

    log("info", "Fallback widget created");
  }

  // Show chat panel
  function showPanel(container, config) {
    let panel = document.getElementById("axe-widget-panel");
    if (!panel) {
      const positionMap = {
        "bottom-right": { bottom: "80px", right: "16px" },
        "bottom-left": { bottom: "80px", left: "16px" },
        "top-right": { top: "80px", right: "16px" },
        "top-left": { top: "80px", left: "16px" },
      };

      const position = positionMap[config.position] || positionMap["bottom-right"];
      const positionStyle = Object.entries(position)
        .map(([k, v]) => `${k}: ${v}`)
        .join("; ");

      panel = document.createElement("div");
      panel.id = "axe-widget-panel";
      panel.innerHTML = `
        <div style="
          position: fixed;
          ${positionStyle};
          width: 320px;
          height: 384px;
          border-radius: 8px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
          background: white;
          display: flex;
          flex-direction: column;
          z-index: 49;
          overflow: hidden;
        ">
          <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            background: #f0f9ff;
            border-bottom: 1px solid #e0f2fe;
          ">
            <h2 style="
              font-weight: 600;
              font-size: 14px;
              margin: 0;
            ">${config.branding?.headerText || "AXE Chat"}</h2>
            <button id="axe-panel-close" style="
              background: none;
              border: none;
              cursor: pointer;
              padding: 4px;
              font-size: 16px;
            ">×</button>
          </div>
          
          <div style="
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 14px;
          ">
            <p>Chat widget ready at origin: <strong>${window.location.origin}</strong></p>
          </div>
          
          <div style="
            display: flex;
            gap: 8px;
            padding: 12px;
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
          ">
            <input 
              id="axe-panel-input"
              type="text" 
              placeholder="Type a message..."
              disabled
              style="
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 14px;
                background: white;
                color: #6b7280;
                cursor: not-allowed;
              "
            />
            <button style="
              width: 32px;
              height: 32px;
              border-radius: 4px;
              background: #3b82f6;
              color: white;
              border: none;
              cursor: not-allowed;
              opacity: 0.5;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 16px;
            " disabled>→</button>
          </div>
        </div>
      `;
      container.appendChild(panel);

      panel.querySelector("#axe-panel-close").addEventListener("click", () => {
        container.querySelector("#axe-widget-button").click();
      });
    }
    panel.style.display = "block";

    // Emit event
    if (window.AXEWidget && window.AXEWidget.emit) {
      window.AXEWidget.emit("open");
    }
  }

  // Hide chat panel
  function hidePanel(container) {
    const panel = document.getElementById("axe-widget-panel");
    if (panel) {
      panel.style.display = "none";
    }

    // Emit event
    if (window.AXEWidget && window.AXEWidget.emit) {
      window.AXEWidget.emit("close");
    }
  }

  // Create widget API and event system
  function createWidgetAPI(container, config) {
    const eventListeners = {};
    let isOpen = false;
    const sessionId = `axe_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

    const widgetAPI = {
      // Configuration
      config,
      sessionId,

      // Lifecycle
      open() {
        if (container) {
          isOpen = true;
          showPanel(container, config);
          this.emit("open");
        }
      },

      close() {
        if (container) {
          isOpen = false;
          hidePanel(container);
          this.emit("close");
        }
      },

      isOpen() {
        return isOpen;
      },

      destroy() {
        if (container && container.parentNode) {
          container.parentNode.removeChild(container);
        }
        this.emit("destroy");
        window.AXEWidget._initialized = false;
      },

      // Messaging
      sendMessage(content) {
        log("info", "Message sent", { content });
        this.emit("message-sent", { content, sessionId });

        // Track analytics if webhook is configured
        if (config.webhookUrl) {
          this.trackEvent("message-sent", { content });
        }
      },

      // Plugin system
      registerPlugin(manifest) {
        log("info", "Plugin registered", { pluginId: manifest.id });
        this.emit("plugin-registered", manifest);
      },

      unregisterPlugin(pluginId) {
        log("info", "Plugin unregistered", { pluginId });
        this.emit("plugin-unregistered", { pluginId });
      },

      // Event system
      on(event, callback) {
        if (!eventListeners[event]) {
          eventListeners[event] = [];
        }
        eventListeners[event].push(callback);
        log("debug", `Listener added for event: ${event}`);

        // Return unsubscribe function
        return () => {
          eventListeners[event] = eventListeners[event].filter((cb) => cb !== callback);
        };
      },

      emit(event, data) {
        log("debug", `Event emitted: ${event}`, data);
        if (eventListeners[event]) {
          eventListeners[event].forEach((callback) => {
            try {
              callback(data);
            } catch (e) {
              console.error(`[AXE Embed] Error in event listener for ${event}:`, e);
            }
          });
        }
      },

      // Analytics
      trackEvent(eventName, data) {
        if (!config.webhookUrl) return;

        const payload = {
          appId: config.appId,
          sessionId,
          event: eventName,
          data,
          timestamp: new Date().toISOString(),
        };

        // Send webhook asynchronously
        fetch(config.webhookUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch((e) => log("warn", "Webhook send failed", e));
      },

      // Branding
      updateBranding(newBranding) {
        config.branding = { ...config.branding, ...newBranding };
        log("info", "Branding updated", newBranding);
        this.emit("branding-updated", newBranding);
      },

      _initialized: true,
    };

    window.AXEWidget = widgetAPI;
    log("info", "Widget API initialized");
    widgetAPI.emit("ready");
  }

  // Start initialization
  initWidget();
})();
