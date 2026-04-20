import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCaptcha, fetchAttackResults, runAttacks } from "../lib/api";
import { pct, fmt, statusColor } from "../lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend, ReferenceLine,
} from "recharts";
import { ArrowLeft, Play, RefreshCw } from "lucide-react";
import { useState } from "react";

const ATTACK_COLORS: Record<string, string> = {
  holistic: "#1a56db",
  modular: "#7c3aed",
  bot_baseline: "#d97706",
  random_baseline: "#6b7280",
};

// Published reference ASRs from Gao et al.
const REFERENCE_ASR = { holistic: 0.673, modular: 0.880 };

const ERROR_COLORS = ["#ef4444", "#f97316", "#eab308", "#3b82f6"];

export default function AttackBenchmarkPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [sampleSize, setSampleSize] = useState(1000);
  const [mode, setMode] = useState("standard");

  const { data: cap } = useQuery({ queryKey: ["captcha", id], queryFn: () => fetchCaptcha(id!) });
  const { data: results, isLoading, refetch } = useQuery({
    queryKey: ["attack-results", id],
    queryFn: () => fetchAttackResults(id!),
    refetchInterval: (q) => {
      const runs = q.state.data?.results || [];
      const hasRunning = runs.some((r: Record<string, unknown>) => r.status === "pending" || r.status === "running");
      return hasRunning ? 3000 : false;
    },
  });

  const runMutation = useMutation({
    mutationFn: (attackTypes: string[]) =>
      runAttacks(id!, { attack_types: attackTypes, sample_size: sampleSize, mode }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attack-results", id] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to enqueue attacks";
      alert(`Error: ${msg}`);
    },
  });

  const runs = results?.results || [];
  const complete = runs.filter((r: Record<string, unknown>) => r.status === "complete");

  // Build bar chart data
  const asrData = complete.map((r: Record<string, unknown>) => ({
    name: r.attack_type as string,
    asr: Number(((r.asr_overall as number) * 100).toFixed(1)),
    fill: ATTACK_COLORS[r.attack_type as string] || "#94a3b8",
  }));

  // Category breakdown for the best complete holistic run
  const holisticRun = complete.find((r: Record<string, unknown>) => r.attack_type === "holistic");
  const catData = holisticRun?.asr_by_category
    ? Object.entries(holisticRun.asr_by_category as Record<string, number>).map(([k, v]) => ({
        name: k.replace(/_/g, " "),
        asr: Number((v * 100).toFixed(1)),
      }))
    : [];

  // Error breakdown pie
  const modularRun = complete.find((r: Record<string, unknown>) => r.attack_type === "modular") || holisticRun;
  const pieData = modularRun?.error_breakdown
    ? Object.entries(modularRun.error_breakdown as Record<string, number>).map(([k, v], i) => ({
        name: k.replace(/_/g, " ").toUpperCase(),
        value: Number((v * 100).toFixed(1)),
        fill: ERROR_COLORS[i % ERROR_COLORS.length],
      }))
    : [];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <button onClick={() => navigate(`/captchas/${id}`)} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 mb-6">
        <ArrowLeft size={16} /> Back to {cap?.name || "CAPTCHA"}
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Attack Benchmark</h1>
          <p className="text-gray-500 mt-1 text-sm">{cap?.name} · {cap?.captcha_type}</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={sampleSize} onChange={(e) => setSampleSize(Number(e.target.value))}>
            {[500, 1000, 2000, 5000, 10000].map((n) => <option key={n}>{n}</option>)}
          </select>
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="standard">Standard</option>
            <option value="fast">⚡ Fast</option>
          </select>
          <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2"><RefreshCw size={16} /></button>
          <button
            onClick={() => runMutation.mutate(["holistic", "modular", "bot_baseline", "random_baseline"])}
            disabled={runMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <Play size={16} /> {runMutation.isPending ? "Queuing…" : "Run All Attacks"}
          </button>
        </div>
      </div>

      {/* Pending/running indicator */}
      {runs.some((r: Record<string, unknown>) => r.status === "pending" || r.status === "running") && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          Attack runs in progress — auto-refreshing every 3 seconds…
        </div>
      )}

      {/* Real vs estimated banner */}
      {complete.length > 0 && (
        <div className={`mb-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
          complete.some((r: Record<string, unknown>) => !r.is_estimated)
            ? "bg-green-50 border border-green-200 text-green-800"
            : "bg-yellow-50 border border-yellow-200 text-yellow-800"
        }`}>
          {complete.some((r: Record<string, unknown>) => !r.is_estimated)
            ? "✓ Real YOLOv8n measurements — ASR computed from actual image inference"
            : "⚠ Estimated results — upload CAPTCHA sample images to enable real YOLO attack measurement"}
        </div>
      )}

      {/* ASR overview */}
      {asrData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-1">Attack Success Rate by Module</h2>
            <p className="text-xs text-gray-400 mb-4">Dashed lines = reference values from Gao et al. (VTT)</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={asrData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => `${v}%`} />
                <ReferenceLine x={REFERENCE_ASR.holistic * 100} stroke="#1a56db" strokeDasharray="4 2" label={{ value: "Gao holistic", fontSize: 10, fill: "#1a56db", position: "top" }} />
                <ReferenceLine x={REFERENCE_ASR.modular * 100} stroke="#7c3aed" strokeDasharray="4 2" label={{ value: "Gao modular", fontSize: 10, fill: "#7c3aed", position: "top" }} />
                <Bar dataKey="asr" fill="#1a56db" radius={[0, 4, 4, 0]}>
                  {asrData.map((entry: { name: string; asr: number; fill: string }, i: number) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Error breakdown */}
          {pieData.length > 0 && (
            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-4">Error Distribution</h2>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}%`} labelLine={false}>
                    {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v}%`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Category breakdown */}
      {catData.length > 0 && (
        <div className="card mb-6">
          <h2 className="font-semibold text-gray-900 mb-4">ASR by Category (Holistic Attack)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={catData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${v}%`} />
              <Bar dataKey="asr" fill="#1a56db" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Results table */}
      <div className="card overflow-hidden p-0">
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <h2 className="font-semibold text-gray-900 text-sm">All Attack Runs</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 font-medium">Attack Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">ASR</th>
              <th className="px-4 py-3 font-medium">Human Parity</th>
              <th className="px-4 py-3 font-medium">Avg Time (ms)</th>
              <th className="px-4 py-3 font-medium">Model</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No attacks run yet. Click "Run All Attacks" to begin.</td></tr>
            ) : (
              runs.map((r: Record<string, unknown>) => (
                <tr key={r.attack_run_id as string} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-gray-900">{r.attack_type as string}</td>
                  <td className="px-4 py-3"><span className={statusColor(r.status as string)}>{r.status as string}</span></td>
                  <td className="px-4 py-3">
                    <span className="font-semibold text-gray-900">{pct(r.asr_overall as number)}</span>
                    {r.status === "complete" && (
                      <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${r.is_estimated ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
                        {r.is_estimated ? "est." : `real · ${r.n_images_used}imgs`}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">{pct(r.human_parity_score as number)}</td>
                  <td className="px-4 py-3">{fmt(r.avg_processing_time_ms as number)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.model_version as string}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
