import type { AgendaItem } from "../lib/types";

function formatTime(value?: string | null) {
  if (!value) return "No time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function AgendaTimeline({ items }: { items: AgendaItem[] }) {
  if (!items.length) {
    return <div className="empty-state">No meetings or tasks for this day.</div>;
  }

  return (
    <div className="timeline-list">
      {items.map((item, index) => (
        <div className="timeline-item" key={`${item.title}-${index}`}>
          <div className="timeline-time">
            {formatTime(item.starts_at || item.due_at)}
          </div>
          <div className="timeline-dot" />
          <div className="timeline-card">
            <div className="timeline-card-header">
              <strong>{item.title}</strong>
              <span>{item.source || item.type || "local"}</span>
            </div>
            <p>
              {item.ends_at ? `${formatTime(item.starts_at)} – ${formatTime(item.ends_at)}` : item.due_at ? `Due ${formatTime(item.due_at)}` : "No exact time"}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
