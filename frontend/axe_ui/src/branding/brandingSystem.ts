/**
 * Custom Branding System for AXE Widget
 * 
 * Supports custom colors, logos, headers, and themes per application.
 */

export interface BrandingTheme {
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  backgroundColor: string;
  textColor: string;
  borderColor: string;
}

export interface BrandingAssets {
  logo?: string; // URL to logo image
  favicon?: string; // URL to favicon
  headerBackground?: string; // URL to header background image
}

export interface BrandingText {
  headerTitle: string;
  placeholder?: string;
  initialMessage?: string;
  errorMessage?: string;
  emptyStateMessage?: string;
}

export interface BrandingConfig {
  appId: string;
  theme?: Partial<BrandingTheme>;
  assets?: BrandingAssets;
  text?: Partial<BrandingText>;
  customCSS?: string;
}

// Default theme
const DEFAULT_THEME: BrandingTheme = {
  primaryColor: "#3b82f6",
  secondaryColor: "#1d4ed8",
  accentColor: "#10b981",
  backgroundColor: "#ffffff",
  textColor: "#1f2937",
  borderColor: "#e5e7eb",
};

const DEFAULT_TEXT: BrandingText = {
  headerTitle: "AXE Chat",
  placeholder: "Type a message...",
  initialMessage: "Hello! How can I help you?",
  errorMessage: "Something went wrong. Please try again.",
  emptyStateMessage: "Start a conversation",
};

/**
 * Branding system manager
 */
export class BrandingSystem {
  private config: BrandingConfig;
  private theme: BrandingTheme;
  private text: BrandingText;

  constructor(config: BrandingConfig) {
    this.config = config;
    this.theme = { ...DEFAULT_THEME, ...config.theme };
    this.text = { ...DEFAULT_TEXT, ...config.text };
  }

  /**
   * Get merged theme
   */
  getTheme(): BrandingTheme {
    return { ...this.theme };
  }

  /**
   * Get merged text
   */
  getText(): BrandingText {
    return { ...this.text };
  }

  /**
   * Get assets
   */
  getAssets(): BrandingAssets {
    return this.config.assets || {};
  }

  /**
   * Generate CSS variables from theme
   */
  generateCSSVariables(): string {
    const vars = [
      `--axe-color-primary: ${this.theme.primaryColor}`,
      `--axe-color-secondary: ${this.theme.secondaryColor}`,
      `--axe-color-accent: ${this.theme.accentColor}`,
      `--axe-color-background: ${this.theme.backgroundColor}`,
      `--axe-color-text: ${this.theme.textColor}`,
      `--axe-color-border: ${this.theme.borderColor}`,
    ];

    return `:root { ${vars.map((v) => v + ";").join(" ")} }`;
  }

  /**
   * Apply branding to DOM
   */
  applyToDOM(): void {
    // Apply CSS variables
    const style = document.createElement("style");
    style.textContent = this.generateCSSVariables();
    if (this.config.customCSS) {
      style.textContent += "\n" + this.config.customCSS;
    }
    document.head.appendChild(style);

    // Apply favicon if provided
    if (this.config.assets?.favicon) {
      const link = document.createElement("link");
      link.rel = "icon";
      link.href = this.config.assets.favicon;
      document.head.appendChild(link);
    }
  }

  /**
   * Update theme dynamically
   */
  updateTheme(updates: Partial<BrandingTheme>): void {
    this.theme = { ...this.theme, ...updates };

    // Re-apply CSS variables
    const existingStyle = document.querySelector('style[data-axe-branding="true"]');
    if (existingStyle) {
      existingStyle.remove();
    }

    const style = document.createElement("style");
    style.setAttribute("data-axe-branding", "true");
    style.textContent = this.generateCSSVariables();
    document.head.appendChild(style);
  }

  /**
   * Get HTML class for theme variant
   */
  getThemeClass(): string {
    // Determine if light or dark based on background brightness
    const bgColor = this.theme.backgroundColor;
    const isDark = this.isDarkColor(bgColor);
    return isDark ? "axe-theme-dark" : "axe-theme-light";
  }

  /**
   * Check if color is dark (simple heuristic)
   */
  private isDarkColor(color: string): boolean {
    const hex = color.replace("#", "");
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness < 128;
  }

  /**
   * Export theme as JSON
   */
  export(): BrandingConfig {
    return {
      appId: this.config.appId,
      theme: this.theme,
      assets: this.config.assets,
      text: this.text,
      customCSS: this.config.customCSS,
    };
  }
}

/**
 * Predefined branding templates
 */
export const BRANDING_TEMPLATES = {
  light: {
    theme: {
      primaryColor: "#3b82f6",
      secondaryColor: "#1d4ed8",
      accentColor: "#10b981",
      backgroundColor: "#ffffff",
      textColor: "#1f2937",
      borderColor: "#e5e7eb",
    },
  },

  dark: {
    theme: {
      primaryColor: "#60a5fa",
      secondaryColor: "#3b82f6",
      accentColor: "#34d399",
      backgroundColor: "#1f2937",
      textColor: "#f3f4f6",
      borderColor: "#4b5563",
    },
  },

  minimal: {
    theme: {
      primaryColor: "#000000",
      secondaryColor: "#333333",
      accentColor: "#666666",
      backgroundColor: "#ffffff",
      textColor: "#000000",
      borderColor: "#cccccc",
    },
  },

  vibrant: {
    theme: {
      primaryColor: "#ff6b6b",
      secondaryColor: "#ee5a6f",
      accentColor: "#f39c12",
      backgroundColor: "#ffffff",
      textColor: "#2d3436",
      borderColor: "#dfe6e9",
    },
  },

  ocean: {
    theme: {
      primaryColor: "#0077be",
      secondaryColor: "#005fa3",
      accentColor: "#00a8e8",
      backgroundColor: "#f0f9ff",
      textColor: "#005fa3",
      borderColor: "#e0f2fe",
    },
  },

  forest: {
    theme: {
      primaryColor: "#165e3a",
      secondaryColor: "#0d3b1f",
      accentColor: "#10b981",
      backgroundColor: "#f0fdf4",
      textColor: "#065f46",
      borderColor: "#d1fae5",
    },
  },
};

/**
 * Create branding from template
 */
export function createBrandingFromTemplate(
  appId: string,
  templateName: keyof typeof BRANDING_TEMPLATES
): BrandingConfig {
  const template = BRANDING_TEMPLATES[templateName] || BRANDING_TEMPLATES.light;
  return {
    appId,
    theme: template.theme,
  };
}
