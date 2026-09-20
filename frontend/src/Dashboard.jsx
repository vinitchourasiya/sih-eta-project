import { useState, useRef } from "react";
import axios from "axios";
import {
  Search, TrainFront, Check, CalendarClock, Sparkles, ShieldCheck,
  CloudFog, TrainTrack, Timer, AlertTriangle, Bus, ArrowRight, SearchX
} from "lucide-react";

const ALL_STATIONS = [
  { code: "NDLS", name: "New Delhi" },
  { code: "KOTA", name: "Kota Jn" },
  { code: "RTM", name: "Ratlam Jn" },
  { code: "BRC", name: "Vadodara Jn" },
  { code: "ST", name: "Surat" },
  { code: "MMCT", name: "Mumbai Central" },
];
const SCHEDULED_TIMES = {
  "New Delhi": "10:00 AM",
  "Kota Jn": "2:00 PM",
  "Ratlam Jn": "5:30 PM",
  "Vadodara Jn": "8:00 PM",
  "Surat": "9:30 PM",
  "Mumbai Central": "11:45 PM",
};

function getActualTime(scheduledStr, delayMin) {
  const [time, period] = scheduledStr.split(" ");
  let [hours, minutes] = time.split(":").map(Number);
  if (period === "PM" && hours !== 12) hours += 12;
  if (period === "AM" && hours === 12) hours = 0;

  const totalMinutes = hours * 60 + minutes + delayMin;
  let newHours = Math.floor(totalMinutes / 60) % 24;
  const newMinutes = Math.round(totalMinutes % 60);
  const newPeriod = newHours >= 12 ? "PM" : "AM";
  const displayHours = newHours % 12 === 0 ? 12 : newHours % 12;

  return `${displayHours}:${String(newMinutes).padStart(2, "0")} ${newPeriod}`;
}

const POPULAR_TRAINS = [
  { number: "12951", name: "Mumbai Rajdhani Express" },
  { number: "12953", name: "August Kranti Rajdhani" },
  { number: "12009", name: "Shatabdi Express" },
  { number: "22119", name: "Tejas Express" },
];

function getStatus(delay) {
  if (delay < 5) return { label: "On Time", badge: "bg-success/15 text-success border-success/30", dot: "bg-success" };
  if (delay < 20) return { label: "Minor Delay", badge: "bg-warning/20 text-warning-foreground border-warning/40", dot: "bg-warning" };
  return { label: "Major Delay", badge: "bg-danger/15 text-danger border-danger/30", dot: "bg-danger" };
}

function LandingPage({ query, setQuery, onSubmit }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-3xl items-center justify-center gap-2.5 px-4 pt-10 pb-2 sm:pt-16">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-rail-blue text-rail-blue-foreground">
          <TrainFront className="h-5 w-5" />
        </span>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Dynamic ETA <span className="text-muted-foreground">· Indian Railways</span>
        </span>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-16">
        <section className="flex flex-col items-center pt-10 text-center sm:pt-16">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Know when your train really arrives
          </h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
            Live, AI-powered arrival predictions for every train across the network.
          </p>

          <form onSubmit={onSubmit} className="mt-8 w-full max-w-xl">
            <div className="flex items-center gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm">
              <Search className="ml-2 h-5 w-5 shrink-0 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter train number or name"
                className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              <button
                type="submit"
                className="shrink-0 rounded-xl bg-rail-orange px-4 py-2 text-sm font-semibold text-rail-orange-foreground hover:opacity-90"
              >
                Search
              </button>
            </div>
          </form>
        </section>

        <section className="mt-14">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Popular Trains</h2>
            <span className="text-xs text-muted-foreground">Tap a train to track</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {POPULAR_TRAINS.map((train) => (
              <button
                key={train.number}
                onClick={() => onSubmit(null, train.number)}
                className="group flex items-center justify-between gap-4 rounded-2xl border border-border bg-card p-4 shadow-sm hover:border-rail-blue/40 text-left"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-rail-blue/10 px-2 py-0.5 text-xs font-semibold text-rail-blue">
                      #{train.number}
                    </span>
                    <h3 className="truncate text-sm font-semibold text-foreground">{train.name}</h3>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-rail-orange" />
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function DashboardHeader({ query, setQuery, onSubmit }) {
  return (
    <header className="bg-rail-blue text-rail-blue-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rail-orange text-rail-orange-foreground shadow-sm">
            <TrainFront className="h-6 w-6" />
          </span>
          <div className="leading-tight">
            <h1 className="text-lg font-semibold tracking-tight">Dynamic ETA</h1>
            <p className="text-xs font-medium text-rail-blue-foreground/70">Indian Railways</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="flex w-full items-center gap-2 sm:max-w-sm">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Train number or name"
              className="h-11 w-full rounded-xl border border-transparent bg-card pl-9 pr-3 text-sm text-foreground shadow-sm outline-none"
            />
          </div>
          <button type="submit" className="h-11 shrink-0 rounded-xl bg-rail-orange px-4 text-sm font-semibold text-rail-orange-foreground hover:opacity-90">
            Search
          </button>
        </form>
      </div>
    </header>
  );
}

function RouteTimeline({ currentStation }) {
  const currentIndex = ALL_STATIONS.findIndex((s) => s.name === currentStation);
  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <h2 className="mb-6 text-sm font-semibold text-foreground">Route Progress</h2>
      <ol className="flex items-start justify-between">
        {ALL_STATIONS.map((station, i) => {
          const isCurrent = i === currentIndex;
          const isDeparted = i < currentIndex;
          return (
            <li key={station.code} className="relative flex flex-1 flex-col items-center last:flex-none">
              {i < ALL_STATIONS.length - 1 && (
                <span className={`absolute left-1/2 top-4 h-0.5 w-full ${isDeparted ? "bg-rail-blue" : "bg-border"}`} />
              )}
              <span className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                isCurrent ? "border-rail-orange bg-rail-orange text-rail-orange-foreground shadow-md ring-4 ring-rail-orange/20"
                : isDeparted ? "border-rail-blue bg-rail-blue text-rail-blue-foreground"
                : "border-border bg-card text-muted-foreground"
              }`}>
                {isCurrent ? <TrainFront className="h-4 w-4" /> : isDeparted ? <Check className="h-4 w-4" /> : <span className="h-2 w-2 rounded-full bg-muted-foreground/50" />}
              </span>
              <div className="mt-2 flex flex-col items-center px-1 text-center">
                <span className={`text-[11px] font-semibold ${isCurrent ? "text-rail-orange" : "text-foreground"}`}>{station.code}</span>
                <span className="mt-0.5 hidden text-[11px] leading-tight text-muted-foreground sm:block">{station.name}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function EtaComparison({ data }) {
  const status = getStatus(data.predictedDelayMin);
  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Arrival Estimate</h2>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${status.badge}`}>
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          {status.label} · +{Math.round(data.predictedDelayMin)} min
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-secondary/50 p-4">
  <div className="flex items-center gap-2 text-muted-foreground">
    <CalendarClock className="h-4 w-4" />
    <span className="text-xs font-medium uppercase tracking-wide">Scheduled Arrival</span>
  </div>
  <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">
    {SCHEDULED_TIMES[data.nextStation]}
  </p>
  <p className="mt-1 text-xs text-muted-foreground">{data.weather} · {data.congestion}</p>
</div>
        <div className="rounded-xl border border-rail-orange/30 bg-rail-orange/5 p-4">
          <div className="flex items-center gap-2 text-rail-orange">
            <Sparkles className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">Predicted Delay</span>
          </div>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">
  {getActualTime(SCHEDULED_TIMES[data.nextStation], data.etaRangeMin)}
  <span className="mx-1 text-muted-foreground">–</span>
  {getActualTime(SCHEDULED_TIMES[data.nextStation], data.etaRangeMax)}
</p>
<p className="mt-0.5 text-xs text-muted-foreground">
  (+{Math.round(data.etaRangeMin * 10) / 10}–{Math.round(data.etaRangeMax * 10) / 10} min delay)
</p>
          <p className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-rail-orange">
            <ShieldCheck className="h-3.5 w-3.5" />
            {data.confidencePercent}% confidence
          </p>
        </div>
      </div>
    </section>
  );
}

const REASON_ICONS = { Fog: CloudFog, "Heavy Rain": CloudFog, Rain: CloudFog, "Route Congestion": TrainTrack, "Historical Pattern": Timer };

function DelayReasons({ reasons }) {
  const weights = { High: 45, Medium: 30, Low: 15 };
  const withContribution = reasons.map((r) => ({ ...r, value: weights[r.impact] || 20 }));
  const total = withContribution.reduce((sum, r) => sum + r.value, 0) || 1;

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-semibold text-foreground">Why this delay?</h2>
      <p className="mt-1 text-xs text-muted-foreground">Estimated contribution of each factor.</p>
      <ul className="mt-4 space-y-4">
        {withContribution.map((reason, i) => {
          const Icon = REASON_ICONS[reason.factor] || Timer;
          const pct = Math.round((reason.value / total) * 100);
          return (
            <li key={i}>
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rail-blue/10 text-rail-blue">
                    <Icon className="h-4 w-4" />
                  </span>
                  {reason.factor}
                </span>
                <span className="text-sm font-semibold tabular-nums text-foreground">{pct}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-rail-orange" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ConnectionsAffected({ alerts, delay }) {
  if (!alerts || alerts.length === 0) return null;
  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-warning-foreground" />
        <h2 className="text-sm font-semibold text-foreground">Connections Affected</h2>
      </div>
      <ul className="mt-4 space-y-3">
        {alerts.map((alert, i) => {
          const isCritical = delay > 20;
          const Icon = alert.toLowerCase().includes("bus") || alert.toLowerCase().includes("feeder") ? Bus : TrainFront;
          return (
            <li key={i} className={`flex gap-3 rounded-xl border p-3.5 ${isCritical ? "border-danger/30 bg-danger/5" : "border-warning/40 bg-warning/10"}`}>
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${isCritical ? "bg-danger/15 text-danger" : "bg-warning/25 text-warning-foreground"}`}>
                <Icon className="h-4 w-4" />
              </span>
              <p className="text-sm font-semibold text-foreground">{alert}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Dashboard() {
  const [view, setView] = useState("landing");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [simulating, setSimulating] = useState(false);
  const stationIndexRef = useRef(0);
  const intervalRef = useRef(null);

  const fetchPrediction = async (trainNumber, stationIndex = null) => {
    try {
      const payload = { trainNumber };
      if (stationIndex !== null) payload.stationIndex = stationIndex;
      const response = await axios.post("https://sih-eta-backend-l25w.onrender.com/predict", payload);
      setData(response.data);
      setError("");
    } catch (err) {
      setError("Could not fetch prediction. Is the backend running?");
    }
  };

  const handleSubmit = async (e, directTrainNumber = null) => {
    if (e) e.preventDefault();
    const trainNumber = directTrainNumber || query;
    if (!trainNumber) return;
    setQuery(trainNumber);
    setView("dashboard");
    setLoading(true);
    await fetchPrediction(trainNumber);
    setLoading(false);
  };

  const handleSimulate = () => {
    setSimulating(true);
    stationIndexRef.current = 0;
    fetchPrediction(query, 0);
    intervalRef.current = setInterval(() => {
      stationIndexRef.current += 1;
      if (stationIndexRef.current >= 5) {
        fetchPrediction(query, stationIndexRef.current);
        clearInterval(intervalRef.current);
        setSimulating(false);
        return;
      }
      fetchPrediction(query, stationIndexRef.current);
    }, 3000);
  };

  const stopSimulation = () => {
    clearInterval(intervalRef.current);
    setSimulating(false);
  };

  if (view === "landing") {
    return <LandingPage query={query} setQuery={setQuery} onSubmit={handleSubmit} />;
  }

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader query={query} setQuery={setQuery} onSubmit={handleSubmit} />
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-4">
          {!simulating ? (
            <button onClick={handleSimulate} className="rounded-xl bg-rail-blue px-4 py-2 text-sm font-semibold text-rail-blue-foreground hover:opacity-90">
              ▶ Simulate Train Movement
            </button>
          ) : (
            <button onClick={stopSimulation} className="rounded-xl bg-danger px-4 py-2 text-sm font-semibold text-danger-foreground hover:opacity-90">
              ■ Stop Simulation
            </button>
          )}
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading prediction...</p>}
        {error && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-card p-12 text-center shadow-sm">
            <SearchX className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">{error}</p>
          </div>
        )}

        {data && !error && (
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-rail-blue/10 px-2 py-0.5 text-xs font-semibold text-rail-blue">#{data.trainNumber}</span>
                  <h2 className="text-base font-semibold text-foreground">{data.trainName}</h2>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{data.currentStation} → {data.nextStation}</p>
              </div>
            </div>

            <RouteTimeline currentStation={data.currentStation} />
            <EtaComparison data={data} />

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <DelayReasons reasons={data.reasons} />
              <ConnectionsAffected alerts={data.cascadeAlerts} delay={data.predictedDelayMin} />
            </div>
          </div>
        )}
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 sm:px-6">
        <p className="text-center text-xs text-muted-foreground">
          Predictions are estimates generated from live network data · Dynamic ETA · Indian Railways
        </p>
      </footer>
    </div>
  );
}

export default Dashboard;