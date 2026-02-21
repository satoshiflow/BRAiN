// BRAiN OS Design Tokens
// Single Source of Truth for Colors, Spacing, Typography

export const colors = {
  // Base Surfaces (Dark Blue)
  background: {
    main: "#0F172A",
    surface: "#111827",
    card: "#1E293B",
    elevated: "#0B1220",
  },
  
  // Text / Neutrals
  text: {
    primary: "#E5E7EB",
    muted: "#9CA3AF",
    disabled: "#6B7280",
  },
  
  // Accent (Gold)
  accent: {
    primary: "#C9A227",
    hover: "#E6C75A",
    muted: "#8A6F1A",
  },
  
  // Status Colors
  status: {
    success: "#10B981",
    warning: "#F59E0B",
    danger: "#EF4444",
    info: "#3B82F6",
  },
  
  // Border
  border: {
    muted: "#334155",
    DEFAULT: "#334155",
  },
} as const;

export const spacing = {
  // 8px Grid System
  0: "0px",
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  5: "20px",
  6: "24px",
  8: "32px",
  10: "40px",
  12: "48px",
  16: "64px",
  20: "80px",
  24: "96px",
} as const;

export const typography = {
  // Font Sizes
  size: {
    xs: "12px",
    sm: "13px",
    base: "14px",
    lg: "16px",
    xl: "18px",
    "2xl": "20px",
    "3xl": "24px",
    "4xl": "32px",
  },
  
  // Font Weights
  weight: {
    normal: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
  },
  
  // Line Heights
  lineHeight: {
    tight: "1.25",
    normal: "1.5",
    relaxed: "1.75",
  },
} as const;

export const radius = {
  none: "0",
  sm: "4px",
  DEFAULT: "8px",
  md: "8px",
  lg: "12px",
  xl: "16px",
  full: "9999px",
} as const;

// Layout Limits (enforce density rules)
export const layout = {
  maxKpiCardsPerRow: 4,
  maxChartsPerPage: 2,
  maxPanelsPerPage: 3,
  maxItemsBeforeVirtualization: 100,
} as const;

// Breakpoints
export const breakpoints = {
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
  "2xl": "1536px",
} as const;

// Accessibility
export const accessibility = {
  // Minimum target sizes
  minTapTarget: {
    mobile: 44,  // px
    desktop: 24, // px
  },
  // Min font size for mobile (prevents iOS zoom)
  minMobileFontSize: 16, // px
} as const;