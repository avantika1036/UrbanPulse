import { useState, useEffect, useRef } from "react";
import { getNarrative } from "../api/client.js";
import { THEME } from "../styles/theme.js";

export default function NarrativeBox({ narratePayload, disabled = false }) {
  const [status, setStatus] = useState("idle"); // idle | loading | streaming | done | error
  const [displayText, setDisplayText] = useState("");
  const [fullText, setFullText] = useState("");
  const [cached, setCached] = useState(false);
  const [model, setModel] = useState("");
  const [error, setError] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) clearInterval(streamRef.current);
    };
  }, []);

  const runTypewriter = (text) => {
    setStatus("streaming");
    setDisplayText("");
    let idx = 0;
    streamRef.current = setInterval(() => {
      idx += 2;
      setDisplayText(text.slice(0, idx));
      if (idx >= text.length) {
        clearInterval(streamRef.current);
        setDisplayText(text);
        setStatus("done");
      }
    }, 20);
  };

  const handleGenerate = async () => {
    if (!narratePayload || disabled) return;
    if (streamRef.current) clearInterval(streamRef.current);

    setStatus("loading");
    setDisplayText("");
    setError(null);

    try {
      const res = await getNarrative(narratePayload);
      setFullText(res.narrative || "");
      setCached(res.cached || false);
      setModel(res.model || "");
      runTypewriter(res.narrative || "");
    } catch (err) {
      setStatus("error");
      setError(err.message || "Failed to generate narrative.");
    }
  };

  const isGenerating = status === "loading" || status === "streaming";

  return (
    <div
      style={{
        backgroundColor: THEME.colors.surface,
        border: `1px solid ${THEME.colors.border}`,
        borderRadius: THEME.radius.lg,
        overflow: "hidden",
        boxShadow: THEME.shadows.md,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: `${THEME.spacing.md} ${THEME.spacing.lg}`,
          borderBottom: `1px solid ${THEME.colors.border}`,
          backgroundColor: THEME.colors.surface2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: THEME.spacing.sm,
        }}
      >
        <div>
          <p
            style={{
              fontSize: THEME.fontSizes.sm,
              fontWeight: THEME.fontWeights.semibold,
              color: THEME.colors.text,
              fontFamily: THEME.fonts.body,
              margin: 0,
            }}
          >
            AI-Generated Analysis
          </p>
          <p
            style={{
              fontSize: THEME.fontSizes.xs,
              color: THEME.colors.textFaint,
              fontFamily: THEME.fonts.body,
              margin: 0,
              marginTop: "2px",
            }}
          >
            Powered by Google Gemini
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: THEME.spacing.sm }}>
          {cached && status === "done" && (
            <span
              style={{
                fontSize: THEME.fontSizes.xs,
                color: THEME.colors.warning,
                fontFamily: THEME.fonts.body,
                backgroundColor: `${THEME.colors.warning}22`,
                padding: `2px ${THEME.spacing.sm}`,
                borderRadius: THEME.radius.full,
                border: `1px solid ${THEME.colors.warning}44`,
              }}
            >
              Cached
            </span>
          )}
          {model && status === "done" && (
            <span
              style={{
                fontSize: THEME.fontSizes.xs,
                color: THEME.colors.textFaint,
                fontFamily: THEME.fonts.mono,
              }}
            >
              {model}
            </span>
          )}
          <button
            onClick={handleGenerate}
            disabled={isGenerating || disabled || !narratePayload}
            style={{
              backgroundColor:
                isGenerating || disabled || !narratePayload
                  ? THEME.colors.surface2
                  : THEME.colors.accent,
              color:
                isGenerating || disabled || !narratePayload
                  ? THEME.colors.textFaint
                  : THEME.colors.white,
              border: `1px solid ${
                isGenerating || disabled || !narratePayload
                  ? THEME.colors.border
                  : THEME.colors.accent
              }`,
              borderRadius: THEME.radius.md,
              padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
              fontSize: THEME.fontSizes.sm,
              fontWeight: THEME.fontWeights.semibold,
              fontFamily: THEME.fonts.body,
              cursor: isGenerating || disabled || !narratePayload
                ? "not-allowed"
                : "pointer",
              transition: THEME.transitions.base,
              display: "flex",
              alignItems: "center",
              gap: THEME.spacing.xs,
            }}
          >
            {status === "loading" && (
              <span
                style={{
                  display: "inline-block",
                  width: "12px",
                  height: "12px",
                  border: `2px solid ${THEME.colors.textFaint}`,
                  borderTopColor: THEME.colors.accent,
                  borderRadius: THEME.radius.full,
                  animation: "spin 0.8s linear infinite",
                }}
              />
            )}
            {status === "streaming" ? "Generating..." : "Generate AI Summary"}
          </button>
        </div>
      </div>

      {/* Body */}
      <div
        style={{
          padding: THEME.spacing.lg,
          minHeight: "100px",
        }}
      >
        {status === "idle" && (
          <p
            style={{
              color: THEME.colors.textFaint,
              fontSize: THEME.fontSizes.sm,
              fontFamily: THEME.fonts.body,
              fontStyle: "italic",
            }}
          >
            {disabled || !narratePayload
              ? "Run a city comparison first to enable AI narrative generation."
              : "Click 'Generate AI Summary' to get a plain-English explanation of this comparison."}
          </p>
        )}

        {status === "loading" && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: THEME.spacing.sm,
              color: THEME.colors.textMuted,
              fontSize: THEME.fontSizes.sm,
              fontFamily: THEME.fonts.body,
            }}
          >
            <div style={{ display: "flex", gap: "4px" }}>
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: THEME.radius.full,
                    backgroundColor: THEME.colors.accent,
                    animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                  }}
                />
              ))}
            </div>
            Contacting Gemini...
          </div>
        )}

        {(status === "streaming" || status === "done") && (
          <div>
            <p
              style={{
                color: THEME.colors.text,
                fontSize: THEME.fontSizes.md,
                lineHeight: THEME.lineHeights.relaxed,
                fontFamily: THEME.fonts.body,
                margin: 0,
                whiteSpace: "pre-wrap",
              }}
            >
              {displayText}
              {status === "streaming" && (
                <span
                  style={{
                    display: "inline-block",
                    width: "2px",
                    height: "1em",
                    backgroundColor: THEME.colors.accent,
                    marginLeft: "2px",
                    verticalAlign: "text-bottom",
                    animation: "blink 0.7s step-end infinite",
                  }}
                />
              )}
            </p>
          </div>
        )}

        {status === "error" && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: THEME.spacing.sm,
            }}
          >
            <p
              style={{
                color: THEME.colors.danger,
                fontSize: THEME.fontSizes.sm,
                fontFamily: THEME.fonts.body,
                margin: 0,
              }}
            >
              Failed to generate narrative: {error}
            </p>
            <button
              onClick={handleGenerate}
              style={{
                alignSelf: "flex-start",
                backgroundColor: "transparent",
                color: THEME.colors.accent,
                border: `1px solid ${THEME.colors.accent}`,
                borderRadius: THEME.radius.md,
                padding: `${THEME.spacing.xs} ${THEME.spacing.md}`,
                fontSize: THEME.fontSizes.sm,
                fontFamily: THEME.fonts.body,
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes pulse {
          0%, 100% { transform: scale(0.6); opacity: 0.4; }
          50% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}