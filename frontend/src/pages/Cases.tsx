import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, ArrowUpRight, FolderSimple, ShieldCheck, MapPin } from "@phosphor-icons/react";
import {
  Button,
  Card,
  Empty,
  ErrorBox,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  useToast,
  cx,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { ago } from "@/lib/format";

export default function Cases() {
  const { data, error, loading, reload } = useApi(() => api.cases(), []);
  const { user, can } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [ref, setRef] = useState("");
  const [title, setTitle] = useState("");
  const [inv, setInv] = useState(user.full_name);
  const [location, setLocation] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [busy, setBusy] = useState(false);

  const PRESETS = [
    { label: "Nariman Point, Mumbai", loc: "Nariman Point Financial District, Mumbai", lat: 18.9275, lon: 72.8256 },
    { label: "Connaught Place, New Delhi", loc: "Connaught Place Financial & Telecom Center, New Delhi", lat: 28.6328, lon: 77.2197 },
    { label: "Whitefield, Bengaluru", loc: "Whitefield Technology Park & Export Zone, Bengaluru", lat: 12.9698, lon: 77.7499 },
    { label: "HITEC City, Hyderabad", loc: "HITEC City Cyber Towers Precinct, Hyderabad", lat: 17.4474, lon: 78.3762 },
    { label: "Sector 62, Noida", loc: "Sector 62 IT & Media Sub-City, Noida", lat: 28.6270, lon: 77.3653 },
    { label: "Financial District, SF", loc: "Financial District & Montgomery Street Vault, San Francisco", lat: 37.7915, lon: -122.4018 },
    { label: "Canary Wharf, London", loc: "Canary Wharf International Banking Hub, London", lat: 51.5054, lon: -0.0235 },
    { label: "DIFC Gate, Dubai", loc: "Dubai International Financial Centre (DIFC) Gate, Dubai", lat: 25.2048, lon: 55.2708 },
  ];

  async function create() {
    setBusy(true);
    try {
      const c = await api.createCase({
        reference: ref.trim(),
        title: title.trim(),
        investigator: inv.trim() || undefined,
        incident_location: location.trim() || undefined,
        incident_lat: lat ? parseFloat(lat) : undefined,
        incident_lon: lon ? parseFloat(lon) : undefined,
      });
      setOpen(false);
      setLocation("");
      setLat("");
      setLon("");
      nav(`/cases/${c.id}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not create case", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        eyebrow="Case collection"
        title="Cases"
        subtitle="All your cases and their checked files"
        actions={
          can("investigator") && (
            <Button
              variant="primary"
              onClick={() => {
                setInv(user.full_name);
                setOpen(true);
              }}
              className="btn-pill"
            >
              <Plus size={16} weight="bold" />
              New case
            </Button>
          )
        }
      />

      {loading && !data && <Loading label="Loading Cases" />}
      {error && !data && <ErrorBox message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <Card className="card-bento p-8">
          <Empty
            title="No cases yet"
            hint={
              can("investigator")
                ? "Create a case, then upload files to check them."
                : "Ask a team member to create one."
            }
          />
        </Card>
      )}

      {data && data.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((c, idx) => (
            <Link
              key={c.id}
              to={`/cases/${c.id}`}
              className={cx(
                "group relative block p-5 rounded-lg border border-line bg-surface shadow-[var(--shadow-bento)] transition-colors  hover:shadow-[var(--shadow-bento-hover)] hover:border-accent/40 select-none",
                `stagger-${(idx % 5) + 1}`
              )}
            >
              {/* Top Row: Case ID Monospace Label & Timestamp */}
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-bold text-accent">
                  {c.reference}
                </span>
                <span className="text-xs font-semibold text-muted">
                  {ago(c.created_at)}
                </span>
              </div>

              {/* Case Title */}
              <div className="mt-2.5 truncate text-base sm:text-lg font-bold text-ink group-hover:text-accent transition-colors">
                {c.title}
              </div>

              {/* Investigator & Incident Location */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-medium text-muted mt-1">
                <span>Lead: {c.investigator || "Unassigned"}</span>
                {c.incident_location && (
                  <span className="inline-flex items-center gap-1 text-accent font-semibold">
                    <MapPin size={13} weight="fill" className="text-accent shrink-0" />
                    <span className="truncate max-w-[280px]">{c.incident_location}</span>
                  </span>
                )}
              </div>

              {/* Verdict Badges (Clean dots & text, no heavy background pills) */}
              <div className="mt-4 pt-3.5 border-t border-line/60 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="font-bold text-ink text-xs">
                  {c.files} file{c.files === 1 ? "" : "s"}
                </span>

                <div className="flex flex-wrap items-center gap-2">
                  {c.likely_manipulated > 0 && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#EF4444]">
                      <span className="size-1.5 rounded-full bg-[#EF4444]" />
                      {c.likely_manipulated} probably fake
                    </span>
                  )}
                  {c.needs_review > 0 && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#F59E0B]">
                      <span className="size-1.5 rounded-full bg-[#F59E0B]" />
                      {c.needs_review} please check
                    </span>
                  )}
                  {c.consistent > 0 && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#12B981]">
                      <span className="size-1.5 rounded-full bg-[#12B981]" />
                      {c.consistent} looks genuine
                    </span>
                  )}
                </div>

                {/* Arrow up right */}
                <span className="size-6 rounded-full bg-surface2 grid place-items-center text-muted group-hover:bg-[#EEF4FE] group-hover:text-accent group-hover:border-[#D2E2FD] border border-transparent transition shadow-3xs ml-auto">
                  <ArrowUpRight size={12} weight="bold" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* New Case Modal */}
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create a new case"
        footer={
          <>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              variant="primary"
              disabled={busy || !ref.trim() || !title.trim()}
              onClick={create}
            >
              {busy ? "Creating..." : "Create case"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Case ID or number">
            <Input
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              placeholder="e.g. Case 1 or CR-01"
              autoFocus
            />
          </Field>
          <Field label="Case name">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Office Break-In Case"
            />
          </Field>
          <Field label="Assigned person">
            <Input
              value={inv}
              onChange={(e) => setInv(e.target.value)}
              placeholder="e.g. Alex / Sarah"
            />
          </Field>
          <Field label="Location or city">
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Nariman Point Financial District, Mumbai"
            />
          </Field>
          {/* Quick Preset Selector Chips */}
          <div className="space-y-1">
            <span className="text-[10px] font-bold text-muted block">
              Common locations:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {PRESETS.map((p) => (
                <button
                  type="button"
                  key={p.label}
                  onClick={() => {
                    setLocation(p.loc);
                    setLat(p.lat.toString());
                    setLon(p.lon.toString());
                  }}
                  className={cx(
                    "px-2 py-0.5 rounded-lg text-[11px] font-medium border transition cursor-pointer",
                    location === p.loc
                      ? "bg-accent/10 border-accent text-accent font-bold"
                      : "bg-surface2/60 border-line text-muted hover:text-ink hover:border-line/90"
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Latitude (optional)">
              <Input
                type="number"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                placeholder="e.g. 18.9275"
              />
            </Field>
            <Field label="Longitude (optional)">
              <Input
                type="number"
                step="0.0001"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                placeholder="e.g. 72.8256"
              />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}
