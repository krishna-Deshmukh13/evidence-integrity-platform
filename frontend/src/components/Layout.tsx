import Logo from "@/components/Logo";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  CaretLeft, CaretRight, CheckCircle, ClockCounterClockwise,
  Compass, FileText, FolderSimple, Gear, Graph, House, List, MagnifyingGlass,
  Moon, Queue, ShieldCheck, SignOut, SpeakerHigh, Sun, UsersThree,
  ShieldCheckered, Scales
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { useTheme } from "@/lib/theme";
import { cx } from "./ui";
import GlobalShortcuts from "./GlobalShortcuts";
import TwoFactorModal from "./misc/TwoFactorModal";
import AssistantWidget from "./assistant/AssistantWidget";

interface NavItem {
  to: string;
  label: string;
  icon: any;
  end?: boolean;
  min?: "admin" | "investigator" | "viewer";
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const SECTIONS: NavSection[] = [
  {
    title: "Workspace",
    items: [
      { to: "/", label: "Home", icon: House, end: true },
      { to: "/cases", label: "Cases", icon: FolderSimple },
      { to: "/tasks", label: "Waiting for review", icon: CheckCircle },
      { to: "/search", label: "Search files", icon: MagnifyingGlass },
    ],
  },
  {
    title: "Checks and Tools",
    items: [
      { to: "/graph", label: "Connected files", icon: Graph },
      { to: "/map", label: "Map", icon: Compass },
      { to: "/audio-forensics", label: "Voice check", icon: SpeakerHigh },
      { to: "/timeline", label: "Timeline", icon: ClockCounterClockwise },
      { to: "/queue", label: "Waiting list", icon: Queue },
    ],
  },
  {
    title: "Reports and Safety",
    items: [
      { to: "/reports", label: "Reports", icon: FileText },
      { to: "/chargesheet", label: "Draft Charge Sheet / Case Summary", icon: Scales },
      { to: "/integrity", label: "File safety", icon: ShieldCheckered },
    ],
  },
  {
    title: "Team and Settings",
    items: [
      { to: "/activity", label: "Activity log", icon: ClockCounterClockwise, min: "investigator" },
      { to: "/users", label: "Team members", icon: UsersThree, min: "admin" },
      { to: "/settings", label: "Settings", icon: Gear, min: "admin" },
    ],
  },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, signOut, can } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();
  const loc = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [twoFactorOpen, setTwoFactorOpen] = useState(false);
  const [q, setQ] = useState("");

  // Live custody monitor status
  const custodyState = useApi(() => api.custodyStatus(), []);

  useEffect(() => setMobile(false), [loc.pathname]);

  const initials = user.full_name
    ? user.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : "KD";

  const side = (
    <nav className="flex h-full flex-col justify-between select-none p-3">
      <div className="flex flex-col gap-4 overflow-y-auto">
        {/* Brand Header */}
        <Link
          to="/"
          className={cx(
            "flex items-center gap-2.5 px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors",
            collapsed ? "justify-center" : ""
          )}
        >
          {collapsed ? (
            <Logo variant="mark" size={28} />
          ) : (
            <div className="flex items-center gap-2.5">
              <Logo variant="mark" size={30} />
              <div className="flex flex-col">
                <span className="font-bold text-sm text-slate-900 dark:text-slate-100 leading-tight">
                  Evidence Integrity
                </span>
                <span className="text-[11px] text-slate-500 leading-tight mt-0.5">
                  Digital evidence, verified
                </span>
              </div>
            </div>
          )}
        </Link>

        {/* Grouped Navigation */}
        <div className="flex flex-col gap-3">
          {SECTIONS.map((sec) => {
            const visibleItems = sec.items.filter((item) => !item.min || can(item.min));
            if (visibleItems.length === 0) return null;
            return (
              <div key={sec.title} className="flex flex-col gap-0.5">
                {!collapsed && (
                  <div className="px-2.5 py-1 text-xs font-semibold text-slate-400 dark:text-slate-500">
                    {sec.title}
                  </div>
                )}
                {visibleItems.map((n) => (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    end={n.end}
                    title={n.label}
                    className={({ isActive }) =>
                      cx(
                        "flex items-center rounded-md text-sm font-medium transition-colors",
                        collapsed
                          ? "size-9 justify-center p-0"
                          : "gap-2.5 px-2.5 py-1.5",
                        isActive
                          ? "bg-blue-50 text-blue-700 font-semibold dark:bg-slate-800 dark:text-blue-400"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <n.icon
                          size={17}
                          className={cx(
                            "shrink-0",
                            isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-500"
                          )}
                        />
                        {!collapsed && (
                          <span className="truncate flex-1">{n.label}</span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Status Box */}
      {!collapsed && (
        <div
          onClick={() => nav("/integrity")}
          className={cx(
            "mt-3 cursor-pointer rounded-md border p-2.5 text-xs transition-colors",
            (custodyState.data?.broken ?? 0) > 0
              ? "border-red-300 bg-red-50 text-red-800 hover:bg-red-100 dark:bg-red-950/40 dark:border-red-800 dark:text-red-300"
              : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300"
          )}
          title="Click to open File safety"
        >
          <div className="flex items-center gap-2 font-semibold">
            <span
              className={cx(
                "size-2 rounded-full shrink-0",
                (custodyState.data?.broken ?? 0) > 0 ? "bg-red-600" : "bg-emerald-600"
              )}
            />
            <span className="truncate">
              {(custodyState.data?.broken ?? 0) > 0
                ? `${custodyState.data.broken} file${custodyState.data.broken > 1 ? "s" : ""} altered`
                : `All ${custodyState.data?.total ?? 40} files unchanged`}
            </span>
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">
            {(custodyState.data?.broken ?? 0) > 0
              ? "Integrity check: Issue detected"
              : "Integrity check: Up to date"}
          </div>
        </div>
      )}
    </nav>
  );

  return (
    <div className="flex h-full overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {/* Standard Left Docked Sidebar */}
      <aside
        className={cx(
          "hidden shrink-0 border-r border-slate-200 bg-white md:flex md:flex-col dark:bg-slate-900 dark:border-slate-800 transition-[width] duration-150",
          collapsed ? "w-16" : "w-60"
        )}
      >
        {side}
      </aside>

      {/* Mobile Drawer */}
      {mobile && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMobile(false)} />
          <aside className="relative h-full w-64 border-r border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-800">
            {side}
          </aside>
        </div>
      )}

      {/* Main Container */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Header Bar */}
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 md:px-6 dark:bg-slate-900 dark:border-slate-800">
          <div className="flex items-center gap-2.5 flex-1 max-w-lg">
            <button
              id="sidebar-toggle"
              className="hidden size-8 place-items-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900 md:grid transition-colors cursor-pointer dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
              onClick={() => setCollapsed((c) => !c)}
              aria-label="Toggle sidebar"
            >
              {collapsed ? <CaretRight size={14} /> : <CaretLeft size={14} />}
            </button>
            <button
              className="size-8 grid place-items-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900 md:hidden cursor-pointer dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
              onClick={() => setMobile(true)}
              aria-label="Open menu"
            >
              <List size={18} />
            </button>

            {/* Global Search Input */}
            <form
              className="relative w-full max-w-sm"
              onSubmit={(e) => {
                e.preventDefault();
                if (q.trim()) nav(`/search?q=${encodeURIComponent(q.trim())}`);
              }}
            >
              <MagnifyingGlass size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="global-search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search files or cases..."
                className="h-8.5 w-full rounded-md border border-slate-300 bg-white pl-8 pr-3 text-xs sm:text-sm text-slate-900 placeholder-slate-400 outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100"
              />
            </form>
          </div>

          {/* Right Header Status & User Profile */}
          <div className="flex items-center gap-2">
            {/* Alerts Button */}
            <button
              onClick={() => nav("/activity")}
              className="h-8 px-2.5 rounded-md border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer dark:bg-slate-850 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              title="Recent updates & alerts"
            >
              Alerts
            </button>

            {/* 2FA Shield Button */}
            <button
              onClick={() => setTwoFactorOpen(true)}
              className="size-8 grid place-items-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer dark:bg-slate-850 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label="Two-factor authentication settings"
              title={user.totp_enabled ? "2FA Enabled" : "2FA Settings"}
            >
              <ShieldCheck size={16} className={user.totp_enabled ? "text-emerald-600" : ""} />
            </button>

            {/* Theme Toggle */}
            <button
              onClick={toggle}
              className="size-8 grid place-items-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer dark:bg-slate-850 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label="Toggle theme"
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            {/* User Profile */}
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-800">
              <div
                className="grid size-8 place-items-center rounded-md bg-slate-800 text-white text-xs font-semibold cursor-pointer"
                title={`${user.full_name} (${user.role})`}
                onClick={() => nav("/users")}
              >
                {initials}
              </div>
              <div className="hidden sm:block text-left cursor-pointer" onClick={() => nav("/users")}>
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-tight">{user.full_name}</div>
                <div className="text-[11px] text-slate-500 capitalize leading-tight">{user.role}</div>
              </div>
              <button
                onClick={signOut}
                className="size-7 grid place-items-center rounded text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer dark:hover:bg-red-950/40"
                aria-label="Sign out"
                title="Sign out"
              >
                <SignOut size={15} />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content Area */}
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1280px] p-4 sm:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>

      {/* Modals & Tools */}
      <TwoFactorModal
        open={twoFactorOpen}
        onClose={() => setTwoFactorOpen(false)}
        onUpdated={() => window.location.reload()}
      />
      <GlobalShortcuts />
      <AssistantWidget />
    </div>
  );
}
