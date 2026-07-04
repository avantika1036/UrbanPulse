import React from "react";
import { THEME, personaColor } from "../styles/theme.js";

const PERSONAS = [
  {
    key: "early_career",
    label: "Early Career",
    description: "Growth, jobs, affordability",
  },
  {
    key: "family_focused",
    label: "Family Focused",
    description: "Healthcare, schools, safety",
  },
  {
    key: "budget_focused",
    label: "Budget Focused",
    description: "Lowest cost, max value",
  },
];

export default function PersonaToggle({ value, onChange, disabled = false }) {
  return (
    <div>
      <p
        style={{
          fontSize: THEME.fontSizes.xs,
          fontWeight: THEME.fontWeights.semibold,
          color: THEME.colors.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: THEME.spacing.sm,
          fontFamily: THEME.fonts.body,
        }}
      >
        Persona
      </p>
      <div
        style={{
          display: "flex",
          gap: THEME.spacing.sm,
          flexWrap: "wrap",
        }}
        role="radiogroup"
        aria-label="Select persona"
      >
        {PERSONAS.map(({ key, label, description }) => {
          const isActive = value === key;
          const color = personaColor(key);
          return (
            <button
              key={key}
              role="radio"
              aria-checked={isActive}
              disabled={disabled}
              onClick={() => !disabled && onChange(key)}
              title={description}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: "2px",
                padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                backgroundColor: isActive
                  ? `${color}22`
                  : THEME.colors.surface2,
                border: `1px solid ${isActive ? color : THEME.colors.border}`,
                borderRadius: THEME.radius.md,
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1,
                transition: THEME.transitions.base,
                textAlign: "left",
                minWidth: "140px",
              }}
            >
              <span
                style={{
                  fontSize: THEME.fontSizes.sm,
                  fontWeight: THEME.fontWeights.semibold,
                  color: isActive ? color : THEME.colors.text,
                  fontFamily: THEME.fonts.body,
                }}
              >
                {label}
              </span>
              <span
                style={{
                  fontSize: THEME.fontSizes.xs,
                  color: THEME.colors.textFaint,
                  fontFamily: THEME.fonts.body,
                }}
              >
                {description}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}