import { TrainFront } from "lucide-react";

const riskColor = (risk) =>
  risk > 60 ? "#ef4444" : risk > 30 ? "#f59e0b" : "#22c55e";

function TrainSwitchCard({ r }) {
  return (
    <div
      style={{
        border: "1px solid #bfdbfe",
        background: "#eff6ff",
        borderRadius: "12px",
        padding: "14px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <TrainFront className="h-4 w-4 text-rail-blue" />
          <span
            style={{
              fontSize: "12px",
              fontWeight: 600,
              background: "#dbeafe",
              color: "#1e3a8a",
              padding: "2px 8px",
              borderRadius: "6px",
            }}
          >
            #{r.train.number}
          </span>
          <span style={{ fontWeight: 600, fontSize: "14px" }}>{r.train.name}</span>
          {r.train.type && (
            <span style={{ fontSize: "11px", color: "#6b7280" }}>{r.train.type}</span>
          )}
        </div>
        <span style={{ fontSize: "12px", fontWeight: 600, color: riskColor(r.risk), whiteSpace: "nowrap" }}>
          Risk {r.risk}%
        </span>
      </div>

      <p style={{ marginTop: "10px", fontSize: "13px", color: "#1f2937", lineHeight: 1.5 }}>
        {r.instruction}
      </p>

      <div
        style={{
          marginTop: "10px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: "8px",
        }}
      >
        <Stat label={`Get off at ${r.changeStation.code}`} value={r.getOffTime} />
        <Stat label="New train departs" value={r.departure} />
        <Stat label={`Reach ${r.destinationName}`} value={r.destinationArrival} />
        {r.timeSavedMin != null && <Stat label="Time saved" value={`${r.timeSavedMin} min`} highlight />}
      </div>

      <p style={{ marginTop: "8px", fontSize: "11px", color: "#6b7280" }}>
        {r.bufferMin} min to change trains · {r.extraCost} (check availability and fare on IRCTC)
      </p>
    </div>
  );
}

function Stat({ label, value, highlight }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "8px", padding: "8px 10px" }}>
      <p style={{ fontSize: "11px", color: "#6b7280" }}>{label}</p>
      <p style={{ fontSize: "14px", fontWeight: 600, color: highlight ? "#16a34a" : "#111827" }}>{value}</p>
    </div>
  );
}

export default function AlternativeRoutes({ routes }) {
  if (!routes || routes.length === 0) return null;

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-semibold text-foreground">Alternative Route Options</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
        {routes.map((r, i) =>
          r.type === "train_change" ? (
            <TrainSwitchCard key={i} r={r} />
          ) : (
            <div
              key={i}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: "10px",
                padding: "12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div>
                <p style={{ fontWeight: 600, fontSize: "13px" }}>{r.option}</p>
                <p style={{ fontSize: "12px", color: "#6b7280" }}>
                  {r.arrival} · Extra: {r.extraCost}
                </p>
              </div>
              {r.risk != null && (
                <span style={{ fontSize: "12px", fontWeight: 600, color: riskColor(r.risk) }}>
                  Risk {r.risk}%
                </span>
              )}
            </div>
          )
        )}
      </div>
    </section>
  );
}