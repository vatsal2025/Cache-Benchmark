import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAlerts, resolveAlert } from "../lib/api";
import { pct } from "../lib/utils";
import { AlertTriangle, CheckCircle, RefreshCw } from "lucide-react";
import { format } from "date-fns";

export default function BacktestMonitorPage() {
  const qc = useQueryClient();
  const { data: alerts = [], isLoading, refetch } = useQuery({
    queryKey: ["alerts"],
    queryFn: fetchAlerts,
    refetchInterval: 60_000,
  });

  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => resolveAlert(alertId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const active = alerts.filter((a: Record<string, unknown>) => a.status === "active");
  const resolved = alerts.filter((a: Record<string, unknown>) => a.status === "resolved");

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backtest Monitor</h1>
          <p className="text-gray-500 mt-1 text-sm">Adversarial adaptation detection — BPAS drift monitoring</p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2"><RefreshCw size={16} /> Refresh</button>
      </div>

      <p className="text-xs text-gray-400 mb-6 bg-blue-50 border border-blue-100 rounded-lg p-3">
        Based on Kozlov et al. (RAID 2020): three adversarial adaptation events were discovered via automated backtesting.
        This monitor alerts when BPAS prevalence in the holdout group shifts by ≥{" "}
        <strong>10 percentage points</strong> from baseline.
      </p>

      {isLoading ? <Spinner /> : (
        <>
          {/* Active alerts */}
          <div className="mb-6">
            <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertTriangle size={18} className="text-red-500" />
              Active Alerts ({active.length})
            </h2>
            {active.length === 0 ? (
              <div className="card text-center py-8 text-gray-400">
                <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
                No active alerts — all holdouts within normal range
              </div>
            ) : (
              <div className="space-y-3">
                {active.map((a: Record<string, unknown>) => (
                  <AlertCard key={a.id as string} alert={a} onResolve={() => resolveMutation.mutate(a.id as string)} resolving={resolveMutation.isPending} />
                ))}
              </div>
            )}
          </div>

          {/* Resolved alerts */}
          {resolved.length > 0 && (
            <div>
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <CheckCircle size={18} className="text-green-500" />
                Resolved Alerts ({resolved.length})
              </h2>
              <div className="space-y-3">
                {resolved.map((a: Record<string, unknown>) => (
                  <AlertCard key={a.id as string} alert={a} onResolve={() => {}} resolving={false} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AlertCard({ alert, onResolve, resolving }: { alert: Record<string, unknown>; onResolve: () => void; resolving: boolean }) {
  const isActive = alert.status === "active";
  return (
    <div className={`card ${isActive ? "border-red-200 bg-red-50" : "border-gray-100"}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`badge ${isActive ? "badge-red" : "badge-green"}`}>{alert.status as string}</span>
            <span className="text-sm font-medium text-gray-900">{alert.nature as string}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Baseline BPAS</p>
              <p className="font-semibold text-gray-900">{pct(alert.baseline_bpas as number)}</p>
            </div>
            <div>
              <p className="text-gray-500">Current BPAS</p>
              <p className={`font-semibold ${isActive ? "text-red-700" : "text-gray-900"}`}>{pct(alert.current_bpas as number)}</p>
            </div>
            <div>
              <p className="text-gray-500">Drift Magnitude</p>
              <p className={`font-semibold ${isActive ? "text-red-700" : "text-gray-900"}`}>{pct(alert.drift_magnitude as number)}</p>
            </div>
            <div>
              <p className="text-gray-500">Detected</p>
              <p className="font-semibold text-gray-900">{format(new Date(alert.created_at as string), "MMM d, HH:mm")}</p>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Experiment ID: {alert.experiment_id as string}</p>
        </div>
        {isActive && (
          <button onClick={onResolve} disabled={resolving} className="btn-secondary text-xs ml-4 flex items-center gap-1">
            <CheckCircle size={14} /> Resolve
          </button>
        )}
      </div>
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
