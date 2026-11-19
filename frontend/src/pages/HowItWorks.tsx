import { PageHeader } from "@/components/ui";
import { SECTIONS, Section } from "@/components/misc/docs";

export default function HowItWorks() {
  return (
    <div>
      <PageHeader title="How it works" subtitle="Scoring, checks, custody and limits" />
      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        <nav className="lg:sticky lg:top-4 lg:self-start">
          <div className="mb-2 text-xs font-semibold text-muted">On this page</div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 lg:block lg:space-y-1.5">
            {SECTIONS.map((s) => <li key={s.id}><a href={`#${s.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(s.id)?.scrollIntoView({ behavior: "smooth" }); }} className="text-muted hover:text-accent">{s.title}</a></li>)}
          </ul>
        </nav>
        <div className="min-w-0">{SECTIONS.map((s) => <Section key={s.id} s={s} />)}</div>
      </div>
    </div>
  );
}
