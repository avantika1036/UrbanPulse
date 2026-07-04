/**
 * App.jsx
 *
 * Root application component. Defines the global routing tree, lazy-loads
 * all page components for code-splitting, wraps everything in an error
 * boundary, and renders the persistent Navbar.
 */

import React, { Suspense, Component } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { THEME } from "./styles/theme.js";
import Navbar from "./components/Navbar.jsx";

// ── LAZY PAGE IMPORTS ──────────────────────────────────────────────────────
// Each page is its own chunk — loaded only when the route is first visited.

const HeroPage = React.lazy(() => import("./pages/HeroPage.jsx"));
const ComparePage = React.lazy(() => import("./pages/ComparePage.jsx"));
const AnalyticsPage = React.lazy(() => import("./pages/AnalyticsPage.jsx"));
const HealthDataPage = React.lazy(() => import("./pages/HealthDataPage.jsx"));

// ── PAGE LOADING FALLBACK ──────────────────────────────────────────────────

function PageLoader() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        flexDirection: "column",
        gap: THEME.spacing.md,
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          border: `3px solid ${THEME.colors.border}`,
          borderTopColor: THEME.colors.accent,
          borderRadius: THEME.radius.full,
          animation: "spin 0.8s linear infinite",
        }}
      />
      <span
        style={{
          color: THEME.colors.textMuted,
          fontSize: THEME.fontSizes.sm,
          fontFamily: THEME.fonts.body,
        }}
      >
        Loading...
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── GLOBAL ERROR BOUNDARY ──────────────────────────────────────────────────

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary] Uncaught error:", error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: THEME.colors.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: THEME.spacing.xl,
        }}
      >
        <div
          style={{
            maxWidth: "520px",
            width: "100%",
            backgroundColor: THEME.colors.surface,
            border: `1px solid ${THEME.colors.danger}`,
            borderRadius: THEME.radius.xl,
            padding: THEME.spacing.xxl,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "48px",
              marginBottom: THEME.spacing.lg,
            }}
          >
            ⚠
          </div>
          <h2
            style={{
              color: THEME.colors.text,
              fontSize: THEME.fontSizes.xxl,
              fontWeight: THEME.fontWeights.semibold,
              marginBottom: THEME.spacing.md,
              fontFamily: THEME.fonts.body,
            }}
          >
            Something went wrong
          </h2>
          <p
            style={{
              color: THEME.colors.textMuted,
              fontSize: THEME.fontSizes.md,
              lineHeight: THEME.lineHeights.relaxed,
              marginBottom: THEME.spacing.xl,
              fontFamily: THEME.fonts.body,
            }}
          >
            An unexpected error occurred in the UrbanPulse application.
          </p>
          {this.state.error && (
            <pre
              style={{
                backgroundColor: THEME.colors.bg,
                border: `1px solid ${THEME.colors.border}`,
                borderRadius: THEME.radius.md,
                padding: THEME.spacing.md,
                marginBottom: THEME.spacing.xl,
                fontSize: THEME.fontSizes.xs,
                fontFamily: THEME.fonts.mono,
                color: THEME.colors.danger,
                textAlign: "left",
                overflow: "auto",
                maxHeight: "120px",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {this.state.error.toString()}
            </pre>
          )}
          <button
            onClick={this.handleReset}
            style={{
              backgroundColor: THEME.colors.accent,
              color: THEME.colors.white,
              border: "none",
              borderRadius: THEME.radius.md,
              padding: `${THEME.spacing.sm} ${THEME.spacing.xl}`,
              fontSize: THEME.fontSizes.md,
              fontWeight: THEME.fontWeights.semibold,
              fontFamily: THEME.fonts.body,
              cursor: "pointer",
            }}
          >
            Return to Home
          </button>
        </div>
      </div>
    );
  }
}

// ── MAIN LAYOUT ───────────────────────────────────────────────────────────

function AppLayout({ children }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: THEME.colors.bg,
        fontFamily: THEME.fonts.body,
      }}
    >
      <Navbar />
      <main
        style={{
          flex: 1,
          paddingTop: THEME.layout.navHeight,
          width: "100%",
          maxWidth: THEME.layout.maxWidth,
          margin: "0 auto",
          padding: `${THEME.layout.navHeight} ${THEME.layout.contentPadding} ${THEME.spacing.xxl}`,
        }}
      >
        {children}
      </main>
      <footer
        style={{
          borderTop: `1px solid ${THEME.colors.border}`,
          padding: `${THEME.spacing.lg} ${THEME.spacing.xl}`,
          textAlign: "center",
        }}
      >
        <p
          style={{
            color: THEME.colors.textFaint,
            fontSize: THEME.fontSizes.xs,
            fontFamily: THEME.fonts.body,
          }}
        >
          UrbanPulse v1.0.0 — Healthcare scores seeded from real government data
          (BBMP · BMC · GCC · PMC · Delhi Health Dept). All other metrics
          synthetic (seed=42).
        </p>
      </footer>
    </div>
  );
}

// ── ROOT APP ──────────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <AppLayout>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Home — city cards, hero CTA, key stats */}
              <Route path="/" element={<HeroPage />} />

              {/* Compare — multi-city scoring form + results */}
              <Route path="/compare" element={<ComparePage />} />

              {/* Analytics — overview rankings, persona comparison */}
              <Route path="/analytics" element={<AnalyticsPage />} />

              {/* Health — real government births/deaths + hospital data */}
              <Route path="/health" element={<HealthDataPage />} />

              {/* Catch-all redirect to home */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AppLayout>
      </ErrorBoundary>
    </BrowserRouter>
  );
}