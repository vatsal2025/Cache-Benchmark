import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../lib/store";
import {
  LayoutDashboard, Shield, Swords, FlaskConical,
  Activity, FileText, LogOut, ShieldCheck
} from "lucide-react";
import { cn } from "../lib/utils";

const navItems = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/captchas", label: "CAPTCHA Library", icon: Shield },
  { to: "/experiments", label: "Experiments", icon: FlaskConical },
  { to: "/backtests", label: "Backtest Monitor", icon: Activity },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function Layout() {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-brand-500" size={24} />
            <div>
              <p className="font-bold text-gray-900 text-sm leading-tight">CAPTCHA Benchmark</p>
              <p className="text-xs text-gray-500">Robustness Dashboard</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <button
            onClick={() => { logout(); navigate("/login"); }}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
