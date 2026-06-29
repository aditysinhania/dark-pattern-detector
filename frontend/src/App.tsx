import {
  BrowserRouter, Routes, Route, Navigate, Outlet
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "./components/layout/Sidebar";
import { Navbar } from "./components/layout/Navbar";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { LoginPage }      from "./pages/auth/LoginPage";
import { RegisterPage }   from "./pages/auth/RegisterPage";
import { DashboardPage }  from "./pages/dashboard/DashboardPage";
import { ScannerPage }    from "./pages/scanner/ScannerPage";
import { ScanResultPage } from "./pages/scanner/ScanResultPage";
import { HistoryPage }    from "./pages/history/HistoryPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 30, // 30 seconds
    },
  },
});

function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/scanner"   element={<ScannerPage />} />
              <Route path="/scans/:scanId" element={<ScanResultPage />} />
              <Route path="/history"   element={<HistoryPage />} />
            </Route>
          </Route>

          {/* Default redirect */}
          <Route path="/"  element={<Navigate to="/dashboard" replace />} />
          <Route path="*"  element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}