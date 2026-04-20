import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchCaptcha, fetchCaptchaHistory } from "../lib/api";
import { statusColor, pct } from "../lib/utils";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { ArrowLeft, Swords, Info } from "lucide-react";
import { format } from "date-fns";

export default function CaptchaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: cap, isLoading } = useQuery({ queryKey: ["captcha", id], queryFn: () => fetchCaptcha(id!) });
  const { data: hist } = useQuery({ queryKey: ["captcha-history", id], queryFn: () => fetchCaptchaHistory(id!) });

  if (isLoading) return <Spinner />;
  if (!cap) return <div className="p-8 text-gray-500">Not found</div>;

  const scores = cap.design_guideline_scores;
  const suggestions = cap.improvement_suggestions || [];
  const histData = (hist?.history || []).filter((h: Record<string, unknown>) => h.asr_overall != null);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <button onClick={() => navigate("/captchas")} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 mb-6">
        <ArrowLeft size={16} /> Back to Library
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{cap.name}</h1>
          <p className="text-gray-500 mt-1 text-sm">v{cap.version} · {cap.captcha_type}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={statusColor(cap.status)}>{cap.status}</span>
          <button onClick={() => navigate(`/captchas/${id}/attacks`)} className="btn-primary flex items-center gap-2">
            <Swords size={16} /> Run Attack Benchmark
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Metadata */}
        <div className="card lg:col-span-1">
          <h2 className="font-semibold text-gray-900 mb-4">Metadata</h2>
          <dl className="space-y-3 text-sm">
            {[
              ["Category Set Size", cap.category_set_size],
              ["Occlusion", cap.occlusion_enabled ? cap.occlusion_type : "None"],
              ["Variation Count", cap.variation_count],
              ["Challenge Format", cap.challenge_format || "—"],
              ["Tags", (cap.tags || []).join(", ") || "—"],
              ["Created", format(new Date(cap.created_at), "MMM d, yyyy")],
            ].map(([k, v]) => (
              <div key={k as string} className="flex justify-between">
                <dt className="text-gray-500">{k}</dt>
                <dd className="font-medium text-gray-800">{v as string}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Design guideline scores */}
        <div className="card lg:col-span-2">
          <h2 className="font-semibold text-gray-900 mb-1">Design Guideline Scores</h2>
          <p className="text-xs text-gray-400 mb-4">Based on Gao et al. (USENIX SEC 2021) Tables 11–12</p>
          <div className="space-y-4">
            {[
              { label: "Category Diversity", value: scores.category_diversity, tip: "50→100 classes reduces ASR ~8pp" },
              { label: "Occlusion Strength", value: scores.occlusion_score, tip: "Answer-object occlusion reduces ASR ~16pp with <1pp human penalty" },
              { label: "Variation Density", value: scores.variation_density, tip: "Tilt/notch/fracture attributes increase bot classification error" },
            ].map(({ label, value, tip }) => (
              <div key={label}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
                    {label}
                    <span title={tip} className="text-gray-400 cursor-help"><Info size={13} /></span>
                  </div>
                  <span className="text-sm font-bold text-gray-900">{Math.round(value * 100)}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${value >= 0.7 ? "bg-green-500" : value >= 0.4 ? "bg-yellow-500" : "bg-red-400"}`}
                    style={{ width: `${value * 100}%` }}
                  />
                </div>
              </div>
            ))}
            <div className="pt-2 border-t border-gray-100">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 font-medium">Aggregate Score</span>
                <span className="font-bold text-gray-900">{Math.round(scores.aggregate * 100)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Improvement suggestions */}
      {suggestions.length > 0 && (
        <div className="card mb-6 border-l-4 border-yellow-400 bg-yellow-50">
          <h2 className="font-semibold text-yellow-800 mb-3">Improvement Suggestions</h2>
          <ul className="space-y-2">
            {suggestions.map((s: Record<string, string>) => (
              <li key={s.dimension} className="text-sm text-yellow-900">
                <span className="font-medium capitalize">{s.dimension.replace("_", " ")}:</span> {s.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ASR history */}
      {histData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">ASR History</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={histData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Legend />
              <Line type="monotone" dataKey="asr_overall" stroke="#1a56db" name="ASR" dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
