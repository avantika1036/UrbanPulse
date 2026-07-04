import React, { useState } from "react";
import { compareCities, getBestCity } from "../api/client.js";
import { THEME, inputStyle, primaryButtonStyle } from "../styles/theme.js";
import PersonaToggle from "./PersonaToggle.jsx";

const CITIES = ["Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"];

const PRIORITIES = [
  "affordability", "healthcare", "job_market", "livability",
  "infrastructure", "growth", "schools", "pollution", "safety",
];

const DEFAULT_FORM = {
  persona: "early_career",
  monthlyIncome: "",
  yearsExperience: "",
  hasChildren: false,
  selectedCities: [],
  priority1: "job_market",
  priority2: "affordability",
  priority3: "livability",
};

export default function CompareForm({ onResult }) {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const setField = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const toggleCity = (city) => {
    setForm((f) => {
      const sel = f.selectedCities;
      if (sel.includes(city)) return { ...f, selectedCities: sel.filter((c) => c !== city) };
      if (sel.length >= 3) return f;
      return { ...f, selectedCities: [...sel, city] };
    });
  };

  const isValid =
    form.selectedCities.length >= 2 &&
    form.selectedCities.length <= 3 &&
    form.monthlyIncome &&
    parseFloat(form.monthlyIncome) > 0 &&
    form.yearsExperience !== "" &&
    parseInt(form.yearsExperience, 10) >= 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValid || loading) return;
    setLoading(true);
    setError(null);

    const comparePayload = {
      cities: form.selectedCities,
      persona: form.persona,
      user_monthly_income: parseFloat(form.monthlyIncome),
      years_experience: parseInt(form.yearsExperience, 10),
      has_children: form.hasChildren,
    };

    const mlPayload = {
      age: 28,
      current_city: form.selectedCities[0],
      target_cities: form.selectedCities.slice(1),
      persona: form.persona,
      monthly_income: parseFloat(form.monthlyIncome),
      dependents_count: form.hasChildren ? 1 : 0,
      priority_1: form.priority1,
      priority_2: form.priority2,
      priority_3: form.priority3,
      has_children: form.hasChildren,
      years_experience: parseFloat(form.yearsExperience),
    };

    try {
      const [compareRes, mlRes] = await Promise.allSettled([
        compareCities(comparePayload),
        getBestCity(mlPayload),
      ]);

      onResult({
        comparison: compareRes.status === "fulfilled" ? compareRes.value : null,
        ml: mlRes.status === "fulfilled" ? mlRes.value : null,
        persona: form.persona,
        compareError: compareRes.status === "rejected" ? compareRes.reason?.message : null,
        mlError: mlRes.status === "rejected" ? mlRes.reason?.message : null,
      });

      if (compareRes.status === "rejected" && mlRes.status === "rejected") {
        setError("Both API calls failed. Is the backend running?");
      }
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  };

  const labelStyle = {
    fontSize: THEME.fontSizes.xs,
    fontWeight: THEME.fontWeights.semibold,
    color: THEME.colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontFamily: THEME.fonts.body,
    display: "block",
    marginBottom: THEME.spacing.sm,
  };

  const sectionStyle = {
    display: "flex",
    flexDirection: "column",
    gap: THEME.spacing.sm,
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        backgroundColor: THEME.colors.surface,
        border: `1px solid ${THEME.colors.border}`,
        borderRadius: THEME.radius.xl,
        padding: THEME.spacing.xl,
        boxShadow: THEME.shadows.md,
        display: "flex",
        flexDirection: "column",
        gap: THEME.spacing.xl,
      }}
      aria-label="City comparison form"
    >
      {/* City selection */}
      <div style={sectionStyle}>
        <label style={labelStyle}>
          Select Cities{" "}
          <span style={{ color: THEME.colors.textFaint, fontWeight: 400 }}>
            (2–3 cities)
          </span>
        </label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: THEME.spacing.sm }}>
          {CITIES.map((city) => {
            const sel = form.selectedCities.includes(city);
            const atMax = form.selectedCities.length >= 3 && !sel;
            return (
              <button
                key={city}
                type="button"
                disabled={atMax}
                onClick={() => toggleCity(city)}
                aria-pressed={sel}
                style={{
                  padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                  borderRadius: THEME.radius.md,
                  border: `1px solid ${sel ? THEME.colors.accent : THEME.colors.border}`,
                  backgroundColor: sel
                    ? THEME.colors.accentGlow
                    : THEME.colors.surface2,
                  color: sel ? THEME.colors.accent : THEME.colors.textMuted,
                  fontSize: THEME.fontSizes.sm,
                  fontWeight: sel
                    ? THEME.fontWeights.semibold
                    : THEME.fontWeights.regular,
                  fontFamily: THEME.fonts.body,
                  cursor: atMax ? "not-allowed" : "pointer",
                  opacity: atMax ? 0.4 : 1,
                  transition: THEME.transitions.base,
                }}
              >
                {city}
              </button>
            );
          })}
        </div>
        {form.selectedCities.length > 0 && (
          <p
            style={{
              fontSize: THEME.fontSizes.xs,
              color: THEME.colors.textFaint,
              fontFamily: THEME.fonts.body,
            }}
          >
            Selected: {form.selectedCities.join(" · ")}
          </p>
        )}
      </div>

      {/* Persona */}
      <div style={sectionStyle}>
        <PersonaToggle
          value={form.persona}
          onChange={(v) => setField("persona", v)}
          disabled={loading}
        />
      </div>

      {/* Income + Experience */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: THEME.spacing.lg,
        }}
      >
        <div style={sectionStyle}>
          <label htmlFor="income" style={labelStyle}>
            Monthly Income (₹)
          </label>
          <input
            id="income"
            type="number"
            min="1"
            placeholder="e.g. 80000"
            value={form.monthlyIncome}
            onChange={(e) => setField("monthlyIncome", e.target.value)}
            disabled={loading}
            style={inputStyle()}
          />
        </div>
        <div style={sectionStyle}>
          <label htmlFor="exp" style={labelStyle}>
            Years of Experience
          </label>
          <input
            id="exp"
            type="number"
            min="0"
            max="50"
            placeholder="e.g. 3"
            value={form.yearsExperience}
            onChange={(e) => setField("yearsExperience", e.target.value)}
            disabled={loading}
            style={inputStyle()}
          />
        </div>
      </div>

      {/* Priorities */}
      <div style={sectionStyle}>
        <label style={labelStyle}>Your Top 3 Priorities</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: THEME.spacing.sm,
          }}
        >
          {["priority1", "priority2", "priority3"].map((key, idx) => (
            <div key={key}>
              <label
                htmlFor={key}
                style={{
                  ...labelStyle,
                  fontSize: "10px",
                  marginBottom: "4px",
                }}
              >
                Priority {idx + 1}
              </label>
              <select
                id={key}
                value={form[key]}
                onChange={(e) => setField(key, e.target.value)}
                disabled={loading}
                style={{ ...inputStyle(), appearance: "none" }}
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Has children */}
      <div style={{ display: "flex", alignItems: "center", gap: THEME.spacing.md }}>
        <input
          id="hasChildren"
          type="checkbox"
          checked={form.hasChildren}
          onChange={(e) => setField("hasChildren", e.target.checked)}
          disabled={loading}
          style={{
            width: "16px",
            height: "16px",
            accentColor: THEME.colors.accent,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        />
        <label
          htmlFor="hasChildren"
          style={{
            fontSize: THEME.fontSizes.sm,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          I have children (applies family fit bonus)
        </label>
      </div>

      {error && (
        <p
          style={{
            fontSize: THEME.fontSizes.sm,
            color: THEME.colors.danger,
            fontFamily: THEME.fonts.body,
            backgroundColor: `${THEME.colors.danger}15`,
            border: `1px solid ${THEME.colors.danger}33`,
            borderRadius: THEME.radius.md,
            padding: THEME.spacing.md,
          }}
        >
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!isValid || loading}
        style={{
          ...primaryButtonStyle(!isValid || loading),
          padding: `${THEME.spacing.md} ${THEME.spacing.xl}`,
          fontSize: THEME.fontSizes.md,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: THEME.spacing.sm,
          alignSelf: "flex-start",
        }}
      >
        {loading && (
          <span
            style={{
              display: "inline-block",
              width: "14px",
              height: "14px",
              border: `2px solid ${THEME.colors.accentLight}`,
              borderTopColor: THEME.colors.white,
              borderRadius: THEME.radius.full,
              animation: "spin 0.8s linear infinite",
            }}
          />
        )}
        {loading ? "Comparing..." : "Compare Cities"}
      </button>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </form>
  );
}