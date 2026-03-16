interface StatPillProps {
  label: string;
  value: string;
  tone?: "neutral" | "primary" | "success" | "warning" | "danger";
}

export function StatPill({ label, value, tone = "neutral" }: StatPillProps) {
  return (
    <div className={`stat-pill stat-pill--${tone}`}>
      <span className="stat-pill__label">{label}</span>
      <span className="stat-pill__value">{value}</span>
    </div>
  );
}
