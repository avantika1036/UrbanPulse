import React, { useState } from "react";
import CompareForm from "../components/CompareForm.jsx";
import CityComparisonTable from "../components/CityComparisonTable.jsx";
import RecommendationPanel from "../components/RecommendationPanel.jsx";
import NarrativeBox from "../components/NarrativeBox.jsx";
import { THEME } from "../styles/theme.js";

function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ marginBottom: THEME.spacing.md }}>
      <h2
        style={{
          fontSize: THEME.fontSizes.xl,
          fontWeight: THEME.fontWeights.semibold,
          color: THEME.colors.text,
          fontFamily: THEME.fonts.body,
          margin: 0,
        }}
      >
        {title}
      </h2>
      {subtitle && (
        <p
          style={{
            fontSize: THEME.fontSizes.sm,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            marginTop: "4px",
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

export default function ComparePage() {
  const [result, setResult] = useState(null);

  const handleResult = (data) => setResult(data);

  const comparison = result?.comparison;
  const ml = result?.ml;
  const persona = result?.persona;

  // Reshape comparison.scores (array of CityScoreDetail) into a keyed dict
  const scoresDict = comparison?.scores
    ? Object.fromEntries(comparison.scores.map((s) => [s.city_name, s]))
    : null;

  const narratePayload =
    comparison && scoresDict
      ? {
          persona: persona,
          best_city: comparison.best_city,
          monthly_income: 80000,
          cities_compared: comparison.cities_compared,
          composite_score:
            scoresDict[comparison.best_city]?.adjusted_life_score ?? 0,
          top_positive_dimension: comparison.top_positive?.dimension ?? "",
          top_positive_score: comparison.top_positive?.score ?? 0,
          top_negative_dimension: comparison.top_negative?.dimension ?? "",
          top_negative_score: comparison.top_negative?.score ?? 0,
          has_children: false,
        }
      : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.xxl }}>
      {/* Page header */}
      <div>
        <h1
          style={{
            fontSize: THEME.fontSizes.xxxl,
            fontWeight: THEME.fontWeights.bold,
            color: THEME.colors.text,
            fontFamily: THEME.fonts.body,
            marginBottom: THEME.spacing.sm,
            letterSpacing: "-0.02em",
          }}
        >
          Compare Cities
        </h1>
        <p
          style={{
            fontSize: THEME.fontSizes.md,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
          }}
        >
          Select 2–3 cities and your persona to get a full salary-adjusted
          score breakdown.
        </p>
      </div>

      {/* Form */}
      <section>
        <SectionHeader
          title="Your Profile"
          subtitle="We use this to weight the 7 scoring dimensions correctly for you."
        />
        <CompareForm onResult={handleResult} />
      </section>

      {/* API error notices */}
      {result?.compareError && (
        <div
          style={{
            backgroundColor: `${THEME.colors.danger}15`,
            border: `1px solid ${THEME.colors.danger}44`,
            borderRadius: THEME.radius.md,
            padding: THEME.spacing.md,
            fontSize: THEME.fontSizes.sm,
            color: THEME.colors.danger,
            fontFamily: THEME.fonts.body,
          }}
        >
          Scoring API error: {result.compareError}
        </div>
      )}
      {result?.mlError && (
        <div
          style={{
            backgroundColor: `${THEME.colors.warning}15`,
            border: `1px solid ${THEME.colors.warning}44`,
            borderRadius: THEME.radius.md,
            padding: THEME.spacing.md,
            fontSize: THEME.fontSizes.sm,
            color: THEME.colors.warning,
            fontFamily: THEME.fonts.body,
          }}
        >
          ML recommendation unavailable: {result.mlError}
        </div>
      )}

      {/* Score table */}
      {comparison && scoresDict && (
        <section>
          <SectionHeader
            title="Score Breakdown"
            subtitle="All dimensions normalised 0–100 relative to your selected cities."
          />
          <CityComparisonTable
            scores={scoresDict}
            bestCity={comparison.best_city}
            citiesCompared={comparison.cities_compared}
          />
        </section>
      )}

      {/* Recommendation */}
      {(comparison || ml) && (
        <section>
          <SectionHeader
            title="Recommendation"
            subtitle="Scoring engine result vs ML model prediction."
          />
          <RecommendationPanel
            bestCity={comparison?.best_city}
            comparisonResult={comparison}
            mlResult={ml}
            persona={persona}
          />
        </section>
      )}

      {/* AI Narrative */}
      {result && (
        <section>
          <SectionHeader
            title="AI Analysis"
            subtitle="Google Gemini explains the recommendation in plain English."
          />
          <NarrativeBox
            narratePayload={narratePayload}
            disabled={!narratePayload}
          />
        </section>
      )}
    </div>
  );
}