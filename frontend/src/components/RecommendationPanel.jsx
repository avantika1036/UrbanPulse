import { THEME, cityColor, personaColor, scoreColor } from "../styles/theme.js";

const PERSONA_LABELS = {
  early_career: "Early Career",
  family_focused: "Family Focused",
  budget_focused: "Budget Focused",
};

export default function RecommendationPanel({
  bestCity,
  comparisonResult,
  mlResult,
  persona,
}) {
  if (!bestCity && !mlResult) return null;

  const scoringBestCity = comparisonResult?.best_city;
  const mlBestCity = mlResult?.recommended_city;
  const agree = scoringBestCity && mlBestCity && scoringBestCity === mlBestCity;

  const topPos = comparisonResult?.top_positive;
  const topNeg = comparisonResult?.top_negative;
  const recText = comparisonResult?.recommendation_text;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: THEME.spacing.lg,
      }}
    >
      {/* Scoring Engine Result */}
      {scoringBestCity && (
        <div
          style={{
            backgroundColor: THEME.colors.surface,
            border: `1px solid ${THEME.colors.accent}`,
            borderRadius: THEME.radius.lg,
            padding: THEME.spacing.lg,
            boxShadow: THEME.shadows.accent,
          }}
        >
          <p
            style={{
              fontSize: THEME.fontSizes.xs,
              fontWeight: THEME.fontWeights.semibold,
              color: THEME.colors.textMuted,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontFamily: THEME.fonts.body,
              marginBottom: THEME.spacing.md,
            }}
          >
            Scoring Engine Recommendation
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: THEME.spacing.md,
              marginBottom: THEME.spacing.md,
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: THEME.radius.lg,
                backgroundColor: `${cityColor(scoringBestCity)}22`,
                border: `2px solid ${cityColor(scoringBestCity)}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "22px",
                flexShrink: 0,
              }}
            >
              {scoringBestCity[0]}
            </div>
            <div>
              <h3
                style={{
                  fontSize: THEME.fontSizes.xxl,
                  fontWeight: THEME.fontWeights.bold,
                  color: THEME.colors.text,
                  fontFamily: THEME.fonts.body,
                  margin: 0,
                  lineHeight: 1.2,
                }}
              >
                {scoringBestCity}
              </h3>
              <span
                style={{
                  fontSize: THEME.fontSizes.xs,
                  color: personaColor(persona),
                  fontFamily: THEME.fonts.body,
                }}
              >
                Best for {PERSONA_LABELS[persona] || persona}
              </span>
            </div>
          </div>

          {recText && (
            <p
              style={{
                fontSize: THEME.fontSizes.sm,
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.body,
                lineHeight: THEME.lineHeights.relaxed,
                marginBottom: THEME.spacing.md,
              }}
            >
              {recText}
            </p>
          )}

          {(topPos || topNeg) && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: THEME.spacing.sm,
              }}
            >
              {topPos && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    backgroundColor: `${THEME.colors.success}15`,
                    border: `1px solid ${THEME.colors.success}33`,
                    borderRadius: THEME.radius.md,
                    padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                  }}
                >
                  <span
                    style={{
                      fontSize: THEME.fontSizes.xs,
                      color: THEME.colors.success,
                      fontFamily: THEME.fonts.body,
                    }}
                  >
                    ↑ {topPos.dimension}
                  </span>
                  <span
                    style={{
                      fontSize: THEME.fontSizes.sm,
                      fontWeight: THEME.fontWeights.semibold,
                      color: THEME.colors.success,
                      fontFamily: THEME.fonts.mono,
                    }}
                  >
                    {topPos.score?.toFixed(1)}
                  </span>
                </div>
              )}
              {topNeg && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    backgroundColor: `${THEME.colors.danger}15`,
                    border: `1px solid ${THEME.colors.danger}33`,
                    borderRadius: THEME.radius.md,
                    padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                  }}
                >
                  <span
                    style={{
                      fontSize: THEME.fontSizes.xs,
                      color: THEME.colors.danger,
                      fontFamily: THEME.fonts.body,
                    }}
                  >
                    ↓ {topNeg.dimension}
                  </span>
                  <span
                    style={{
                      fontSize: THEME.fontSizes.sm,
                      fontWeight: THEME.fontWeights.semibold,
                      color: THEME.colors.danger,
                      fontFamily: THEME.fonts.mono,
                    }}
                  >
                    {topNeg.score?.toFixed(1)}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ML Recommendation */}
      {mlResult && (
        <div
          style={{
            backgroundColor: THEME.colors.surface,
            border: `1px solid ${THEME.colors.border}`,
            borderRadius: THEME.radius.lg,
            padding: THEME.spacing.lg,
            boxShadow: THEME.shadows.md,
          }}
        >
          <p
            style={{
              fontSize: THEME.fontSizes.xs,
              fontWeight: THEME.fontWeights.semibold,
              color: THEME.colors.textMuted,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontFamily: THEME.fonts.body,
              marginBottom: THEME.spacing.md,
            }}
          >
            ML Model Recommendation
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: THEME.spacing.md,
              marginBottom: THEME.spacing.md,
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: THEME.radius.lg,
                backgroundColor: `${cityColor(mlBestCity)}22`,
                border: `2px solid ${cityColor(mlBestCity)}44`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "22px",
                flexShrink: 0,
              }}
            >
              {mlBestCity?.[0]}
            </div>
            <div>
              <h3
                style={{
                  fontSize: THEME.fontSizes.xxl,
                  fontWeight: THEME.fontWeights.bold,
                  color: THEME.colors.text,
                  fontFamily: THEME.fonts.body,
                  margin: 0,
                  lineHeight: 1.2,
                }}
              >
                {mlBestCity}
              </h3>
              <span
                style={{
                  fontSize: THEME.fontSizes.xs,
                  color: THEME.colors.textMuted,
                  fontFamily: THEME.fonts.mono,
                }}
              >
                {((mlResult.confidence || 0) * 100).toFixed(1)}% confidence
              </span>
            </div>
          </div>

          <div
            style={{
              marginBottom: THEME.spacing.md,
              backgroundColor: THEME.colors.surface2,
              borderRadius: THEME.radius.md,
              padding: `${THEME.spacing.xs} ${THEME.spacing.sm}`,
              display: "flex",
              alignItems: "center",
              gap: THEME.spacing.sm,
            }}
          >
            <div
              style={{
                flex: 1,
                height: "6px",
                backgroundColor: THEME.colors.border,
                borderRadius: THEME.radius.full,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${((mlResult.confidence || 0) * 100).toFixed(0)}%`,
                  backgroundColor: scoreColor((mlResult.confidence || 0) * 100),
                  borderRadius: THEME.radius.full,
                  transition: "width 0.6s ease",
                }}
              />
            </div>
            <span
              style={{
                fontSize: THEME.fontSizes.xs,
                color: THEME.colors.textFaint,
                fontFamily: THEME.fonts.mono,
                whiteSpace: "nowrap",
              }}
            >
              {((mlResult.confidence || 0) * 100).toFixed(1)}%
            </span>
          </div>

          {mlResult.reasoning && (
            <p
              style={{
                fontSize: THEME.fontSizes.sm,
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.body,
                lineHeight: THEME.lineHeights.relaxed,
                marginBottom: THEME.spacing.md,
              }}
            >
              {mlResult.reasoning}
            </p>
          )}

          {agree !== null && scoringBestCity && mlBestCity && (
            <div
              style={{
                fontSize: THEME.fontSizes.xs,
                padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                borderRadius: THEME.radius.md,
                backgroundColor: agree
                  ? `${THEME.colors.success}15`
                  : `${THEME.colors.warning}15`,
                border: `1px solid ${
                  agree ? THEME.colors.success : THEME.colors.warning
                }33`,
                color: agree ? THEME.colors.success : THEME.colors.warning,
                fontFamily: THEME.fonts.body,
              }}
            >
              {agree
                ? "✓ Both models agree on this recommendation"
                : `⚠ Scoring engine favours ${scoringBestCity}`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}