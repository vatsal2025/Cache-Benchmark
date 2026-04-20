import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchExperiment, fetchScorecard, startExperiment, fetchBacktests, uploadLabels } from "../lib/api";
import { pct, statusColor, recColor, pvalColor } from "../lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, Legend,
} from "recharts";
import { ArrowLeft, Play, Download, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { downloadScorecardJson, downloadScorecardPdf } from "../lib/api";

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadMsg, setUploadMsg] = useState("");

  const { data: exp, isLoading: expLoading } = useQuery({
    queryKey: ["experiment", id],
    queryFn: () => fetchExperiment(id!),
    refetchInterval: (q) => ["running", "analysing"].includes(q.state.data?.status) ? 5000 : false,
  });

  const { data: scorecard } = useQuery({
    queryKey: ["scorecard", id],
    queryFn: () => fetchScorecard(id!),
    enabled: exp?.status === "complete" || exp?.status === "backtesting",
    retry: false,
  });

  const { data: backtests = [] } = useQuery({
    queryKey: ["backtests", id],
    queryFn: () => fetchBacktests(id!),
    enabled: !!exp?.backtest_enabled,
  });

  const startMutation = useMutation({
    mutationFn: () => startExperiment(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiment", id] }),
  });

  async function handleLabelUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await uploadLabels(id!, file);
      setUploadMsg(`Uploaded ${res.labels_uploaded} labels. BPAS F1: ${(res.validation_result.f1_bpas * 100).toFixed(1)}%`);
      qc.invalidateQueries({ queryKey: ["scorecard", id] });
    } catch {
      setUploadMsg("Upload failed. Check CSV format: account_id, group, human_label");
    }
  }

  if (expLoading) return <Spinner />;
  if (!exp) return <div className="p-8 text-gray-500">Not found</div>;

  const sc = scorecard;

  const pasData = sc ? [
    { group: "Control", GPAS: +(sc.control.gpas_proportion * 100).toFixed(1), BPAS: +(sc.control.bpas_proportion * 100).toFixed(1), EPAS: +(sc.control.epas_proportion * 100).toFixed(1) },
    { group: "Test", GPAS: +(sc.test.gpas_proportion * 100).toFixed(1), BPAS: +(sc.test.bpas_proportion * 100).toFixed(1), EPAS: +(sc.test.epas_proportion * 100).toFixed(1) },
  ] : [];

  const radarData = sc ? [
    { subject: "Category Div.", value: +(sc.design_guideline_scores.category_diversity * 100).toFixed(0) },
    { subject: "Occlusion", value: +(sc.design_guideline_scores.occlusion_score * 100).toFixed(0) },
    { subject: "Variation", value: +(sc.design_guideline_scores.variation_density * 100).toFixed(0) },
  ] : [];

  const funnelData = sc?.clearance_funnel?.control
    ? sc.clearance_funnel.control.map((step: Record<string, unknown>, i: number) => ({
        step: step.step as string,
        control: step.count as number,
        test: sc.clearance_funnel.test[i]?.count as number,
      }))
    : [];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <button onClick={() => navigate("/experiments")} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 mb-6">
        <ArrowLeft size={16} /> Back to Experiments
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{exp.name}</h1>
          <p className="text-gray-500 mt-1 text-sm">N={exp.n_day_delay}d delay · {exp.backtest_enabled ? "Backtest enabled" : "No backtest"}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={statusColor(exp.status)}>{exp.status}</span>
          {exp.status === "draft" && (
            <button onClick={() => startMutation.mutate()} disabled={startMutation.isPending} className="btn-primary flex items-center gap-2">
              <Play size={16} /> {startMutation.isPending ? "Starting…" : "Start Experiment"}
            </button>
          )}
          {startMutation.error && (
            <span className="text-red-600 text-sm">{(startMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed"}</span>
          )}
        </div>
      </div>

      {/* Progress indicator for running */}
      {(exp.status === "running" || exp.status === "analysing") && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center gap-3 text-blue-800">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">
            {exp.status === "running" ? "Experiment running — collecting clearance events and classifying accounts…" : "Analysing results — computing PAS distributions and statistical tests…"}
          </span>
        </div>
      )}

      {/* Scorecard */}
      {sc && (
        <>
          {/* Recommendation */}
          <div className={`p-4 rounded-xl border mb-6 ${recColor(sc.recommendation)}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-bold text-lg">{sc.recommendation.replace(/_/g, " ")}</p>
                {sc.executive_summary && <p className="text-sm mt-1 opacity-90">{sc.executive_summary}</p>}
              </div>
              <div className="flex gap-2">
                <a href={downloadScorecardJson(id!)} target="_blank" rel="noopener noreferrer" className="btn-secondary flex items-center gap-1 text-xs py-1.5 px-3">
                  <Download size={13} /> JSON
                </a>
                <a href={downloadScorecardPdf(id!)} target="_blank" rel="noopener noreferrer" className="btn-secondary flex items-center gap-1 text-xs py-1.5 px-3">
                  <Download size={13} /> PDF
                </a>
              </div>
            </div>
          </div>

          {/* Side-by-side metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-4">Key Metrics Comparison</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-100">
                    <th className="text-left py-2">Metric</th>
                    <th className="text-right py-2">Control</th>
                    <th className="text-right py-2">Test</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Clearance Rate", pct(sc.control.clearance_rate), pct(sc.test.clearance_rate)],
                    ["GPAS (Real)", pct(sc.control.gpas_proportion), pct(sc.test.gpas_proportion)],
                    ["BPAS (Fake)", pct(sc.control.bpas_proportion), pct(sc.test.bpas_proportion)],
                    ["EPAS (Empty)", pct(sc.control.epas_proportion), pct(sc.test.epas_proportion)],
                    ["ASR Holistic", pct(sc.control.asr_holistic), pct(sc.test.asr_holistic)],
                    ["ASR Modular", pct(sc.control.asr_modular), pct(sc.test.asr_modular)],
                  ].map(([label, ctrl, test]) => (
                    <tr key={label} className="border-b border-gray-50">
                      <td className="py-2 text-gray-600">{label}</td>
                      <td className="py-2 text-right font-mono text-xs">{ctrl}</td>
                      <td className="py-2 text-right font-mono text-xs font-semibold text-brand-700">{test}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Statistical significance */}
            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-1">Statistical Significance</h2>
              <p className="text-xs text-gray-400 mb-4">Wald binomial CI + 2-proportion z-test (Kozlov et al., Section 5.6)</p>
              <div className="space-y-4">
                {[
                  { label: "Clearance Rate", p: sc.statistical_significance.clearance_rate_pvalue },
                  { label: "BPAS Proportion", p: sc.statistical_significance.bpas_proportion_pvalue },
                ].map(({ label, p }) => (
                  <div key={label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{label}</span>
                      <span className={pvalColor(p)}>p = {p?.toFixed(4) ?? "—"}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${p != null && p < 0.05 ? "bg-green-500" : "bg-gray-300"}`} style={{ width: p != null ? `${Math.min(100, (1 - p) * 100)}%` : "0%" }} />
                    </div>
                  </div>
                ))}
                <div className={`text-sm font-semibold mt-2 ${sc.statistical_significance.significant ? "text-green-700" : "text-yellow-700"}`}>
                  {sc.statistical_significance.significant ? "✓ Statistically significant (α=0.05)" : "⚠ Not significant — collect more data"}
                </div>
              </div>
            </div>
          </div>

          {/* PAS distribution + Funnel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-4">PAS Label Distribution</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={pasData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="group" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Legend />
                  <Bar dataKey="GPAS" stackId="a" fill="#22c55e" />
                  <Bar dataKey="BPAS" stackId="a" fill="#ef4444" />
                  <Bar dataKey="EPAS" stackId="a" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {funnelData.length > 0 && (
              <div className="card">
                <h2 className="font-semibold text-gray-900 mb-4">Clearance Funnel</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={funnelData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="step" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="control" fill="#1a56db" name="Control" />
                    <Bar dataKey="test" fill="#7c3aed" name="Test" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Design guidelines radar */}
          {radarData.length > 0 && (
            <div className="card mb-6">
              <h2 className="font-semibold text-gray-900 mb-4">Design Guideline Scores (Test Variant)</h2>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={80}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Radar name="Score" dataKey="value" stroke="#1a56db" fill="#1a56db" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Human label upload */}
          <div className="card mb-6">
            <h2 className="font-semibold text-gray-900 mb-2">Upload Human Labels</h2>
            <p className="text-sm text-gray-500 mb-4">CSV columns: account_id, group, human_label (abusive/benign/empty). Min 400 labels per group (Wald method).</p>
            <div className="flex items-center gap-3">
              <button onClick={() => fileRef.current?.click()} className="btn-secondary flex items-center gap-2">
                <Upload size={16} /> Choose CSV File
              </button>
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleLabelUpload} />
              {uploadMsg && <p className="text-sm text-green-700">{uploadMsg}</p>}
            </div>
          </div>
        </>
      )}

      {/* Backtest section */}
      {backtests.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Backtest Holdouts</h2>
          {backtests.map((bt: Record<string, unknown>) => (
            <BacktestCard key={bt.id as string} bt={bt} />
          ))}
        </div>
      )}
    </div>
  );
}

function BacktestCard({ bt }: { bt: Record<string, unknown> }) {
  const hist = (bt.bpas_history as { date: string; bpas_prevalence: number }[]) || [];
  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-3">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className={statusColor(bt.status as string)}>{bt.status as string}</span>
          <span className="ml-3 text-sm text-gray-500">{bt.holdout_pct as number}% holdout</span>
        </div>
        {(bt.active_alerts as number) > 0 && (
          <span className="badge-red">⚠ {bt.active_alerts as number} active alert(s)</span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm mb-3">
        <div><span className="text-gray-500">Baseline BPAS:</span> <span className="font-semibold">{pct(bt.baseline_bpas_prevalence as number)}</span></div>
        <div><span className="text-gray-500">Current BPAS:</span> <span className="font-semibold">{pct(bt.current_bpas_prevalence as number)}</span></div>
      </div>
      {hist.length > 1 && (
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={hist}>
            <XAxis dataKey="date" tick={{ fontSize: 9 }} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 9 }} />
            <Tooltip formatter={(v: number) => pct(v)} />
            <Line type="monotone" dataKey="bpas_prevalence" stroke="#ef4444" dot={false} strokeWidth={2} name="BPAS" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
