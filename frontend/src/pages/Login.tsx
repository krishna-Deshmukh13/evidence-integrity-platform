import Logo from "@/components/Logo";
import { useState } from "react";
import {
  ShieldCheck,
  Lock,
  User,
  Key,
  Eye,
  EyeSlash,
  CircleNotch,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import type { User as UserType } from "@/lib/types";

export default function Login({
  needsSetup,
  onDone,
}: {
  needsSetup: boolean;
  onDone: (u: UserType) => void;
}) {
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Handle form submission (preserving exact existing API contracts and authentication behavior)
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (needsSetup) {
        const u = await api.setup({ username, full_name: fullName, password });
        onDone(u);
      } else {
        const res = await api.login({
          username,
          password,
          code: requires2FA ? code : undefined,
        });
        if (res.requires_2fa) {
          setRequires2FA(true);
          setCode("");
        } else {
          onDone(res as UserType);
        }
      }
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-4 sm:p-6 text-slate-800">
      {/* Centered Small Login Card */}
      <div className="w-full max-w-[380px]">
        <div className="bg-white border border-slate-200 rounded-lg p-6 sm:p-8 shadow-xs">
          {/* Card Header */}
          <div className="text-center mb-6">
            <Logo variant="mark" size={48} className="mx-auto mb-3 shadow-xs" />
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {needsSetup
                ? "Create Admin Account"
                : requires2FA
                ? "Two-Factor Verification"
                : "Sign in"}
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-500">
              {needsSetup
                ? "Set up the initial system administrator account."
                : requires2FA
                ? "Enter the 6-digit TOTP code from your authenticator."
                : "Evidence Integrity — Digital evidence, verified"}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={submit} className="space-y-4">
            {!requires2FA ? (
              <>
                {/* Full Name field for initial setup */}
                {needsSetup && (
                  <div>
                    <label
                      htmlFor="fullName"
                      className="block text-xs font-semibold text-slate-700 mb-1.5"
                    >
                      Full name
                    </label>
                    <div className="relative">
                      <User
                        size={16}
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                      />
                      <input
                        id="fullName"
                        name="fullName"
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required
                        placeholder="Full name"
                        className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:ring-1 focus:ring-slate-900 outline-none transition-colors"
                      />
                    </div>
                  </div>
                )}

                {/* Username Field */}
                <div>
                  <label
                    htmlFor="username"
                    className="block text-xs font-semibold text-slate-700 mb-1.5"
                  >
                    Username
                  </label>
                  <div className="relative">
                    <User
                      size={16}
                      className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      id="username"
                      name="username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoFocus
                      required
                      autoComplete="username"
                      placeholder="Enter username"
                      className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:ring-1 focus:ring-slate-900 outline-none transition-colors"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label
                      htmlFor="password"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Password
                    </label>
                    {needsSetup && (
                      <span className="text-[11px] text-slate-400">
                        At least 8 characters
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <Lock
                      size={16}
                      className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={needsSetup ? 8 : 1}
                      autoComplete={needsSetup ? "new-password" : "current-password"}
                      placeholder="Enter password"
                      className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-10 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:ring-1 focus:ring-slate-900 outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                    >
                      {showPassword ? <EyeSlash size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* Two-Factor Authentication TOTP Input */
              <div>
                <label
                  htmlFor="code"
                  className="block text-xs font-semibold text-slate-700 mb-1.5"
                >
                  Authentication code
                </label>
                <div className="relative">
                  <Key
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />
                  <input
                    id="code"
                    name="code"
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    autoFocus
                    required
                    placeholder="000000"
                    autoComplete="one-time-code"
                    className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-center font-mono text-base tracking-widest text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:ring-1 focus:ring-slate-900 outline-none transition-colors"
                  />
                </div>
                <p className="mt-1.5 text-xs text-slate-500">
                  Open your registered authenticator app for the 6-digit code.
                </p>
              </div>
            )}

            {/* Error Message */}
            {err && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700"
              >
                <WarningCircle size={16} weight="fill" className="shrink-0 text-red-500 mt-0.5" />
                <span>{err}</span>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={busy}
                className="w-full h-10 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold transition-colors disabled:opacity-60 cursor-pointer flex items-center justify-center gap-2 shadow-xs"
              >
                {busy ? (
                  <>
                    <CircleNotch size={16} className="animate-spin" />
                    <span>
                      {needsSetup
                        ? "Creating Account..."
                        : requires2FA
                        ? "Verifying Token..."
                        : "Signing in..."}
                    </span>
                  </>
                ) : (
                  <span>
                    {needsSetup
                      ? "Create Admin Account"
                      : requires2FA
                      ? "Verify & Sign in"
                      : "Sign in"}
                  </span>
                )}
              </button>

              {/* Cancel Button for 2FA Mode */}
              {requires2FA && (
                <button
                  type="button"
                  onClick={() => {
                    setRequires2FA(false);
                    setCode("");
                    setErr("");
                  }}
                  className="mt-2 w-full text-center text-xs text-slate-500 hover:text-slate-800 py-1 transition-colors cursor-pointer"
                >
                  Cancel and return to sign in
                </button>
              )}
            </div>

            {/* Security Note */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-center gap-1.5 text-xs text-slate-500 font-medium">
              <ShieldCheck size={15} weight="fill" className="text-emerald-600 shrink-0" />
              <span>Secured with cryptographic integrity checks</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
