import React from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCities } from "../api/client.js";
import { THEME, cityColor, primaryButtonStyle, secondaryButtonStyle, cardStyle } from "../styles/theme.js";

const STATS = [
  { value: "6", label: "Cities Covered" },
  { value: "7", label: "Score Dimensions" },
  { value: "Real", label: "Government Data" },
  { value: "AI", label: "Narratives" },
];

function StatBadge({ value, label }) {
  return (
    <div
      style={{
        ...cardStyle(),
        textAlign: "center",
        padding: `${THEME.spacing.lg} ${THEME.spacing.xl}`,
        minWidth: "160px",
      }}
    >
      <div
        style={{
          fontSize: THEME.fontSizes.xxxl,
          fontWeight: THEME.fontWeights.bold,
          color: THEME.colors.accent,
          fontFamily: THEME.fonts.mono,
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: THEME.fontSizes.xs,
          color: THEME.colors.textMuted,
          fontFamily: THEME.fonts.body,
          marginTop: THEME.spacing.xs,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function CityCard({ city }) {
  const [hovered, setHovered] = useState(false);
  const navigate = useNavigate();
  const color = cityColor(city.city_name);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate("/compare")}
      onKeyDown={(e) => e.key === "Enter" && navigate("/compare")}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        ...cardStyle(),
        backgroundColor: hovered ? "rgba(45, 63, 94, 0.85)" : "rgba(30, 41, 59, 0.65)",
        borderColor: hovered ? color : "rgba(255, 255, 255, 0.08)",
        cursor: "pointer",
        transform: hovered ? "translateY(-4px)" : "none",
        boxShadow: hovered ? `0 12px 40px ${color}33` : THEME.shadows.lg,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: THEME.spacing.md,
        }}
      >
        <div>
          <h3
            style={{
              fontSize: THEME.fontSizes.lg,
              fontWeight: THEME.fontWeights.bold,
              color: THEME.colors.text,
              fontFamily: THEME.fonts.body,
              margin: 0,
            }}
          >
            {city.city_name}
          </h3>
          <p
            style={{
              fontSize: THEME.fontSizes.xs,
              color: THEME.colors.textFaint,
              fontFamily: THEME.fonts.body,
              marginTop: "2px",
            }}
          >
            {city.state}
          </p>
        </div>
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: THEME.radius.full,
            backgroundColor: color,
            marginTop: "4px",
            flexShrink: 0,
          }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: THEME.spacing.md, marginTop: THEME.spacing.md }}>
        {[
          { label: "Avg 1BHK Rent", value: `₹${(city.avg_monthly_rent_1bhk / 1000).toFixed(0)}k/mo` },
          { label: "Fresher Salary", value: `₹${(city.avg_salary_fresher / 100000).toFixed(1)}L/yr` },
          { label: "CoL Index", value: city.cost_of_living_index?.toFixed(0) },
          { label: "Avg AQI", value: city.pollution_aqi_avg?.toFixed(0) },
        ].map(({ label, value }) => (
          <div key={label} style={{
            backgroundColor: "rgba(0,0,0,0.2)",
            padding: THEME.spacing.sm,
            borderRadius: THEME.radius.md,
            border: "1px solid rgba(255,255,255,0.03)"
          }}>
            <p
              style={{
                fontSize: THEME.fontSizes.xs,
                color: THEME.colors.textFaint,
                fontFamily: THEME.fonts.body,
                margin: 0,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "4px",
              }}
            >
              {label}
            </p>
            <p
              style={{
                fontSize: THEME.fontSizes.md,
                fontWeight: THEME.fontWeights.semibold,
                color: THEME.colors.text,
                fontFamily: THEME.fonts.mono,
                margin: 0,
              }}
            >
              {value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HeroPage() {
  const navigate = useNavigate();
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCities()
      .then(setCities)
      .catch(() => setCities([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: THEME.spacing.xxl }}>
      {/* Hero Section */}
      <section style={{ textAlign: "center", paddingTop: THEME.spacing.xxl }}>
        <div
          style={{
            display: "inline-block",
            fontSize: THEME.fontSizes.xs,
            fontFamily: THEME.fonts.mono,
            color: THEME.colors.accent,
            backgroundColor: THEME.colors.accentGlow,
            border: `1px solid ${THEME.colors.accent}44`,
            borderRadius: THEME.radius.full,
            padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
            marginBottom: THEME.spacing.xl,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          Relocation Intelligence Platform
        </div>
        <h1
          style={{
            fontSize: "clamp(28px, 5vw, 52px)",
            fontWeight: THEME.fontWeights.bold,
            color: THEME.colors.text,
            fontFamily: THEME.fonts.body,
            lineHeight: THEME.lineHeights.tight,
            marginBottom: THEME.spacing.lg,
            letterSpacing: "-0.02em",
          }}
        >
          Find Your City.{" "}
          <span style={{ color: THEME.colors.accent }}>Backed by Data.</span>
        </h1>
        <p
          style={{
            fontSize: "clamp(14px, 2vw, 18px)",
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            lineHeight: THEME.lineHeights.relaxed,
            maxWidth: "600px",
            margin: "0 auto",
            marginBottom: THEME.spacing.xxl,
          }}
        >
          Compare Mumbai, Bengaluru, Chennai, Pune, Delhi & Hyderabad using
          real government data + AI-powered scoring. Persona-driven.
          Salary-adjusted. Explainable.
        </p>
        <div
          style={{
            display: "flex",
            gap: THEME.spacing.md,
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <button
            onClick={() => navigate("/compare")}
            style={{
              ...primaryButtonStyle(),
              padding: `${THEME.spacing.md} ${THEME.spacing.xxl}`,
              fontSize: THEME.fontSizes.md,
            }}
          >
            Compare Cities
          </button>
          <button
            onClick={() => navigate("/analytics")}
            style={{
              ...secondaryButtonStyle(),
              padding: `${THEME.spacing.md} ${THEME.spacing.xxl}`,
              fontSize: THEME.fontSizes.md,
            }}
          >
            View Analytics
          </button>
        </div>
      </section>

      {/* Stats Row */}
      <section>
        <div
          style={{
            display: "flex",
            gap: THEME.spacing.md,
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          {STATS.map((s) => (
            <StatBadge key={s.label} {...s} />
          ))}
        </div>
      </section>

      {/* City Cards */}
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
          Cities Covered
        </h2>
        {loading ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: THEME.spacing.md,
            }}
          >
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                style={{
                  height: "160px",
                  backgroundColor: THEME.colors.surface,
                  border: `1px solid ${THEME.colors.border}`,
                  borderRadius: THEME.radius.lg,
                  animation: "pulse 1.5s ease-in-out infinite",
                }}
              />
            ))}
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: THEME.spacing.md,
            }}
          >
            {cities.map((city) => (
              <CityCard key={city.city_name} city={city} />
            ))}
          </div>
        )}
      </section>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}