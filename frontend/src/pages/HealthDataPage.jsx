import { useState } from "react";
import { getCityHealth } from "../api/client.js";
import { THEME, cityColor } from "../styles/theme.js";
import TrendChart from "../components/TrendChart.jsx";

const CITIES = ["Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"];

const HOSPITAL_REAL_DATA_CITIES = new Set(["Mumbai", "Bengaluru", "Chennai"]);
const BIRTHS_DEATHS_REAL_CITIES = new Set(["Bengaluru", "Chennai", "Delhi", "Pune"]);

function KpiCard({ label, value, subLabel, isReal = true }) {
  return (
    <div
      style={{
        backgroundColor: THEME.colors.surface,
        border: `1px solid ${isReal ? THEME.colors.border : THEME.colors.warning + "55"}`,
        borderRadius: THEME.radius.lg,
        padding: THEME.spacing.lg,
        boxShadow: THEME.shadows.sm,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: THEME.spacing.sm,
        }}
      >
        <p
          style={{
            fontSize: THEME.fontSizes.xs,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            margin: 0,
          }}
        >
          {label}
        </p>
        <span
          style={{
            fontSize: "10px",
            padding: `2px ${THEME.spacing.xs}`,
            borderRadius: THEME.radius.sm,
            backgroundColor: isReal
              ? `${THEME.colors.success}22`
              : `${THEME.colors.warning}22`,
            color: isReal ? THEME.colors.success : THEME.colors.warning,
            fontFamily: THEME.fonts.body,
            fontWeight: THEME.fontWeights.semibold,
            whiteSpace: "nowrap",
          }}
        >
          {isReal ? "Real" : "Estimated"}
        </span>
      </div>
      <p
        style={{
          fontSize: THEME.fontSizes.xxl,
          fontWeight: THEME.fontWeights.bold,
          color: THEME.colors.text,
          fontFamily: THEME.fonts.mono,
          margin: 0,
          lineHeight: 1,
        }}
      >
        {value}
      </p>
      {subLabel && (
        <p
          style={{
            fontSize: THEME.fontSizes.xs,
            color: THEME.colors.textFaint,
            fontFamily: THEME.fonts.body,
            marginTop: THEME.spacing.xs,
            margin: 0,
            marginTop: "6px",
          }}
        >
          {subLabel}
        </p>
      )}
    </div>
  );
}

export default function HealthDataPage() {
  const [selectedCity, setSelectedCity] = useState("Bengaluru");
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasFetched, setHasFetched] = useState(false);

  const fetchHealth = async (city) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCityHealth(city);
      setHealthData(data);
      setHasFetched(true);
    } catch (e) {
      setError(e.message || "Failed to load health data.");
    } finally {
      setLoading(false);
    }
  };

  const handleCityChange = (city) => {
    setSelectedCity(city);
    fetchHealth(city);
  };

  const hasRealBD = BIRTHS_DEATHS_REAL_CITIES.has(selectedCity);
  const hasRealHospital = HOSPITAL_REAL_DATA_CITIES.has(selectedCity);

  const annualRecords = healthData?.annual_health_data?.records || [];
  const hospitalCounts = healthData?.hospital_data?.counts;

  const chartData = [...annualRecords]
    .sort((a, b) => a.year - b.year)
    .map((r) => ({
      year: String(r.year),
      total_births: r.total_births,
      total_deaths: r.total_deaths,
      crude_death_rate: r.crude_death_rate_per_1000
        ? parseFloat(r.crude_death_rate_per_1000.toFixed(2))
        : null,
    }));

  const cityCol = cityColor(selectedCity);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.xxl }}>
      {/* Header */}
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
          Real Health Data
        </h1>
        <p
          style={{
            fontSize: THEME.fontSizes.md,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
          }}
        >
          Births, deaths, and hospital infrastructure from actual government
          records.
        </p>
      </div>

      {/* Source attribution banner */}
      <div
        style={{
          backgroundColor: `${THEME.colors.accent}15`,
          border: `1px solid ${THEME.colors.accent}44`,
          borderRadius: THEME.radius.md,
          padding: `${THEME.spacing.sm} ${THEME.spacing.lg}`,
          fontSize: THEME.fontSizes.xs,
          color: THEME.colors.textMuted,
          fontFamily: THEME.fonts.body,
          lineHeight: THEME.lineHeights.relaxed,
        }}
      >
        <strong style={{ color: THEME.colors.accent }}>Real Data Sources: </strong>
        Bengaluru BBMP (Annual B&D 2001–2024, 32 Health Centres) | Mumbai BMC
        (288 ward-level hospitals with bed counts) | Chennai GCC (16 UCHCs,
        Annual B&D 2018–2025) | Pune PMC (Annual B&D 1975–2018, KRA Disease
        Report 2017) | Delhi State Health Dept (Annual B&D 2017–2024).
        <strong style={{ color: THEME.colors.warning }}> Hyderabad: all metrics are synthetic estimates.</strong>
      </div>

      {/* City selector */}
      <section>
        <p
          style={{
            fontSize: THEME.fontSizes.xs,
            fontWeight: THEME.fontWeights.semibold,
            color: THEME.colors.textMuted,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontFamily: THEME.fonts.body,
            marginBottom: THEME.spacing.sm,
          }}
        >
          Select City
        </p>
        <div style={{ display: "flex", gap: THEME.spacing.sm, flexWrap: "wrap" }}>
          {CITIES.map((city) => {
            const isActive = city === selectedCity;
            const col = cityColor(city);
            const hasReal = BIRTHS_DEATHS_REAL_CITIES.has(city) || HOSPITAL_REAL_DATA_CITIES.has(city);
            return (
              <button
                key={city}
                onClick={() => handleCityChange(city)}
                style={{
                  padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                  borderRadius: THEME.radius.md,
                  border: `1px solid ${isActive ? col : THEME.colors.border}`,
                  backgroundColor: isActive ? `${col}22` : THEME.colors.surface,
                  color: isActive ? col : THEME.colors.textMuted,
                  fontSize: THEME.fontSizes.sm,
                  fontWeight: isActive ? THEME.fontWeights.semibold : THEME.fontWeights.regular,
                  fontFamily: THEME.fonts.body,
                  cursor: "pointer",
                  transition: THEME.transitions.base,
                  display: "flex",
                  alignItems: "center",
                  gap: THEME.spacing.xs,
                }}
              >
                {city}
                {!hasReal && (
                  <span
                    style={{
                      fontSize: "10px",
                      color: THEME.colors.warning,
                      fontFamily: THEME.fonts.body,
                    }}
                  >
                    ~
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <p
          style={{
            fontSize: "10px",
            color: THEME.colors.textFaint,
            fontFamily: THEME.fonts.body,
            marginTop: THEME.spacing.xs,
          }}
        >
          ~ = Estimated data only
        </p>
      </section>

      {loading && (
        <p
          style={{
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            fontSize: THEME.fontSizes.sm,
          }}
        >
          Loading health data for {selectedCity}...
        </p>
      )}

      {error && (
        <div
          style={{
            backgroundColor: `${THEME.colors.danger}15`,
            border: `1px solid ${THEME.colors.danger}44`,
            borderRadius: THEME.radius.md,
            padding: THEME.spacing.md,
            color: THEME.colors.danger,
            fontSize: THEME.fontSizes.sm,
            fontFamily: THEME.fonts.body,
          }}
        >
          {error}
        </div>
      )}

      {hasFetched && !loading && healthData && (
        <>
          {/* Hospital KPI cards */}
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
              Healthcare Infrastructure — {selectedCity}
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                gap: THEME.spacing.md,
              }}
            >
              {hospitalCounts ? (
                <>
                  <KpiCard
                    label="Total Facilities"
                    value={hospitalCounts.total_facilities?.toLocaleString("en-IN")}
                    subLabel="Hospitals & health centres"
                    isReal={hasRealHospital}
                  />
                  <KpiCard
                    label="Total Beds"
                    value={
                      hospitalCounts.has_bed_data
                        ? hospitalCounts.total_beds?.toLocaleString("en-IN")
                        : "N/A"
                    }
                    subLabel={hospitalCounts.has_bed_data ? "Recorded beds" : "Bed data not available"}
                    isReal={hospitalCounts.has_bed_data}
                  />
                  <KpiCard
                    label="Public Facilities"
                    value={hospitalCounts.public_count?.toLocaleString("en-IN")}
                    subLabel="Govt / Municipal / BMC"
                    isReal={hasRealHospital}
                  />
                  <KpiCard
                    label="Private Facilities"
                    value={hospitalCounts.private_count?.toLocaleString("en-IN")}
                    subLabel="Private & Trust hospitals"
                    isReal={hasRealHospital}
                  />
                  <KpiCard
                    label="Beds per Lakh Pop."
                    value={hospitalCounts.hospital_beds_per_lakh?.toFixed(1)}
                    subLabel="Per 1,00,000 population"
                    isReal={hospitalCounts.has_bed_data}
                  />
                  <KpiCard
                    label="Centres per Lakh"
                    value={hospitalCounts.health_centres_per_lakh?.toFixed(2)}
                    subLabel="Health centres per lakh"
                    isReal={hasRealHospital}
                  />
                </>
              ) : (
                <div
                  style={{
                    gridColumn: "1 / -1",
                    backgroundColor: `${THEME.colors.warning}15`,
                    border: `1px solid ${THEME.colors.warning}44`,
                    borderRadius: THEME.radius.md,
                    padding: THEME.spacing.lg,
                    color: THEME.colors.warning,
                    fontSize: THEME.fontSizes.sm,
                    fontFamily: THEME.fonts.body,
                  }}
                >
                  No real hospital facility data available for {selectedCity}. Bed density and facility
                  counts shown on the Compare and Analytics pages are synthetic estimates.
                </div>
              )}
            </div>
          </section>

          {/* Birth/Death trend chart */}
          <section>
            <h2
              style={{
                fontSize: THEME.fontSizes.xl,
                fontWeight: THEME.fontWeights.semibold,
                color: THEME.colors.text,
                fontFamily: THEME.fonts.body,
                marginBottom: THEME.spacing.sm,
              }}
            >
              Annual Births & Deaths
            </h2>
            {!hasRealBD && (
              <div
                style={{
                  backgroundColor: `${THEME.colors.warning}15`,
                  border: `1px solid ${THEME.colors.warning}44`,
                  borderRadius: THEME.radius.md,
                  padding: THEME.spacing.md,
                  marginBottom: THEME.spacing.md,
                  color: THEME.colors.warning,
                  fontSize: THEME.fontSizes.sm,
                  fontFamily: THEME.fonts.body,
                }}
              >
                No real births/deaths data for {selectedCity}. The charts below would show synthetic estimates.
              </div>
            )}
            {chartData.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.lg }}>
                <TrendChart
                  data={chartData}
                  xKey="year"
                  lines={[
                    { key: "total_births", color: THEME.colors.success, label: "Total Births" },
                    { key: "total_deaths", color: THEME.colors.danger, label: "Total Deaths" },
                  ]}
                  title={`Births vs Deaths — ${selectedCity} (Real government data)`}
                  height={260}
                  yTickFormatter={(v) => v != null ? `${(v / 1000).toFixed(0)}k` : ""}
                />
                <TrendChart
                  data={chartData.filter((r) => r.crude_death_rate != null)}
                  xKey="year"
                  lines={[
                    { key: "crude_death_rate", color: cityCol, label: "Crude Death Rate" },
                  ]}
                  title="Crude Death Rate per 1,000 Population"
                  yAxisLabel="per 1k"
                  height={220}
                />
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: THEME.colors.surface,
                  border: `1px solid ${THEME.colors.border}`,
                  borderRadius: THEME.radius.lg,
                  padding: THEME.spacing.xl,
                  textAlign: "center",
                  color: THEME.colors.textFaint,
                  fontSize: THEME.fontSizes.sm,
                  fontFamily: THEME.fonts.body,
                }}
              >
                No annual health records available for {selectedCity}. Run{" "}
                <code style={{ fontFamily: THEME.fonts.mono }}>
                  scripts/load_database.py
                </code>{" "}
                to populate data.
              </div>
            )}
          </section>
        </>
      )}

      {!hasFetched && !loading && (
        <div
          style={{
            backgroundColor: THEME.colors.surface,
            border: `1px solid ${THEME.colors.border}`,
            borderRadius: THEME.radius.lg,
            padding: THEME.spacing.xxl,
            textAlign: "center",
            color: THEME.colors.textFaint,
            fontSize: THEME.fontSizes.md,
            fontFamily: THEME.fonts.body,
          }}
        >
          Select a city above to load health data.
        </div>
      )}
    </div>
  );
}