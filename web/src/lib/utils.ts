import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function pct(v: number | null | undefined, digits = 1) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

export function fmt(v: number | null | undefined, digits = 3) {
  if (v == null) return "—";
  return v.toFixed(digits);
}

export function statusColor(status: string) {
  const map: Record<string, string> = {
    complete: "badge-green",
    ready: "badge-green",
    running: "badge-blue",
    analysing: "badge-blue",
    pending: "badge-yellow",
    processing: "badge-yellow",
    draft: "badge-gray",
    failed: "badge-red",
    backtesting: "badge-blue",
    monitoring: "badge-green",
    alert: "badge-red",
  };
  return map[status] || "badge-gray";
}

export function recColor(rec: string) {
  if (rec === "LAUNCH_TEST_VARIANT") return "bg-green-100 text-green-800 border-green-300";
  if (rec === "KEEP_CONTROL") return "bg-red-100 text-red-800 border-red-300";
  return "bg-yellow-100 text-yellow-800 border-yellow-300";
}

export function pvalColor(p: number | null | undefined) {
  if (p == null) return "text-gray-500";
  if (p < 0.05) return "text-green-700 font-semibold";
  if (p < 0.10) return "text-yellow-700 font-semibold";
  return "text-red-700 font-semibold";
}
