import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchCaptchas, submitCaptcha, uploadAsset } from "../lib/api";
import { statusColor, pct } from "../lib/utils";
import { Plus, Upload, Search, RefreshCw, ChevronRight } from "lucide-react";
import { format } from "date-fns";

const CAPTCHA_TYPES = ["visual_reasoning", "image_object", "text_based", "slider", "adversarial"];

export default function CaptchaLibraryPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  const { data, isLoading, refetch } = useQuery({ queryKey: ["captchas"], queryFn: () => fetchCaptchas() });

  const captchas = (data?.items || []).filter((c: Record<string, unknown>) =>
    (c.name as string).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CAPTCHA Library</h1>
          <p className="text-gray-500 mt-1">{data?.total ?? 0} CAPTCHAs submitted</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2">
            <RefreshCw size={16} /> Refresh
          </button>
          <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Submit CAPTCHA
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
        <input
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm"
          placeholder="Search CAPTCHAs…"
          value={search} onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? <Spinner /> : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Version</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Category Diversity</th>
                <th className="px-4 py-3 font-medium">Occlusion</th>
                <th className="px-4 py-3 font-medium">Variation</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {captchas.length === 0 && (
                <tr><td colSpan={9} className="text-center py-8 text-gray-400">No CAPTCHAs yet. Submit your first one →</td></tr>
              )}
              {captchas.map((c: Record<string, unknown>) => {
                const scores = c.design_guideline_scores as Record<string, number>;
                return (
                  <tr key={c.id as string} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/captchas/${c.id}`)}>
                    <td className="px-4 py-3 font-medium text-gray-900">{c.name as string}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{c.captcha_type as string}</td>
                    <td className="px-4 py-3 text-gray-500">{c.version as string}</td>
                    <td className="px-4 py-3"><span className={statusColor(c.status as string)}>{c.status as string}</span></td>
                    <td className="px-4 py-3"><ScoreBar value={scores?.category_diversity ?? 0} /></td>
                    <td className="px-4 py-3"><ScoreBar value={scores?.occlusion_score ?? 0} /></td>
                    <td className="px-4 py-3"><ScoreBar value={scores?.variation_density ?? 0} /></td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{format(new Date(c.created_at as string), "MMM d, yyyy")}</td>
                    <td className="px-4 py-3 text-gray-400"><ChevronRight size={16} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showModal && <SubmitCaptchaModal onClose={() => setShowModal(false)} onSuccess={() => { setShowModal(false); qc.invalidateQueries({ queryKey: ["captchas"] }); }} />}
    </div>
  );
}

function ScoreBar({ value }: { value: number }) {
  const pctVal = Math.round(value * 100);
  const color = value >= 0.7 ? "bg-green-500" : value >= 0.4 ? "bg-yellow-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-gray-100 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pctVal}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pctVal}%</span>
    </div>
  );
}

function SubmitCaptchaModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0");
  const [type, setType] = useState("visual_reasoning");
  const [catSize, setCatSize] = useState(50);
  const [occlusion, setOcclusion] = useState(false);
  const [occType, setOccType] = useState("partial");
  const [varCount, setVarCount] = useState(2);
  const [tags, setTags] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const res = await submitCaptcha({
        name, version, type,
        metadata: { category_set_size: catSize, occlusion_enabled: occlusion, occlusion_type: occlusion ? occType : "none", variation_count: varCount },
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      if (file) await uploadAsset(res.captcha_id, file);
      onSuccess();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Submission failed");
    } finally { setLoading(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold mb-4">Submit CAPTCHA</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} required /></Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Version"><input className="input" value={version} onChange={(e) => setVersion(e.target.value)} /></Field>
            <Field label="Type">
              <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
                {CAPTCHA_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Category Set Size">
            <input type="number" className="input" value={catSize} onChange={(e) => setCatSize(Number(e.target.value))} min={0} />
          </Field>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="occ" checked={occlusion} onChange={(e) => setOcclusion(e.target.checked)} />
            <label htmlFor="occ" className="text-sm font-medium">Occlusion Enabled</label>
            {occlusion && (
              <select className="input flex-1" value={occType} onChange={(e) => setOccType(e.target.value)}>
                {["partial", "full"].map((t) => <option key={t}>{t}</option>)}
              </select>
            )}
          </div>
          <Field label="Variation Count">
            <input type="number" className="input" value={varCount} onChange={(e) => setVarCount(Number(e.target.value))} min={0} max={10} />
          </Field>
          <Field label="Tags (comma separated)">
            <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="production, experimental" />
          </Field>
          <Field label="Asset File (optional)">
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-brand-400 transition-colors"
            >
              <Upload size={24} className="mx-auto text-gray-400 mb-1" />
              <p className="text-sm text-gray-500">{file ? file.name : "Click or drag to upload CAPTCHA assets"}</p>
            </div>
            <input ref={fileRef} type="file" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </Field>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary">{loading ? "Submitting…" : "Submit"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
