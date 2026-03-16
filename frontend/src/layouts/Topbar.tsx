import { StatPill } from "../components/ui/StatPill";

export function Topbar() {
  return (
    <header className="topbar">
      <div>
        <p className="topbar__eyebrow">Explainable Verification Workspace</p>
        <p className="topbar__title">
          Calm product framing for evidence-led verification and review work.
        </p>
      </div>
      <div className="topbar__stats">
        <StatPill label="API surface" tone="primary" value="4 endpoints" />
        <StatPill label="Data mode" value="Typed demo data" />
      </div>
    </header>
  );
}
