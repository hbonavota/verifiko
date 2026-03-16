interface BadgeProps {
  label: string;
  tone?: "neutral" | "primary" | "success" | "warning" | "danger";
}

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  return <span className={`badge badge--${tone}`}>{label}</span>;
}
