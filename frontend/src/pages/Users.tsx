import { useState } from "react";
import { Plus } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { ago } from "@/lib/format";
import { Badge, Button, Card, Empty, ErrorBox, Loading, PageHeader, Select, useToast } from "@/components/ui";
import { NewAccountModal, ResetPasswordModal } from "@/components/misc/UserModals";
import type { Role, UserAdmin } from "@/lib/types";

const ROLES: { role: Role; title: string; text: string }[] = [
  { role: "admin", title: "Admin", text: "Everything, plus accounts and deleting." },
  { role: "investigator", title: "Investigator", text: "Cases, uploads, review, notes." },
  { role: "viewer", title: "Viewer", text: "Read, search, compare, export." },
];
const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((s) => s[0]?.toUpperCase()).join("") || "?";

export default function Users() {
  const { user, can } = useAuth();
  const toast = useToast();
  const isAdmin = can("admin");
  const state = useApi(() => (isAdmin ? api.users() : Promise.resolve([] as UserAdmin[])), [isAdmin]);
  const [creating, setCreating] = useState(false);
  const [reset, setReset] = useState<UserAdmin | null>(null);

  if (!isAdmin) return <Empty title="Admins only" hint="You need an administrator account to manage users." />;
  const users = state.data ?? null;
  const count = (r: Role) => (users ?? []).filter((u) => u.role === r).length;

  const patch = async (u: UserAdmin, b: { role?: Role; is_active?: boolean }) => {
    try { await api.patchUser(u.id, b); toast("Saved"); state.reload(); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
  };

  const handleReset2FA = async (u: UserAdmin) => {
    if (!confirm(`Are you sure you want to reset two-factor authentication for ${u.full_name}? They will be required to re-enrol on their next login.`)) return;
    try {
      await api.reset2FA(u.id);
      toast(`2FA reset for ${u.full_name}`, "good");
      state.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to reset 2FA", "bad");
    }
  };

  return (
    <div>
      <PageHeader title="Users" subtitle={users ? `${count("admin")} admin, ${count("investigator")} investigator, ${count("viewer")} viewers` : undefined}
        actions={<Button variant="primary" onClick={() => setCreating(true)}><Plus size={16} />New account</Button>} />
      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {ROLES.map((r) => (
          <Card key={r.role} className="p-4"><div className="font-semibold">{r.title}</div><div className="mt-1 text-muted">{r.text}</div></Card>
        ))}
      </div>
      {state.error ? <ErrorBox message={String(state.error)} onRetry={state.reload} /> : !users ? <Loading /> : users.length === 0 ? (
        <Card className="p-8">
          <Empty title="No user accounts found" hint="Click 'New account' to provision investigators or administrators." action={<Button variant="primary" onClick={() => setCreating(true)}><Plus size={16} />New account</Button>} />
        </Card>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead className="border-b border-line text-xs text-muted">
              <tr>
                <th className="px-4 py-2">User</th>
                <th className="px-2 py-2">Username</th>
                <th className="px-2 py-2">Role</th>
                <th className="px-2 py-2">2FA Status</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Last sign-in</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => {
                const me = u.id === user?.id;
                return (
                  <tr key={u.id}>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <span className="flex size-8 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">{initials(u.full_name)}</span>
                        <span className="font-medium">{u.full_name}{me && <span className="ml-1 text-muted">(you)</span>}</span>
                      </div>
                    </td>
                    <td className="px-2 py-2.5 text-muted">{u.username}</td>
                    <td className="px-2 py-2.5">
                      <Select className="w-36" value={u.role} disabled={me} onChange={(e) => patch(u, { role: e.target.value as Role })}>
                        <option value="admin">Admin</option><option value="investigator">Investigator</option><option value="viewer">Viewer</option>
                      </Select>
                    </td>
                    <td className="px-2 py-2.5">
                      <Badge tone={u.totp_enabled ? "good" : u.role !== "viewer" ? "warn" : "muted"}>
                        {u.totp_enabled ? "Active" : u.role !== "viewer" ? "Required" : "Off"}
                      </Badge>
                    </td>
                    <td className="px-2 py-2.5"><Badge tone={u.is_active ? "good" : "muted"}>{u.is_active ? "Active" : "Disabled"}</Badge></td>
                    <td className="px-2 py-2.5 text-muted">{u.last_login_at ? ago(u.last_login_at) : "Never"}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex justify-end gap-2">
                        {u.totp_enabled && (
                          <Button size="sm" onClick={() => handleReset2FA(u)} title="Reset TOTP authentication for this user">
                            Reset 2FA
                          </Button>
                        )}
                        <Button size="sm" onClick={() => setReset(u)}>Reset password</Button>
                        <Button size="sm" disabled={me} onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
      <NewAccountModal open={creating} onClose={() => setCreating(false)} onDone={state.reload} />
      <ResetPasswordModal user={reset} onClose={() => setReset(null)} />
    </div>
  );
}
