import React from "react";
import { THEME, scoreColor, cityColor } from "../styles/theme.js";

const DIMENSIONS = [
  { key: "income_score", label: "Income vs CoL" },
  { key: "affordability_score", label: "Affordability" },
  { key: "healthcare_score", label: "Healthcare" },
  { key: "environment_score", label: "Environment" },
  { key: "career_growth_score", label: "Career Growth" },
  { key: "family_fit_score", label: "Family Fit" },
  { key: "adjusted_life_score", label: "Overall Score", isComposite: true },
];

function ScoreCell({ score, isComposite = false }) {
  const color = scoreColor(score);
  return (
    <td
      style={{
        padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
        textAlign: "center",
        borderBottom: `1px solid ${THEME.colors.border}`,
        backgroundColor: isComposite ? `${color}15` : "transparent",
      }}
    >
      <span
        style={{
          display: "inline-block",
          padding: `2px ${THEME.spacing.sm}`,
          borderRadius: THEME.radius.sm,
          backgroundColor: `${color}22`,
          color: color,
          fontSize: isComposite ? THEME.fontSizes.md : THEME.fontSizes.sm,
          fontWeight: isComposite
            ? THEME.fontWeights.bold
            : THEME.fontWeights.medium,
          fontFamily: THEME.fonts.mono,
          minWidth: "52px",
          textAlign: "center",
        }}
      >
        {score?.toFixed(1)}
      </span>
    </td>
  );
}

export default function CityComparisonTable({ scores, bestCity, citiesCompared }) {
  if (!scores || !citiesCompared || citiesCompared.length === 0) return null;

  const cityList = citiesCompared.filter((c) => scores[c]);

  return (
    <div
      style={{
        overflowX: "auto",
        borderRadius: THEME.radius.lg,
        border: `1px solid ${THEME.colors.border}`,
        boxShadow: THEME.shadows.md,
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontFamily: THEME.fonts.body,
          minWidth: "520px",
        }}
        aria-label="City score comparison table"
      >
        <thead>
          <tr style={{ backgroundColor: THEME.colors.surface2 }}>
            <th
              style={{
                padding: `${THEME.spacing.md} ${THEME.spacing.md}`,
                textAlign: "left",
                color: THEME.colors.textMuted,
                fontSize: THEME.fontSizes.xs,
                fontWeight: THEME.fontWeights.semibold,
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                borderBottom: `2px solid ${THEME.colors.border}`,
                whiteSpace: "nowrap",
                minWidth: "140px",
              }}
            >
              Dimension
            </th>
            {cityList.map((city) => {
              const isBest = city === bestCity;
              const color = cityColor(city);
              return (
                <th
                  key={city}
                  style={{
                    padding: `${THEME.spacing.md} ${THEME.spacing.md}`,
                    textAlign: "center",
                    borderBottom: `2px solid ${isBest ? THEME.colors.accent : THEME.colors.border}`,
                    borderLeft: isBest
                      ? `2px solid ${THEME.colors.accent}`
                      : `1px solid ${THEME.colors.border}`,
                    borderRight: isBest
                      ? `2px solid ${THEME.colors.accent}`
                      : "none",
                    backgroundColor: isBest
                      ? THEME.colors.accentLight
                      : THEME.colors.surface2,
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: THEME.spacing.xs,
                    }}
                  >
                    <div
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: THEME.radius.full,
                        backgroundColor: color,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        color: isBest ? THEME.colors.accent : THEME.colors.text,
                        fontSize: THEME.fontSizes.sm,
                        fontWeight: THEME.fontWeights.semibold,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {city}
                    </span>
                    {isBest && (
                      <span
                        style={{
                          fontSize: THEME.fontSizes.xs,
                          color: THEME.colors.accent,
                          fontWeight: THEME.fontWeights.bold,
                        }}
                      >
                        ★
                      </span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {DIMENSIONS.map(({ key, label, isComposite }, rowIdx) => (
            <tr
              key={key}
              style={{
                backgroundColor:
                  isComposite
                    ? THEME.colors.surface2
                    : rowIdx % 2 === 0
                    ? THEME.colors.surface
                    : `${THEME.colors.surface}cc`,
              }}
            >
              <td
                style={{
                  padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                  color: isComposite
                    ? THEME.colors.text
                    : THEME.colors.textMuted,
                  fontSize: isComposite
                    ? THEME.fontSizes.sm
                    : THEME.fontSizes.xs,
                  fontWeight: isComposite
                    ? THEME.fontWeights.semibold
                    : THEME.fontWeights.regular,
                  borderBottom: `1px solid ${THEME.colors.border}`,
                  borderTop: isComposite
                    ? `2px solid ${THEME.colors.border}`
                    : "none",
                  whiteSpace: "nowrap",
                }}
              >
                {isComposite ? "▶ " : ""}{label}
              </td>
              {cityList.map((city) => {
                const isBest = city === bestCity;
                return (
                  <td
                    key={city}
                    style={{
                      borderLeft: isBest
                        ? `2px solid ${THEME.colors.accent}`
                        : `1px solid ${THEME.colors.border}`,
                      borderRight: isBest
                        ? `2px solid ${THEME.colors.accent}`
                        : "none",
                      borderBottom: `1px solid ${THEME.colors.border}`,
                      borderTop: isComposite
                        ? `2px solid ${THEME.colors.border}`
                        : "none",
                      padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                      textAlign: "center",
                      backgroundColor: isBest
                        ? `${THEME.colors.accentLight}80`
                        : "transparent",
                    }}
                  >
                    <span
                      style={{
                        display: "inline-block",
                        padding: `2px ${THEME.spacing.sm}`,
                        borderRadius: THEME.radius.sm,
                        backgroundColor: `${scoreColor(scores[city]?.[key])}22`,
                        color: scoreColor(scores[city]?.[key]),
                        fontSize: isComposite
                          ? THEME.fontSizes.md
                          : THEME.fontSizes.sm,
                        fontWeight: isComposite
                          ? THEME.fontWeights.bold
                          : THEME.fontWeights.medium,
                        fontFamily: THEME.fonts.mono,
                        minWidth: "52px",
                        textAlign: "center",
                      }}
                    >
                      {scores[city]?.[key]?.toFixed(1) ?? "—"}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div
        style={{
          padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
          backgroundColor: THEME.colors.surface,
          borderTop: `1px solid ${THEME.colors.border}`,
          display: "flex",
          gap: THEME.spacing.lg,
          flexWrap: "wrap",
        }}
      >
        {[
          { color: THEME.colors.success, label: "≥ 70 — Strong" },
          { color: THEME.colors.warning, label: "40–69 — Moderate" },
          { color: THEME.colors.danger, label: "< 40 — Weak" },
        ].map(({ color, label }) => (
          <div
            key={label}
            style={{ display: "flex", alignItems: "center", gap: THEME.spacing.xs }}
          >
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: THEME.radius.sm,
                backgroundColor: color,
              }}
            />
            <span
              style={{
                fontSize: THEME.fontSizes.xs,
                color: THEME.colors.textFaint,
                fontFamily: THEME.fonts.body,
              }}
            >
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}