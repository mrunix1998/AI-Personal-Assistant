type Props = {
  label: string;
  value: string | number;
  hint?: string;
  icon?: string;
};

export function MetricCard({ label, value, hint, icon = "◆" }: Props) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        {hint ? <span>{hint}</span> : null}
      </div>
    </div>
  );
}
