/**
 * theme.js
 *
 * Central design token object for UrbanPulse.
 * All component styles reference THEME — no hardcoded hex values elsewhere.
 *
 * Design language: dark navy base, electric blue accent, clean analytics
 * feel. No decorative gradients or drop-shadows except where they
 * communicate depth in a data-dense UI.
 */

export const THEME = {
  // ── COLOR PALETTE ──────────────────────────────────────────────────────
  colors: {
    // Backgrounds
    bg: "#0f172a",           // page background — deepest navy
    surface: "#1e293b",      // card / panel surface
    surface2: "#263248",     // slightly lighter surface for nested cards
    surfaceHover: "#2d3f5e", // hover state on interactive surfaces

    // Borders
    border: "#334155",       // default border
    borderLight: "#475569",  // lighter border for dividers

    // Text
    text: "#f1f5f9",         // primary text — near-white
    textMuted: "#94a3b8",    // secondary / label text
    textFaint: "#64748b",    // placeholder / disabled text

    // Accent
    accent: "#3b82f6",       // electric blue — primary CTA, highlights
    accentHover: "#2563eb",  // darker blue on hover
    accentLight: "#1d3a6e",  // very dark blue tint — accent backgrounds
    accentGlow: "rgba(59, 130, 246, 0.15)", // soft glow for selected states

    // Semantic
    success: "#22c55e",      // green — high scores, positive deltas
    successDim: "#14532d",   // dark green background
    warning: "#f59e0b",      // amber — mid-range, caution
    warningDim: "#451a03",   // dark amber background
    danger: "#ef4444",       // red — low scores, negative signals
    dangerDim: "#450a0a",    // dark red background

    // Neutrals
    white: "#ffffff",
    black: "#000000",

    // City brand colors (consistent across all charts)
    cities: {
      Mumbai: "#E63946",
      Bengaluru: "#457B9D",
      Chennai: "#2A9D8F",
      Pune: "#E9C46A",
      Delhi: "#F4A261",
      Hyderabad: "#264653",
    },

    // Persona colors
    personas: {
      early_career: "#3b82f6",
      family_focused: "#22c55e",
      budget_focused: "#f59e0b",
    },
  },

  // ── SPACING SCALE (4px base unit) ─────────────────────────────────────
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "16px",
    lg: "24px",
    xl: "32px",
    xxl: "48px",
    xxxl: "64px",
  },

  // ── BORDER RADIUS ─────────────────────────────────────────────────────
  radius: {
    sm: "4px",
    md: "8px",
    lg: "12px",
    xl: "16px",
    full: "9999px",
  },

  // ── SHADOWS ───────────────────────────────────────────────────────────
  shadows: {
    sm: "0 1px 3px rgba(0, 0, 0, 0.4)",
    md: "0 4px 12px rgba(0, 0, 0, 0.5)",
    lg: "0 12px 40px rgba(0, 0, 0, 0.7)",
    accent: "0 0 0 3px rgba(59, 130, 246, 0.25)",
    inset: "inset 0 1px 3px rgba(0, 0, 0, 0.3)",
    glow: "0 0 15px rgba(59, 130, 246, 0.4)",
  },

  // ── TYPOGRAPHY ────────────────────────────────────────────────────────
  fonts: {
    body: '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    mono: '"IBM Plex Mono", "Fira Code", "Cascadia Code", monospace',
  },

  fontSizes: {
    xs: "14px",
    sm: "16px",
    md: "18px",
    lg: "20px",
    xl: "24px",
    xxl: "32px",
    xxxl: "40px",
    display: "56px",
  },

  fontWeights: {
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeights: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },

  // ── LAYOUT ────────────────────────────────────────────────────────────
  layout: {
    maxWidth: "1200px",
    navHeight: "60px",
    contentPadding: "24px",
    contentPaddingMobile: "16px",
  },

  // ── TRANSITIONS ───────────────────────────────────────────────────────
  transitions: {
    fast: "all 0.1s ease",
    base: "all 0.2s ease",
    slow: "all 0.35s ease",
  },

  // ── Z-INDEX SCALE ─────────────────────────────────────────────────────
  zIndex: {
    base: 0,
    raised: 10,
    overlay: 100,
    modal: 200,
    nav: 300,
    toast: 400,
  },
};

// ── CONVENIENCE HELPERS ───────────────────────────────────────────────────

/**
 * Returns the city brand color for a given city name.
 * Falls back to accent blue if the city is not in the palette.
 * @param {string} cityName
 * @returns {string} hex color
 */
export function cityColor(cityName) {
  return THEME.colors.cities[cityName] ?? THEME.colors.accent;
}

/**
 * Returns the persona brand color.
 * @param {string} persona
 * @returns {string} hex color
 */
export function personaColor(persona) {
  return THEME.colors.personas[persona] ?? THEME.colors.accent;
}

/**
 * Maps a 0-100 score to a semantic color:
 *   >= 70 → success green
 *   >= 45 → warning amber
 *   <  45 → danger red
 * @param {number} score
 * @returns {string} hex color
 */
export function scoreColor(score) {
  if (score >= 70) return THEME.colors.success;
  if (score >= 45) return THEME.colors.warning;
  return THEME.colors.danger;
}

/**
 * Returns inline style object for a standard card/panel surface.
 * @param {Object} [overrides={}] - Additional inline style properties
 * @returns {Object}
 */
export function cardStyle(overrides = {}) {
  return {
    background: "linear-gradient(145deg, rgba(38, 50, 72, 0.85) 0%, rgba(30, 41, 59, 0.75) 100%)",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    border: `1px solid rgba(255, 255, 255, 0.08)`,
    borderTop: `1px solid rgba(255, 255, 255, 0.15)`,
    borderLeft: `1px solid rgba(255, 255, 255, 0.1)`,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.lg,
    boxShadow: `0 8px 32px rgba(0, 0, 0, 0.3)`,
    transition: THEME.transitions.base,
    ...overrides,
  };
}

/**
 * Returns inline style for a primary action button.
 * @param {boolean} [disabled=false]
 * @returns {Object}
 */
export function primaryButtonStyle(disabled = false) {
  return {
    background: disabled ? THEME.colors.borderLight : `linear-gradient(135deg, ${THEME.colors.accentHover}, ${THEME.colors.accent})`,
    color: THEME.colors.white,
    border: "none",
    borderRadius: THEME.radius.md,
    padding: `${THEME.spacing.sm} ${THEME.spacing.lg}`,
    fontSize: THEME.fontSizes.md,
    fontWeight: THEME.fontWeights.semibold,
    fontFamily: THEME.fonts.body,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: THEME.transitions.base,
    opacity: disabled ? 0.5 : 1,
    letterSpacing: "0.01em",
    boxShadow: disabled ? "none" : THEME.shadows.glow,
  };
}

/**
 * Returns inline style for a secondary / ghost button.
 * @param {boolean} [disabled=false]
 * @returns {Object}
 */
export function secondaryButtonStyle(disabled = false) {
  return {
    backgroundColor: "transparent",
    color: disabled ? THEME.colors.textFaint : THEME.colors.accent,
    border: `1px solid ${disabled ? THEME.colors.border : THEME.colors.accent}`,
    borderRadius: THEME.radius.md,
    padding: `${THEME.spacing.sm} ${THEME.spacing.lg}`,
    fontSize: THEME.fontSizes.md,
    fontWeight: THEME.fontWeights.medium,
    fontFamily: THEME.fonts.body,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: THEME.transitions.base,
    opacity: disabled ? 0.5 : 1,
  };
}

/**
 * Standard input/select style.
 * @returns {Object}
 */
export function inputStyle() {
  return {
    backgroundColor: THEME.colors.surface2,
    color: THEME.colors.text,
    border: `1px solid ${THEME.colors.border}`,
    borderRadius: THEME.radius.md,
    padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
    fontSize: THEME.fontSizes.md,
    fontFamily: THEME.fonts.body,
    width: "100%",
    outline: "none",
    transition: THEME.transitions.base,
  };
}

export default THEME;