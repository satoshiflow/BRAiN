/**
 * AXE Floating Widget Embed Script
 * 
 * Usage: Add to external website
 * <script
 *   src="https://axe.example.com/embed.js"
 *   data-app-id="mysite-chat"
 *   data-backend-url="https://api.brain.example.com"
 *   data-origin-allowlist="mysite.com,app.mysite.com"
 *   async
 * ></script>
 * 
 * Initializes window.AXEWidget singleton
 */

(function () {
  // Prevent multiple initializations
  if (window.AXEWidget) {
    console.warn("[AXE Embed] Widget already initialized");
    return;
  }

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
      debug: script.getAttribute("data-debug") === "true",
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

  // Initialize widget
  async function initWidget() {
    const config = getScriptConfig();
    if (!config) return;

    try {
      // Wait for DOM to be ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => loadWidget(config));
      } else {
        loadWidget(config);
      }
    } catch (error) {
      console.error("[AXE Embed] Initialization error:", error);
    }
  }

  // Load the widget component
  async function loadWidget(config) {
    // Determine base URL (same origin as script)
    const scriptSrc = document.currentScript?.src || "";
    const baseUrl = new URL(scriptSrc).origin;

    // Create container
    const container = document.createElement("div");
    container.id = "axe-widget-container";
    container.setAttribute("data-testid", "axe-widget-container");
    document.body.appendChild(container);

    // Dynamically load React and widget component
    // In production, this would use a bundled UMD build
    // For now, log initialization
    console.log("[AXE Embed] Widget initialized with config:", {
      appId: config.appId,
      backendUrl: config.backendUrl,
      debug: config.debug,
    });

    // Create a mock widget for now (will be replaced with actual React component)
    createMockWidget(container, config);
  }

  // Temporary: create a mock widget for testing
  function createMockWidget(container, config) {
    container.innerHTML = `
      <div style="
        position: fixed;
        bottom: 16px;
        right: 16px;
        width: 56px;
        height: 56px;
        border-radius: 9999px;
        background: linear-gradient(to bottom right, #3b82f6, #1d4ed8);
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
        💬
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

    // Expose widget API
    window.AXEWidget = {
      config,
      open: () => {
        if (!isOpen) {
          isOpen = true;
          showPanel(container, config);
        }
      },
      close: () => {
        if (isOpen) {
          isOpen = false;
          hidePanel(container);
        }
      },
      isOpen: () => isOpen,
      sendMessage: (message) => {
        console.log("[AXE Widget] Message:", message);
        // Will be implemented when React component is loaded
      },
    };

    console.log("[AXE Embed] Widget API available at window.AXEWidget");
  }

  // Show chat panel
  function showPanel(container, config) {
    let panel = document.getElementById("axe-widget-panel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "axe-widget-panel";
      panel.innerHTML = `
        <div style="
          position: fixed;
          bottom: 80px;
          right: 16px;
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
            ">AXE Chat</h2>
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
  }

  // Hide chat panel
  function hidePanel(container) {
    const panel = document.getElementById("axe-widget-panel");
    if (panel) {
      panel.style.display = "none";
    }
  }

  // Start initialization
  initWidget();
})();
