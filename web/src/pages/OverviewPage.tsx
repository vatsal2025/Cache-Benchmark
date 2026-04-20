import { useQuery } from "@tanstack/react-query";
import { fetchOverview } from "../lib/api";
import { pct, fmt, statusColor } from "../lib/utils";
import { Shield, FlaskConical, AlertTriangle, Activity } from "lucide-react";
import { format } from "date-fns";

export default function OverviewPage() {
  const { data, isLoading } = useQuery({ queryKey: ["overview"], queryFn: fetchOverview, refetchInterval: 30_000 });

  if (isLoading) return <PageShell><Spinner /></PageShell>;

  const stats = [
    { label: "CAPTCHAs Evaluated", value: data?.total_captchas_evaluated ?? 0, icon: Shield, color: "text-blue-600 bg-blue-50" },
    { label: "Active Experiments", value: data?.active_experiments ?? 0, icon: FlaskConical, color: "text-purple-600 bg-purple-50" },
    { label: "Active Alerts", value: data?.active_asr_alerts ?? 0, icon: AlertTriangle, color: data?.active_asr_alerts > 0 ? "text-red-600 bg-red-50" : "text-green-600 bg-green-50" },
  ];

  return (
    <PageShell>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
        <p className="text-gray-500 mt-1">CAPTCHA Robustness Benchmark Dashboard</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">{label}</p>
              <div className={`p-2 rounded-lg ${color}`}>
                <Icon size={20} />
              </div>
            </div>
            <p className="text-3xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Attack Runs */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity size={18} /> Recent Attack Runs
          </h2>
          {!data?.recent_attack_runs?.length ? (
            <p className="text-sm text-gray-400">No attack runs yet</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="pb-2">Type</th>
                  <th className="pb-2">ASR</th>
                  <th className="pb-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_attack_runs.map((r: Record<string, unknown>) => (
                  <tr key={r.id as string} className="border-b border-gray-50">
                    <td className="py-2 font-mono text-xs">{r.attack_type as string}</td>
                    <td className="py-2">{pct(r.asr_overall as number)}</td>
                    <td className="py-2 text-gray-400 text-xs">
                      {r.completed_at ? format(new Date(r.completed_at as string), "MMM d") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent Experiments */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FlaskConical size={18} /> Recent Experiments
          </h2>
          {!data?.recent_experiments?.length ? (
            <p className="text-sm text-gray-400">No experiments yet</p>
          ) : (
            <div className="space-y-3">
              {data.recent_experiments.map((e: Record<string, unknown>) => (
                <div key={e.id as string} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{e.name as string}</p>
                    <p className="text-xs text-gray-400">{format(new Date(e.created_at as string), "MMM d, yyyy")}</p>
                  </div>
                  <span className={statusColor(e.status as string)}>{e.status as string}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Research basis */}
      <div className="mt-6 p-4 bg-blue-50 rounded-xl text-sm text-blue-800 border border-blue-100">
        <strong>Research basis:</strong> This platform implements the PAS methodology (Kozlov et al., RAID 2020)
        and attack framework (Gao et al., USENIX SEC 2021). Hover over any metric for its research citation.
      </div>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return <div className="p-8 max-w-7xl mx-auto">{children}</div>;
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
