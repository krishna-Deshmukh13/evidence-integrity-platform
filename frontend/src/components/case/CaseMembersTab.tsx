import { useState } from "react";
import { Plus, Trash, UserCheck, UserPlus, UsersThree } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { ago } from "@/lib/format";
import type { CaseMember, UserAdmin } from "@/lib/types";
import { Badge, Button, Card, Empty, ErrorBox, Loading, Select, useToast } from "@/components/ui";

const initials = (n: string) =>
  n
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("") || "?";

export default function CaseMembersTab({
  caseId,
  members,
  onUpdated,
}: {
  caseId: number;
  members: CaseMember[];
  onUpdated: () => void;
}) {
  const { can, user: currentUser } = useAuth();
  const isAdmin = can("admin");
  const toast = useToast();

  const usersState = useApi(() => (isAdmin ? api.users() : Promise.resolve([] as UserAdmin[])), [isAdmin]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [caseRole, setCaseRole] = useState<"member" | "lead">("member");
  const [busy, setBusy] = useState(false);

  const existingMemberIds = new Set(members.map((m) => m.user_id));
  const candidateUsers = (usersState.data || []).filter((u) => !existingMemberIds.has(u.id) && u.is_active);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) return;
    setBusy(true);
    try {
      await api.addCaseMember(caseId, {
        user_id: Number(selectedUserId),
        role: caseRole,
      });
      toast("Member added to case", "good");
      setSelectedUserId("");
      onUpdated();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to add member", "bad");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (m: CaseMember) => {
    if (!confirm(`Remove ${m.full_name} from this case?`)) return;
    try {
      await api.removeCaseMember(caseId, m.user_id);
      toast(`Removed ${m.full_name} from case`, "good");
      onUpdated();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to remove member", "bad");
    }
  };

  return (
    <div className="space-y-4">
      {/* Information Header */}
      <Card className="p-4 bg-surface2/50 border-line">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-accent-soft text-accent shrink-0">
            <UsersThree size={20} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Per-Case Access Control</h3>
            <p className="text-xs text-muted mt-0.5">
              Administrators have platform-wide access. Investigators and Viewers can only view and manage cases
              they own or are assigned to as team members below.
            </p>
          </div>
        </div>
      </Card>

      {/* Add Member Bar (Admin only) */}
      {isAdmin && (
        <Card className="p-4">
          <h4 className="text-xs font-semibold text-muted mb-3 flex items-center gap-1.5">
            <UserPlus size={14} /> Add Team Member
          </h4>
          <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="flex-1 w-full">
              <label className="text-xs text-muted block mb-1">Select User</label>
              <Select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : "")}
                className="w-full"
                required
              >
                <option value="">-- Choose active user to assign --</option>
                {candidateUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.username}) — {u.role}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-full sm:w-44">
              <label className="text-xs text-muted block mb-1">Case Role</label>
              <Select
                value={caseRole}
                onChange={(e) => setCaseRole(e.target.value as any)}
                className="w-full"
              >
                <option value="member">Member</option>
                <option value="lead">Case Lead</option>
              </Select>
            </div>
            <Button
              variant="primary"
              disabled={busy || !selectedUserId}
              className="w-full sm:w-auto shrink-0"
            >
              <Plus size={14} /> Add to Case
            </Button>
          </form>
        </Card>
      )}

      {/* Members List Table */}
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-left">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th className="px-4 py-2.5">Investigator / Examiner</th>
              <th className="px-3 py-2.5">System Role</th>
              <th className="px-3 py-2.5">Case Role</th>
              <th className="px-3 py-2.5">Assigned</th>
              {isAdmin && <th className="px-4 py-2.5 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-line text-xs">
            {members.length === 0 ? (
              <tr>
                <td colSpan={isAdmin ? 5 : 4} className="py-8 text-center text-muted">
                  No individual team members assigned yet. Case owner and Administrators have access.
                </td>
              </tr>
            ) : (
              members.map((m) => {
                const isMe = m.user_id === currentUser?.id;
                return (
                  <tr key={m.id} className="hover:bg-surface2/50 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <span className="flex size-7 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
                          {initials(m.full_name)}
                        </span>
                        <div>
                          <div className="font-medium text-foreground">
                            {m.full_name}
                            {isMe && <span className="ml-1 text-muted font-normal">(you)</span>}
                          </div>
                          <div className="text-[11px] text-muted">@{m.username}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 capitalize">
                      <Badge tone={m.user_role === "admin" ? "good" : m.user_role === "investigator" ? "warn" : "muted"}>
                        {m.user_role}
                      </Badge>
                    </td>
                    <td className="px-3 py-3">
                      <span className="font-semibold capitalize text-foreground flex items-center gap-1">
                        <UserCheck size={13} className="text-accent" />
                        {m.case_role}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-muted">{m.added_at ? ago(m.added_at) : "Case creation"}</td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          onClick={() => handleRemove(m)}
                          title="Remove user from case"
                          className="text-bad hover:bg-bad-soft"
                        >
                          <Trash size={13} /> Remove
                        </Button>
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
