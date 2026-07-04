/**
 * client.js
 *
 * Axios instance and typed API helper functions for the UrbanPulse
 * FastAPI backend.
 *
 * Base URL is read from VITE_API_URL (set in frontend/.env).
 * Falls back to http://localhost:8000 for local development.
 *
 * All functions return the response data directly (not the axios wrapper),
 * so callers can do:
 *   const cities = await getCities();
 * rather than:
 *   const { data: cities } = await getCities();
 */

import axios from "axios";

const BASE_URL =
  typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL
    ? import.meta.env.VITE_API_URL
    : "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ── Request interceptor — adds request timestamp for performance logging ──
api.interceptors.request.use(
  (config) => {
    config.metadata = { startTime: Date.now() };
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor — unwraps data, logs timing, normalises errors ──
api.interceptors.response.use(
  (response) => {
    const duration = Date.now() - (response.config.metadata?.startTime ?? 0);
    if (import.meta.env?.DEV) {
      console.debug(
        `[api] ${response.config.method?.toUpperCase()} ${response.config.url} ` +
          `→ ${response.status} (${duration}ms)`
      );
    }
    return response.data;
  },
  (error) => {
    const status = error.response?.status ?? "NETWORK";
    const isNetworkError = !error.response && !!error.request;
    const detail =
      (isNetworkError
        ? `Cannot reach API at ${BASE_URL}. Start backend server on port 8000 or set VITE_API_URL.`
        : null) ||
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unknown error occurred";

    const normalised = {
      status,
      message: typeof detail === "string" ? detail : JSON.stringify(detail),
      raw: error,
    };

    if (import.meta.env?.DEV) {
      console.error(
        `[api] Error ${status}: ${normalised.message}`,
        error.config?.url
      );
    }

    return Promise.reject(normalised);
  }
);

// ═══════════════════════════════════════════════════════════════════════════
// CITY ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * GET /cities/
 * Returns the list of all 6 cities with key stats.
 * @returns {Promise<Array>}
 */
export async function getCities() {
  return api.get("/cities/");
}

/**
 * GET /cities/{name}
 * Full city profile with scores for all 3 personas.
 * @param {string} name - City name e.g. "Bengaluru"
 * @returns {Promise<Object>}
 */
export async function getCity(name) {
  return api.get(`/cities/${encodeURIComponent(name)}`);
}

/**
 * GET /cities/{name}/monthly-trends
 * Last 12 months of time-series metrics for a city.
 * @param {string} name
 * @returns {Promise<Object>}
 */
export async function getMonthlyTrends(name) {
  return api.get(`/cities/${encodeURIComponent(name)}/monthly-trends`);
}

/**
 * GET /cities/{name}/health
 * Real births/deaths and hospital data for a city.
 * @param {string} name
 * @returns {Promise<Object>}
 */
export async function getCityHealth(name) {
  return api.get(`/cities/${encodeURIComponent(name)}/health`);
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPARE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * POST /compare/
 * Compare 2-3 cities and return full scoring breakdown.
 * @param {{ cities: string[], persona: string, user_monthly_income: number, years_experience: number, has_children: boolean }} payload
 * @returns {Promise<Object>} ComparisonTableResponse
 */
export async function compareCities(payload) {
  return api.post("/compare/", payload);
}

/**
 * POST /compare/salary-equivalence
 * Compute the salary required in target_city for equivalent purchasing power.
 * @param {{ source_city: string, target_city: string, current_salary: number, persona: string }} payload
 * @returns {Promise<Object>} SalaryEquivalenceResponse
 */
export async function getSalaryEquivalence(payload) {
  return api.post("/compare/salary-equivalence", payload);
}

// ═══════════════════════════════════════════════════════════════════════════
// ANALYTICS ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * GET /analytics/overview
 * Average scores per city across all personas + overall ranking.
 * @returns {Promise<Object>}
 */
export async function getAnalyticsOverview() {
  return api.get("/analytics/overview");
}

/**
 * GET /analytics/persona-rankings/{persona}
 * City rankings for a specific persona.
 * @param {string} persona - "early_career" | "family_focused" | "budget_focused"
 * @param {boolean} [hasChildren=false]
 * @returns {Promise<Object>}
 */
export async function getPersonaRankings(persona, hasChildren = false) {
  return api.get(
    `/analytics/persona-rankings/${encodeURIComponent(persona)}?has_children=${hasChildren}`
  );
}

/**
 * GET /analytics/real-health-summary
 * Summary of all real government health data in the database.
 * @returns {Promise<Object>}
 */
export async function getRealHealthSummary() {
  return api.get("/analytics/real-health-summary");
}

// ═══════════════════════════════════════════════════════════════════════════
// RECOMMENDATIONS ENDPOINT
// ═══════════════════════════════════════════════════════════════════════════

/**
 * POST /recommendations/best-city
 * ML RandomForest prediction of best city for a user profile.
 * @param {{ age: number, current_city: string, target_cities: string[], persona: string, monthly_income: number, dependents_count: number, priority_1: string, priority_2: string, priority_3: string, has_children: boolean, years_experience: number }} payload
 * @returns {Promise<Object>} RecommendationResponse
 */
export async function getBestCity(payload) {
  return api.post("/recommendations/best-city", payload);
}

// ═══════════════════════════════════════════════════════════════════════════
// NARRATE ENDPOINT
// ═══════════════════════════════════════════════════════════════════════════

/**
 * POST /narrate/
 * Gemini-powered plain-English narrative explanation.
 * @param {{ persona: string, best_city: string, monthly_income: number, cities_compared: string[], composite_score: number, top_positive_dimension: string, top_positive_score: number, top_negative_dimension: string, top_negative_score: number, has_children: boolean, required_salary_equivalent?: number }} payload
 * @returns {Promise<Object>} NarrativeResponse
 */
export async function getNarrative(payload) {
  try {
    // Current backend route
    return await api.post("/narrate/relocation", payload);
  } catch (err) {
    // Backward compatibility for older backend snapshots
    if (err?.status === 404) {
      return api.post("/narrate/", payload);
    }
    throw err;
  }
}

export default api;