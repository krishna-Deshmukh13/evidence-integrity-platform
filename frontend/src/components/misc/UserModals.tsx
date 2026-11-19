import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Field, Input, Modal, Select, useToast } from "@/components/ui";
import type { Role, UserAdmin } from "@/lib/types";

const msg = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong");

export function NewAccountModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [username, setUsername] = useState("");
  const [full, setFull] = useState("");
  const [pw, setPw] = useState("");
  const [role, setRole] = useState<Role>("investigator");
  const [busy, setBusy] = useState(false);
  const ok = username.trim().length > 0 && full.trim().length > 0 && pw.length >= 8;
  const submit = async () => {
    setBusy(true);
    try {
      await api.createUser({ username: username.trim(), full_name: full.trim(), password: pw, role });
      toast("Account created");
      setUsername(""); setFull(""); setPw(""); setRole("investigator");
      onDone(); onClose();
    } catch (e) { toast(msg(e), "bad"); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title="New account"
      footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" disabled={!ok || busy} onClick={submit}>Create</Button></>}>
      <div className="space-y-3">
        <Field label="Username"><Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" /></Field>
        <Field label="Full name"><Input value={full} onChange={(e) => setFull(e.target.value)} /></Field>
        <Field label="Password" hint="At least 8 characters"><Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
        <Field label="Role">
          <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="admin">Admin</option><option value="investigator">Investigator</option><option value="viewer">Viewer</option>
          </Select>
        </Field>
      </div>
    </Modal>
  );
}

export function ResetPasswordModal({ user, onClose }: { user: UserAdmin | null; onClose: () => void }) {
  const toast = useToast();
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const close = () => { setPw(""); onClose(); };
  const submit = async () => {
    if (!user) return;
    setBusy(true);
    try { await api.patchUser(user.id, { password: pw }); toast("Password reset"); close(); }
    catch (e) { toast(msg(e), "bad"); } finally { setBusy(false); }
  };
  return (
    <Modal open={user !== null} onClose={close} title={`Reset password${user ? ` for ${user.full_name}` : ""}`}
      footer={<><Button onClick={close}>Cancel</Button><Button variant="primary" disabled={pw.length < 8 || busy} onClick={submit}>Reset</Button></>}>
      <Field label="New password" hint="At least 8 characters"><Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
    </Modal>
  );
}
