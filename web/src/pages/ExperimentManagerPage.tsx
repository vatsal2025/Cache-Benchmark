import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchExperiments, fetchCaptchas, createExperiment } from "../lib/api";
import { statusColor } from "../lib/utils";
import { Plus, ChevronRight } from "lucide-react";
import { format } from "date-fns";

export default function ExperimentManagerPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const { data: experiments = [], isLoading } = useQuery({
    queryKey: ["experiments"],
    queryFn: fetchExperiments,
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Experiment Manager</h1>
          <p className="text-gray-500 mt-1 text-sm">A/B test CAPTCHA versions with statistical significance</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Experiment
        </button>
      </div>

      {isLoading ? <Spinner /> : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">N-day Delay</th>
                <th className="px-4 py-3 font-medium">Backtest</th>
                <th className="px-4 py-3 font-medium">Start</th>
                <th className="px-4 py-3 font-medium">End</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {experiments.length === 0 && (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400">No experiments yet.</td></tr>
              )}
              {experiments.map((e: Record<string, unknown>) => (
                <tr key={e.id as string} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/experiments/${e.id}`)}>
                  <td className="px-4 py-3 font-medium text-gray-900">{e.name as string}</td>
                  <td className="px-4 py-3"><span className={statusColor(e.status as string)}>{e.status as string}</span></td>
                  <td className="px-4 py-3 text-gray-500">{e.n_day_delay as number}d</td>
                  <td className="px-4 py-3">{e.backtest_enabled ? "✓" : "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{e.start_date ? format(new Date(e.start_date as string), "MMM d, yyyy") : "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{e.end_date ? format(new Date(e.end_date as string), "MMM d, yyyy") : "—"}</td>
                  <td className="px-4 py-3 text-gray-400"><ChevronRight size={16} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <CreateExperimentModal
          onClose={() => setShowModal(false)}
          onSuccess={() => { setShowModal(false); qc.invalidateQueries({ queryKey: ["experiments"] }); }}
        />
      )}
    </div>
  );
}

function CreateExperimentModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [controlId, setControlId] = useState("");
  const [testId, setTestId] = useState("");
  const [nDay, setNDay] = useState(7);
  const [backtest, setBacktest] = useState(false);
  const [holdoutPct, setHoldoutPct] = useState(5);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: capsData } = useQuery({ queryKey: ["captchas"], queryFn: () => fetchCaptchas() });
  const readyCaps = (capsData?.items || []).filter((c: Record<string, unknown>) => c.status === "ready" || c.status === "complete");

  async function handleSubmit() {
    setError(""); setLoading(true);
    try {
      await createExperiment({ name, control_captcha_id: controlId, test_captcha_id: testId, n_day_delay: nDay, backtest_enabled: backtest, holdout_pct: holdoutPct });
      onSuccess();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create experiment");
    } finally { setLoading(false); }
  }

  const steps = ["Select CAPTCHAs", "Configure", "Review"];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
        {/* Stepper */}
        <div className="flex items-center gap-2 mb-6">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step > i + 1 ? "bg-green-500 text-white" : step === i + 1 ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-400"}`}>
                {step > i + 1 ? "✓" : i + 1}
              </div>
              <span className={`text-sm ${step === i + 1 ? "font-semibold text-gray-900" : "text-gray-400"}`}>{s}</span>
              {i < steps.length - 1 && <div className="flex-1 h-px bg-gray-200 w-8" />}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <Field label="Experiment Name">
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label="Control CAPTCHA">
              <select className="input" value={controlId} onChange={(e) => setControlId(e.target.value)}>
                <option value="">Select…</option>
                {readyCaps.map((c: Record<string, unknown>) => (
                  <option key={c.id as string} value={c.id as string}>{c.name as string} (v{c.version as string})</option>
                ))}
              </select>
            </Field>
            <Field label="Test CAPTCHA">
              <select className="input" value={testId} onChange={(e) => setTestId(e.target.value)}>
                <option value="">Select…</option>
                {readyCaps.filter((c: Record<string, unknown>) => c.id !== controlId).map((c: Record<string, unknown>) => (
                  <option key={c.id as string} value={c.id as string}>{c.name as string} (v{c.version as string})</option>
                ))}
              </select>
            </Field>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <Field label={`N-day Post-Clearance Delay: ${nDay} days`}>
              <input type="range" min={1} max={30} value={nDay} onChange={(e) => setNDay(Number(e.target.value))} className="w-full" />
              <p className="text-xs text-gray-400 mt-1">Accounts are classified {nDay} days after clearing the CAPTCHA (Kozlov et al.)</p>
            </Field>
            <div className="flex items-center gap-3">
              <input type="checkbox" id="bt" checked={backtest} onChange={(e) => setBacktest(e.target.checked)} />
              <label htmlFor="bt" className="text-sm font-medium">Enable Backtest Holdout</label>
            </div>
            {backtest && (
              <Field label={`Holdout %: ${holdoutPct}%`}>
                <input type="range" min={1} max={20} value={holdoutPct} onChange={(e) => setHoldoutPct(Number(e.target.value))} className="w-full" />
              </Field>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3 text-sm">
            <h3 className="font-semibold text-gray-900">Review & Launch</h3>
            {[
              ["Name", name],
              ["Control CAPTCHA", controlId],
              ["Test CAPTCHA", testId],
              ["N-day Delay", `${nDay} days`],
              ["Backtest", backtest ? `Yes (${holdoutPct}% holdout)` : "No"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-500">{k}</span>
                <span className="font-medium text-gray-900 max-w-[60%] truncate text-right">{v}</span>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}

        <div className="flex gap-3 justify-between mt-6">
          <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
          <div className="flex gap-2">
            {step > 1 && <button type="button" onClick={() => setStep(s => s - 1)} className="btn-secondary">Back</button>}
            {step < 3
              ? <button type="button" onClick={() => setStep(s => s + 1)} disabled={step === 1 && (!name || !controlId || !testId)} className="btn-primary">Next</button>
              : <button type="button" onClick={handleSubmit} disabled={loading} className="btn-primary">{loading ? "Creating…" : "Create Experiment"}</button>
            }
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>{children}</div>;
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
