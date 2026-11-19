// Shown by pages / viewers that a part has not replaced yet. DO NOT EDIT.
import { Card, PageHeader } from "./ui";
export default function Placeholder({ name, part }: { name: string; part: string }) {
  return <><PageHeader title={name} /><Card className="p-8 text-center text-muted">"{name}" is built in {part}. This placeholder is replaced when that part is merged.</Card></>;
}
