import { useState, useEffect } from "react";
import { Check, Copy, Key, QrCode, ShieldCheck, Warning } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import type { TotpSetupResponse } from "@/lib/types";
import { Button, Card, Field, Input, Modal, useToast } from "@/components/ui";

export default function TwoFactorModal({
  open,
  onClose,
  onUpdated,
}: {
  open: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}) {
  const toast = useToast();
  const [data, setData] = useState<TotpSetupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedRecovery, setCopiedRecovery] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const loadSetup = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.setup2FA();
      setData(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load 2FA setup");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadSetup();
      setCode("");
      setPassword("");
    }
  }, [open]);

  const copySecret = () => {
    if (!data?.secret) return;
    navigator.clipboard.writeText(data.secret);
    setCopiedSecret(true);
    toast("Secret copied to clipboard");
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyRecovery = () => {
    if (!data?.recovery_codes) return;
    navigator.clipboard.writeText(data.recovery_codes.join("\n"));
    setCopiedRecovery(true);
    toast("Recovery codes copied to clipboard");
    setTimeout(() => setCopiedRecovery(false), 2000);
  };

  const enable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    setBusy(true);
    setErr("");
    try {
      await api.enable2FA({
        secret: data.secret,
        code,
        recovery_codes: data.recovery_codes,
      });
      toast("Two-factor authentication enabled successfully", "good");
      onUpdated?.();
      onClose();
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  const disable = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.disable2FA({ password });
      toast("Two-factor authentication disabled", "good");
      onUpdated?.();
      onClose();
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Failed to disable 2FA");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Two-Factor Authentication (TOTP)">
      {loading ? (
        <div className="py-8 text-center text-sm text-muted">Generating secure authentication keys...</div>
      ) : !data ? (
        <div className="py-4 text-sm text-bad">{err || "Could not load 2FA configuration"}</div>
      ) : data.totp_enabled ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2.5 rounded-lg border border-good/30 bg-good-soft p-3 text-good">
            <ShieldCheck size={24} className="shrink-0" />
            <div>
              <div className="font-semibold text-sm">Two-Factor Authentication is Active</div>
              <div className="text-xs opacity-90">
                Your account is protected by an authenticator application on sign-in.
              </div>
            </div>
          </div>

          <form onSubmit={disable} className="space-y-3 pt-2">
            <div className="text-xs text-muted">
              To disable 2FA, please enter your current account password:
            </div>
            <Field label="Account Password">
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Current password"
              />
            </Field>
            {err && <div className="text-xs text-bad">{err}</div>}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" onClick={onClose}>
                Close
              </Button>
              <Button variant="danger" disabled={busy || !password}>
                Disable 2FA
              </Button>
            </div>
          </form>
        </div>
      ) : (
        <form onSubmit={enable} className="space-y-4">
          {data.totp_required && (
            <div className="flex items-start gap-2 rounded-lg border border-warn/30 bg-warn-soft p-2.5 text-xs text-warn">
              <Warning size={18} className="shrink-0 mt-0.5" />
              <div>
                <strong>Mandatory Requirement:</strong> Two-factor authentication is required for {data.role} accounts.
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-4 items-center">
            {data.qr_code && (
              <div className="shrink-0 rounded-lg border border-line bg-white p-2">
                <img src={data.qr_code} alt="TOTP QR Code" className="size-36" />
              </div>
            )}
            <div className="space-y-2 text-xs flex-1">
              <p className="text-muted">
                1. Scan this QR code with <strong>Google Authenticator</strong>, <strong>Authy</strong>, or your preferred authenticator app.
              </p>
              <div>
                <span className="text-muted">Or enter the manual setup key:</span>
                <div className="mt-1 flex items-center gap-1.5 font-mono text-ink bg-surface2 px-2.5 py-1.5 rounded border border-line">
                  <span className="select-all tracking-wider font-semibold text-xs">{data.secret}</span>
                  <button
                    type="button"
                    onClick={copySecret}
                    className="ml-auto text-muted hover:text-ink"
                    title="Copy secret"
                  >
                    {copiedSecret ? <Check size={14} className="text-good" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-surface2 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold">Emergency Recovery Codes</span>
              <button
                type="button"
                onClick={copyRecovery}
                className="flex items-center gap-1 text-[11px] text-accent hover:underline font-medium"
              >
                {copiedRecovery ? <Check size={12} className="text-good" /> : <Copy size={12} />}
                {copiedRecovery ? "Copied" : "Copy all"}
              </button>
            </div>
            <p className="text-[11px] text-muted">
              Keep these codes in a safe place. Each code can be used once if you lose your authenticator.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 font-mono text-xs">
              {data.recovery_codes.map((rc, idx) => (
                <div key={idx} className="bg-surface rounded px-2 py-1 text-center border border-line select-all">
                  {rc}
                </div>
              ))}
            </div>
          </div>

          <Field label="Verification Code" hint="Enter the 6-digit code currently shown on your app">
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="000000"
              autoFocus
              required
              className="font-mono text-center tracking-widest text-lg"
              maxLength={6}
            />
          </Field>

          {err && <div className="text-xs text-bad">{err}</div>}

          <div className="flex justify-end gap-2 pt-2 border-t border-line">
            <Button type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" disabled={busy || code.trim().length !== 6}>
              Verify & Enable 2FA
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
