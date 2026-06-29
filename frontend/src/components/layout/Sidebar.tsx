import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  History,
  FileText,
  User,
  Settings,
  Shield,
  LogOut,
} from "lucide-react";
import { clsx } from "clsx";
import { useLogout } from "../../hooks/useAuth";

const navItems = [
  { to: "/dashboard",  icon: LayoutDashboard, label: "Dashboard" },
  { to: "/scanner",    icon: Search,           label: "Scanner" },
  { to: "/history",    icon: History,          label: "History" },
  { to: "/reports",    icon: FileText,         label: "Reports" },
  { to: "/profile",    icon: User,             label: "Profile" },
  { to: "/settings",   icon: Settings,         label: "Settings" },
];

export function Sidebar() {
  const logout = useLogout();

  return (
    <aside className="w-64 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-bold text-white text-sm">Dark Pattern</p>
            <p className="text-xs text-gray-500">Detector</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-brand-500/10 text-brand-400 font-medium"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
              )
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-red-400 transition-colors w-full"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}