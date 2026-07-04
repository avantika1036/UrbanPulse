import { useEffect, useState } from "react";
import { getAnalyticsOverview, getMonthlyTrends } from "../api/client.js";
import { THEME, scoreColor, cityColor } from "../styles/theme.js";
import PersonaToggle from "../components/PersonaToggle.jsx";
import TrendChart from "../components/TrendChart.jsx";

const DIMENSION_KEYS = [
  { key: "avg_income_score", label: "Income" },
  { key: "avg_affordability_score", label: "Affordability" },
  { key: "avg_healthcare_score", label: "Healthcare" },
  { key: "avg_environment_score", label: "Environment" },
  { key: "avg_career_growth_score", label: "Career Growth" },
  { key: "avg_family_fit_score", label: "Family Fit" },
  { key: "avg_adjusted_life_score", label: "Overall" },
];

function RankingTable({ rankings, persona }) {
  if (!rankings || rankings.length === 0) return null;

  const personaKey = `scores_by_persona.${persona}`;

  return (
    <div
      style={{
        overflowX: "auto",
        borderRadius: THEME.radius.lg,
        border: `1px solid ${THEME.colors.border}`,
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontFamily: THEME.fonts.body,
          minWidth: "700px",
        }}
      >
        <thead>
          <tr style={{ backgroundColor: THEME.colors.surface2 }}>
            {["Rank", "City", "Income", "Afford.", "Health", "Environ.", "Career", "Family", "Overall"].map(
              (h) => (
                <th
                  key={h}
                  style={{
                    padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                    textAlign: h === "Rank" || h === "City" ? "left" : "center",
                    color: THEME.colors.textMuted,
                    fontSize: THEME.fontSizes.xs,
                    fontWeight: THEME.fontWeights.semibold,
                    textTransform: "uppercase",
                    letterSpacing: "0.07em",
                    borderBottom: `1px solid ${THEME.colors.border}`,
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {rankings.map((city, idx) => {
            const personaScores = city.scores_by_persona?.[persona] || {};
            const color = cityColor(city.city_name);
            return (
              <tr
                key={city.city_name}
                style={{
                  backgroundColor:
                    idx % 2 === 0 ? THEME.colors.surface : `${THEME.colors.surface}cc`,
                }}
              >
                <td
                  style={{
                    padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                    borderBottom: `1px solid ${THEME.colors.border}`,
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: "24px",
                      height: "24px",
                      borderRadius: THEME.radius.full,
                      backgroundColor:
                        city.overall_rank === 1
                          ? `${THEME.colors.success}22`
                          : THEME.colors.surface2,
                      color:
                        city.overall_rank === 1
                          ? THEME.colors.success
                          : THEME.colors.textMuted,
                      fontSize: THEME.fontSizes.xs,
                      fontWeight: THEME.fontWeights.bold,
                      fontFamily: THEME.fonts.mono,
                    }}
                  >
                    {city.overall_rank}
                  </span>
                </td>
                <td
                  style={{
                    padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                    borderBottom: `1px solid ${THEME.colors.border}`,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: THEME.spacing.sm }}>
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
                        fontSize: THEME.fontSizes.sm,
                        fontWeight: THEME.fontWeights.semibold,
                        color: THEME.colors.text,
                      }}
                    >
                      {city.city_name}
                    </span>
                  </div>
                </td>
                {[
                  "income_score",
                  "affordability_score",
                  "healthcare_score",
                  "environment_score",
                  "career_growth_score",
                  "family_fit_score",
                  "adjusted_life_score",
                ].map((key) => {
                  const val = personaScores[key];
                  const sc = scoreColor(val ?? 0);
                  return (
                    <td
                      key={key}
                      style={{
                        padding: `${THEME.spacing.sm} ${THEME.spacing.md}`,
                        textAlign: "center",
                        borderBottom: `1px solid ${THEME.colors.border}`,
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          minWidth: "44px",
                          padding: `1px ${THEME.spacing.sm}`,
                          borderRadius: THEME.radius.sm,
                          backgroundColor: `${sc}22`,
                          color: sc,
                          fontSize: THEME.fontSizes.xs,
                          fontWeight: THEME.fontWeights.semibold,
                          fontFamily: THEME.fonts.mono,
                          textAlign: "center",
                        }}
                      >
                        {val != null ? val.toFixed(1) : "—"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const TREND_CITIES = ["Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"];

export default function AnalyticsPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [persona, setPersona] = useState("early_career");
  const [trendData, setTrendData] = useState([]);
  const [trendLoading, setTrendLoading] = useState(true);

  useEffect(() => {
    getAnalyticsOverview()
      .then(setOverview)
      .catch((e) => setError(e.message || "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setTrendLoading(true);
    Promise.all(TREND_CITIES.map((city) => getMonthlyTrends(city).then((res) => ({ city, trends: res.trends || [] }))))
      .then((results) => {
        const byMonth = {};
        results.forEach(({ city, trends }) => {
          trends.forEach((row) => {
            const ym = row.year_month;
            if (!byMonth[ym]) byMonth[ym] = { year_month: ym };
            byMonth[ym][`aqi_${city}`] = row.avg_aqi;
            byMonth[ym][`rent_${city}`] = row.avg_rent_1bhk;
          });
        });
        setTrendData(Object.values(byMonth).sort((a, b) => a.year_month.localeCompare(b.year_month)));
      })
      .catch(() => setTrendData([]))
      .finally(() => setTrendLoading(false));
  }, []);

  const aqiLines = TREND_CITIES.map((city) => ({
    key: `aqi_${city}`,
    color: cityColor(city),
    label: city,
  }));

  const rentLines = TREND_CITIES.map((city) => ({
    key: `rent_${city}`,
    color: cityColor(city),
    label: city,
  }));

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "40vh",
          color: THEME.colors.textMuted,
          fontSize: THEME.fontSizes.md,
          fontFamily: THEME.fonts.body,
        }}
      >
        Loading analytics...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          backgroundColor: `${THEME.colors.danger}15`,
          border: `1px solid ${THEME.colors.danger}44`,
          borderRadius: THEME.radius.lg,
          padding: THEME.spacing.xl,
          color: THEME.colors.danger,
          fontFamily: THEME.fonts.body,
        }}
      >
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.xxl }}>
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
          Analytics
        </h1>
        <p
          style={{
            fontSize: THEME.fontSizes.md,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
          }}
        >
          City rankings, score breakdowns, and 24-month trends across all
          personas.
        </p>
      </div>

      {/* Persona toggle */}
      <PersonaToggle value={persona} onChange={setPersona} />

      {/* Rankings */}
      <section>
        <h2
          style={{
            fontSize: THEME.fontSizes.xl,
            fontWeight: THEME.fontWeights.semibold,
            color: THEME.colors.text,
            fontFamily: THEME.fonts.body,
            marginBottom: THEME.spacing.md,
          }}
        >
          City Rankings by Persona
        </h2>
        <RankingTable
          rankings={overview?.city_rankings || []}
          persona={persona}
        />
      </section>

      {/* Trend Charts */}
      <section>
        <h2
          style={{
            fontSize: THEME.fontSizes.xl,
            fontWeight: THEME.fontWeights.semibold,
            color: THEME.colors.text,
            fontFamily: THEME.fonts.body,
            marginBottom: THEME.spacing.lg,
          }}
        >
          24-Month Trends
        </h2>
        {trendLoading ? (
          <p
            style={{
              color: THEME.colors.textMuted,
              fontFamily: THEME.fonts.body,
              fontSize: THEME.fontSizes.sm,
            }}
          >
            Loading trend data...
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.lg }}>
            <TrendChart
              data={trendData}
              xKey="year_month"
              lines={aqiLines}
              title="Average AQI by City (Jan 2023 – Dec 2024)"
              yAxisLabel="AQI"
              height={260}
            />
            <TrendChart
              data={trendData}
              xKey="year_month"
              lines={rentLines}
              title="Average 1BHK Rent (₹/month)"
              yAxisLabel="₹/mo"
              yTickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              height={260}
            />
          </div>
        )}
      </section>
    </div>
  );
}