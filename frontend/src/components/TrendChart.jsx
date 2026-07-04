import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { THEME } from "../styles/theme.js";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      style={{
        backgroundColor: THEME.colors.surface,
        border: `1px solid ${THEME.colors.border}`,
        borderRadius: THEME.radius.md,
        padding: THEME.spacing.md,
        boxShadow: THEME.shadows.lg,
        fontFamily: THEME.fonts.body,
        minWidth: "160px",
      }}
    >
      <p
        style={{
          fontSize: THEME.fontSizes.xs,
          color: THEME.colors.textMuted,
          marginBottom: THEME.spacing.sm,
          fontWeight: THEME.fontWeights.semibold,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </p>
      {payload.map((entry) => (
        <div
          key={entry.dataKey}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: THEME.spacing.lg,
            marginBottom: "4px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: THEME.spacing.xs }}>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: THEME.radius.full,
                backgroundColor: entry.color,
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: THEME.fontSizes.xs, color: THEME.colors.textMuted }}>
              {entry.name}
            </span>
          </div>
          <span
            style={{
              fontSize: THEME.fontSizes.sm,
              fontWeight: THEME.fontWeights.semibold,
              color: THEME.colors.text,
              fontFamily: THEME.fonts.mono,
            }}
          >
            {typeof entry.value === "number"
              ? entry.value % 1 === 0
                ? entry.value.toLocaleString("en-IN")
                : entry.value.toFixed(1)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function CustomLegend({ payload }) {
  if (!payload) return null;
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: THEME.spacing.md,
        justifyContent: "center",
        paddingTop: THEME.spacing.sm,
      }}
    >
      {payload.map((entry) => (
        <div
          key={entry.value}
          style={{ display: "flex", alignItems: "center", gap: THEME.spacing.xs }}
        >
          <div
            style={{
              width: "12px",
              height: "2px",
              backgroundColor: entry.color,
              borderRadius: THEME.radius.full,
            }}
          />
          <span
            style={{
              fontSize: THEME.fontSizes.xs,
              color: THEME.colors.textMuted,
              fontFamily: THEME.fonts.body,
            }}
          >
            {entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function TrendChart({
  data,
  xKey,
  lines,
  title,
  height = 280,
  yAxisLabel,
  yTickFormatter,
}) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: THEME.colors.surface,
          borderRadius: THEME.radius.lg,
          border: `1px solid ${THEME.colors.border}`,
        }}
      >
        <span
          style={{
            color: THEME.colors.textFaint,
            fontSize: THEME.fontSizes.sm,
            fontFamily: THEME.fonts.body,
          }}
        >
          No trend data available
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: THEME.colors.surface,
        borderRadius: THEME.radius.lg,
        border: `1px solid ${THEME.colors.border}`,
        padding: THEME.spacing.lg,
        boxShadow: THEME.shadows.md,
      }}
    >
      {title && (
        <p
          style={{
            fontSize: THEME.fontSizes.sm,
            fontWeight: THEME.fontWeights.semibold,
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.body,
            marginBottom: THEME.spacing.md,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {title}
        </p>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid
            stroke={THEME.colors.border}
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey={xKey}
            tick={{
              fill: THEME.colors.textFaint,
              fontSize: 11,
              fontFamily: THEME.fonts.body,
            }}
            axisLine={{ stroke: THEME.colors.border }}
            tickLine={false}
            tickMargin={8}
          />
          <YAxis
            tick={{
              fill: THEME.colors.textFaint,
              fontSize: 11,
              fontFamily: THEME.fonts.mono,
            }}
            axisLine={false}
            tickLine={false}
            tickFormatter={yTickFormatter}
            label={
              yAxisLabel
                ? {
                    value: yAxisLabel,
                    angle: -90,
                    position: "insideLeft",
                    offset: 10,
                    style: {
                      fill: THEME.colors.textFaint,
                      fontSize: 10,
                      fontFamily: THEME.fonts.body,
                    },
                  }
                : undefined
            }
            width={yAxisLabel ? 60 : 45}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
          {lines.map(({ key, color, label }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={color}
              name={label || key}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}