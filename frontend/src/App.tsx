// Router + session bootstrap: Clean Light Pro with animated transitions and full feature routes.
import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import type { User } from "@/lib/types";
import Layout from "@/components/Layout";
import { Loading, ToastProvider } from "@/components/ui";

// Pages
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Cases from "@/pages/Cases";
import Case from "@/pages/Case";
import Evidence from "@/pages/Evidence";
import Search from "@/pages/Search";
import Compare from "@/pages/Compare";
import Activity from "@/pages/Activity";
import Users from "@/pages/Users";
import HowItWorks from "@/pages/HowItWorks";
import Verify from "@/pages/Verify";
import NotFound from "@/pages/NotFound";

// New Pages (Matches Clean Light Pro PDF Feature Spec)
import MyTasksPage from "@/pages/MyTasksPage";
import IntelligenceGraph from "@/pages/IntelligenceGraph";
import TimelinePage from "@/pages/TimelinePage";
import AnalysisQueuePage from "@/pages/AnalysisQueuePage";
import CertificatesPage from "@/pages/CertificatesPage";
import ReportsCenterPage from "@/pages/ReportsCenterPage";
import IntegrityMonitorPage from "@/pages/IntegrityMonitorPage";
import SettingsPage from "@/pages/SettingsPage";
import GlossaryPage from "@/pages/GlossaryPage";

// Forensic Media & Intelligence Pages
import TacticalMapPage from "@/pages/TacticalMapPage";
import AudioForensicsPage from "@/pages/AudioForensicsPage";

// Prize-Winning Feature Additions
import ChargeSheetPage from "@/pages/ChargeSheetPage";

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined); // undefined = still checking
  const [needsSetup, setNeedsSetup] = useState(false);

  const boot = useCallback(async () => {
    try {
      setUser(await api.me());
    } catch {
      try {
        setNeedsSetup((await api.authStatus()).needs_setup);
      } catch {
        /* server down */
      }
      setUser(null);
    }
  }, []);

  useEffect(() => {
    boot();
    const h = () => setUser(null);
    window.addEventListener("auth:expired", h);
    return () => window.removeEventListener("auth:expired", h);
  }, [boot]);

  // Support public unauthenticated verification portal
  if (window.location.pathname === "/verify") {
    return (
      <ToastProvider>
        <Verify />
      </ToastProvider>
    );
  }

  if (user === undefined) return <Loading label="Starting Evidence Platform" />;
  if (user === null) return <Login needsSetup={needsSetup} onDone={setUser} />;

  return (
    <ToastProvider>
      <AuthProvider user={user} onSignOut={() => { setUser(null); boot(); }}>
        <BrowserRouter>
          <Layout>
            <Routes>
              {/* Workspace */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:id" element={<Case />} />
              <Route path="/evidence/:id" element={<Evidence />} />
              <Route path="/tasks" element={<MyTasksPage />} />
              <Route path="/search" element={<Search />} />
              <Route path="/compare" element={<Compare />} />

              {/* Analysis */}
              <Route path="/graph" element={<IntelligenceGraph />} />
              <Route path="/map" element={<TacticalMapPage />} />
              <Route path="/audio-forensics" element={<AudioForensicsPage />} />
              <Route path="/photo-video-check" element={<Navigate to="/" replace />} />
              <Route path="/video-forensics" element={<Navigate to="/" replace />} />
              <Route path="/media-check" element={<Navigate to="/" replace />} />
              <Route path="/document-forensics" element={<Navigate to="/" replace />} />
              <Route path="/live-mirror" element={<Navigate to="/" replace />} />
              <Route path="/url-debunker" element={<Navigate to="/" replace />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/queue" element={<AnalysisQueuePage />} />

              {/* Legal & Reports */}
              <Route path="/certificates" element={<CertificatesPage />} />
              <Route path="/reports" element={<ReportsCenterPage />} />
              <Route path="/chargesheet" element={<ChargeSheetPage />} />
              <Route path="/chargesheet/:id" element={<ChargeSheetPage />} />
              <Route path="/integrity" element={<IntegrityMonitorPage />} />

              {/* Admin */}
              <Route path="/activity" element={<Activity />} />
              <Route path="/users" element={<Users />} />
              <Route path="/settings" element={<SettingsPage />} />

              {/* Help & Portal */}
              <Route path="/glossary" element={<GlossaryPage />} />
              <Route path="/how-it-works" element={<HowItWorks />} />
              <Route path="/verify" element={<Verify />} />

              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
}
