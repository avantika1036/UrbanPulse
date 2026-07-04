import { THEME, scoreColor, cityColor } from "../styles/theme.js";

const DIMENSION_LABELS = {
  income_score: "Income vs CoL",
  affordability_score: "Affordability",
  healthcare_score: "Healthcare",
  environment_score: "Environment",
  career_growth_score: "Career Growth",
  family_fit_score: "Family Fit",
  adjusted_life_score: "Overall Score",
};

function ScoreBar({ score, color }) {
  return (
    <div
      style={{
        width: "100%",
        height: "4px",
        backgroundColor: THEME.colors.border,
        borderRadius: THEME.radius.full,
        overflow: "hidden",
      }}
      role="progressbar"
      aria-valuenow={score}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        style={{
          height: "100%",
          width: `${Math.max(0, Math.min(100, score))}%`,
          backgroundColor: color,
          borderRadius: THEME.radius.full,
          transition: "width 0.6s ease",
        }}
      />
    </div>
  );
}

export default function ScoreCard({ cityName, scores, isHighlighted = false }) {
  if (!scores) return null;

  const overallScore = scores.adjusted_life_score;
  const color = cityColor(cityName);

  const dimensions = [
    "income_score",
    "affordability_score",
    "healthcare_score",
    "environment_score",
    "career_growth_score",
    "family_fit_score",
  ];

  return (
    <div
      style={{
        backgroundColor: THEME.colors.surface,
        border: `1px solid ${isHighlighted ? THEME.colors.accent : THEME.colors.border}`,
        borderRadius: THEME.radius.lg,
        padding: THEME.spacing.lg,
        boxShadow: isHighlighted ? THEME.shadows.accent : THEME.shadows.md,
        position: "relative",
        transition: THEME.transitions.base,
      }}
    >
      {isHighlighted && (
        <div
          style={{
            position: "absolute",
            top: "-1px",
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: THEME.colors.accent,
            color: THEME.colors.white,
            fontSize: THEME.fontSizes.xs,
            fontWeight: THEME.fontWeights.semibold,
            padding: `2px ${THEME.spacing.sm}`,
            borderRadius: `0 0 ${THEME.radius.sm} ${THEME.radius.sm}`,
            fontFamily: THEME.fonts.body,
            whiteSpace: "nowrap",
          }}
        >
          TOP PICK
        </div>
      )}

      {/* City header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: THEME.spacing.lg,
          paddingTop: isHighlighted ? THEME.spacing.sm : 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: THEME.spacing.sm }}>
          <div
            style={{
              width: "10px",
              height: "10px",
              borderRadius: THEME.radius.full,
              backgroundColor: color,
              flexShrink: 0,
            }}
          />
          <h3
            style={{
              fontSize: THEME.fontSizes.lg,
              fontWeight: THEME.fontWeights.bold,
              color: THEME.colors.text,
              fontFamily: THEME.fonts.body,
              margin: 0,
            }}
          >
            {cityName}
          </h3>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: THEME.fontSizes.xxl,
              fontWeight: THEME.fontWeights.bold,
              color: scoreColor(overallScore),
              fontFamily: THEME.fonts.mono,
              lineHeight: 1,
            }}
          >
            {overallScore?.toFixed(1)}
          </div>
          <div
            style={{
              fontSize: THEME.fontSizes.xs,
              color: THEME.colors.textFaint,
              fontFamily: THEME.fonts.body,
            }}
          >
            / 100
          </div>
        </div>
      </div>

      {/* Dimension bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.md }}>
        {dimensions.map((dim) => {
          const val = scores[dim];
          if (val === undefined) return null;
          const sc = scoreColor(val);
          return (
            <div key={dim}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "4px",
                }}
              >
                <span
                  style={{
                    fontSize: THEME.fontSizes.xs,
                    color: THEME.colors.textMuted,
                    fontFamily: THEME.fonts.body,
                  }}
                >
                  {DIMENSION_LABELS[dim]}
                </span>
                <span
                  style={{
                    fontSize: THEME.fontSizes.xs,
                    fontWeight: THEME.fontWeights.semibold,
                    color: sc,
                    fontFamily: THEME.fonts.mono,
                  }}
                >
                  {val?.toFixed(1)}
                </span>
              </div>
              <ScoreBar score={val} color={sc} />
            </div>
          );
        })}
      </div>
    </div>
  );
}