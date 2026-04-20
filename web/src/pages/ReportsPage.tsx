import { useQuery } from "@tanstack/react-query";
import { fetchExperiments } from "../lib/api";
import { downloadScorecardJson, downloadScorecardPdf } from "../lib/api";
import { pct, statusColor, recColor } from "../lib/utils";
import { Download, FileJson, FileText } from "lucide-react";
import { format } from "date-fns";

export default function ReportsPage() {
  const { data: experiments = [], isLoading } = useQuery({
    queryKey: ["experiments"],
    queryFn: fetchExperiments,
  });

  const complete = experiments.filter((e: Record<string, unknown>) => e.status === "complete" || e.status === "backtesting");

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 mt-1 text-sm">Export scorecards as JSON or PDF · Download raw funnel data</p>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          {complete.length === 0 ? (
            <div className="card text-center py-12 text-gray-400">
              <FileText size={40} className="mx-auto mb-3 opacity-30" />
              <p>No completed experiments yet</p>
              <p className="text-sm mt-1">Run an A/B experiment to generate reports</p>
            </div>
          ) : (
            <div className="space-y-4">
              {complete.map((e: Record<string, unknown>) => (
                <div key={e.id as string} className="card">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold text-gray-900">{e.name as string}</h3>
                        <span className={statusColor(e.status as string)}>{e.status as string}</span>
                      </div>
                      <p className="text-xs text-gray-400">
                        {e.start_date ? format(new Date(e.start_date as string), "MMM d") : "—"} →{" "}
                        {e.end_date ? format(new Date(e.end_date as string), "MMM d, yyyy") : "—"} ·{" "}
                        N={e.n_day_delay as number}d delay
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <a
                        href={downloadScorecardJson(e.id as string)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary flex items-center gap-1.5 text-sm py-2 px-3"
                      >
                        <FileJson size={15} /> JSON
                      </a>
                      <a
                        href={downloadScorecardPdf(e.id as string)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary flex items-center gap-1.5 text-sm py-2 px-3"
                      >
                        <FileText size={15} /> PDF
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-8 card bg-gray-50">
            <h2 className="font-semibold text-gray-900 mb-2">Report Contents</h2>
            <ul className="text-sm text-gray-600 space-y-1 list-disc ml-4">
              <li>Full PAS label distributions (GPAS / BPAS / EPAS) for control and test groups</li>
              <li>Clearance rates per step and population segment</li>
              <li>Attack Success Rates (holistic + modular) with reference baselines from Gao et al.</li>
              <li>Statistical significance tests (z-test, Wald CI, Bonferroni correction)</li>
              <li>Design guideline scores with improvement suggestions</li>
              <li>Auto-generated executive summary (template-based)</li>
              <li>Model version and timestamp for full reproducibility</li>
            </ul>
            <p className="text-xs text-gray-400 mt-3">
              Research basis: Kozlov et al. (RAID 2020), Gao et al. (USENIX SEC 2021)
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
