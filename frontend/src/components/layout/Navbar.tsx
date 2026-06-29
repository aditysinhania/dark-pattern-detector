import { Bell, User } from "lucide-react";
import { useAuthStore } from "../../store/auth.store";

export function Navbar() {
  const { user } = useAuthStore();

  return (
    <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-4">
        <button className="p-2 text-gray-400 hover:text-gray-100 hover:bg-gray-800 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500/20 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-brand-400" />
          </div>
          <div className="text-sm">
            <p className="text-gray-100 font-medium">{user?.full_name}</p>
            <p className="text-gray-500 text-xs">{user?.email}</p>
          </div>
        </div>
      </div>
    </header>
  );
}