import React from "react";
import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { THEME } from "../styles/theme.js";

const NAV_LINKS = [
  { to: "/", label: "Home", exact: true },
  { to: "/compare", label: "Compare Cities" },
  { to: "/analytics", label: "Analytics" },
  { to: "/health", label: "Health Data" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const navStyle = {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    height: THEME.layout.navHeight,
    backgroundColor: scrolled
      ? `${THEME.colors.surface}f5`
      : THEME.colors.surface,
    backdropFilter: scrolled ? "blur(12px)" : "none",
    borderBottom: `1px solid ${THEME.colors.border}`,
    zIndex: THEME.zIndex.nav,
    transition: THEME.transitions.base,
    boxShadow: scrolled ? THEME.shadows.md : "none",
  };

  const innerStyle = {
    maxWidth: THEME.layout.maxWidth,
    margin: "0 auto",
    height: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: `0 ${THEME.layout.contentPadding}`,
  };

  const logoStyle = {
    fontFamily: THEME.fonts.body,
    fontSize: THEME.fontSizes.xl,
    fontWeight: THEME.fontWeights.bold,
    color: THEME.colors.text,
    letterSpacing: "-0.02em",
    display: "flex",
    alignItems: "center",
    gap: THEME.spacing.xs,
    textDecoration: "none",
  };

  const linkListStyle = {
    display: "flex",
    alignItems: "center",
    gap: THEME.spacing.xs,
    listStyle: "none",
  };

  const getLinkStyle = (isActive) => ({
    fontFamily: THEME.fonts.body,
    fontSize: THEME.fontSizes.sm,
    fontWeight: isActive ? THEME.fontWeights.semibold : THEME.fontWeights.medium,
    color: isActive ? THEME.colors.accent : THEME.colors.textMuted,
    padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
    borderRadius: THEME.radius.md,
    backgroundColor: isActive ? THEME.colors.accentGlow : "transparent",
    transition: THEME.transitions.base,
    textDecoration: "none",
    whiteSpace: "nowrap",
    borderBottom: isActive
      ? `2px solid ${THEME.colors.accent}`
      : "2px solid transparent",
  });

  const hamburgerStyle = {
    display: "none",
    flexDirection: "column",
    gap: "5px",
    background: "none",
    border: "none",
    padding: THEME.spacing.xs,
    cursor: "pointer",
  };

  const mobileMenuStyle = {
    position: "fixed",
    top: THEME.layout.navHeight,
    left: 0,
    right: 0,
    backgroundColor: THEME.colors.surface,
    borderBottom: `1px solid ${THEME.colors.border}`,
    padding: THEME.spacing.md,
    display: menuOpen ? "flex" : "none",
    flexDirection: "column",
    gap: THEME.spacing.xs,
    zIndex: THEME.zIndex.nav - 1,
    boxShadow: THEME.shadows.lg,
  };

  return (
    <>
      <nav style={navStyle} role="navigation" aria-label="Main navigation">
        <div style={innerStyle}>
          <NavLink to="/" style={logoStyle} aria-label="UrbanPulse home">
            <span style={{ color: THEME.colors.accent }}>Urban</span>
            <span>Pulse</span>
          </NavLink>

          {/* Desktop links */}
          <ul style={linkListStyle} className="nav-links-desktop">
            {NAV_LINKS.map(({ to, label }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === "/"}
                  style={({ isActive }) => getLinkStyle(isActive)}
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>

          {/* Mobile hamburger */}
          <button
            style={hamburgerStyle}
            className="hamburger"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                style={{
                  display: "block",
                  width: "22px",
                  height: "2px",
                  backgroundColor: THEME.colors.text,
                  borderRadius: "2px",
                  transition: THEME.transitions.base,
                  transformOrigin: "center",
                  transform:
                    menuOpen && i === 0
                      ? "rotate(45deg) translate(5px, 5px)"
                      : menuOpen && i === 1
                      ? "scaleX(0)"
                      : menuOpen && i === 2
                      ? "rotate(-45deg) translate(5px, -5px)"
                      : "none",
                }}
              />
            ))}
          </button>
        </div>
      </nav>

      {/* Mobile dropdown */}
      <div style={mobileMenuStyle} role="menu">
        {NAV_LINKS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            role="menuitem"
            style={({ isActive }) => ({
              ...getLinkStyle(isActive),
              display: "block",
              padding: THEME.spacing.md,
            })}
          >
            {label}
          </NavLink>
        ))}
      </div>

      {/* Responsive CSS injected inline */}
      <style>{`
        @media (max-width: 640px) {
          .nav-links-desktop { display: none !important; }
          .hamburger { display: flex !important; }
        }
      `}</style>
    </>
  );
}