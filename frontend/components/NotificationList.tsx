import type { NotificationItem } from "../lib/types";

export function NotificationList({ items, onRead }: { items: NotificationItem[]; onRead: (id: string) => void }) {
  if (!items.length) return <div className="empty-state">No notifications yet.</div>;

  return (
    <div className="notification-list">
      {items.map((item) => (
        <div className={`notification-card ${item.status === "unread" ? "unread" : ""}`} key={item.id}>
          <div>
            <div className="notification-title-row">
              <strong>{item.title}</strong>
              <span>{item.channel || "web"}</span>
            </div>
            <p>{item.message}</p>
            <small>{new Date(item.created_at).toLocaleString()}</small>
          </div>
          {item.status === "unread" ? (
            <button className="small-button" onClick={() => onRead(item.id)}>Mark read</button>
          ) : (
            <span className="read-badge">Read</span>
          )}
        </div>
      ))}
    </div>
  );
}
