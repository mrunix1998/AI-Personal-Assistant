"use client";

import type { User } from "../lib/types";

type Props = {
  user: User | null;
  active: string;
  onNavigate: (page: string) => void;
  onLogout: () => void;
  children: React.ReactNode;
};

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: "✦" },
  { id: "agenda", label: "Daily Agenda", icon: "◷" },
  { id: "notifications", label: "Notifications", icon: "●" },
  { id: "integrations", label: "Integrations", icon: "⌁" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

export function AppShell({ user, active, onNavigate, onLogout, children }: Props) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-icon">AI</div>
          <div>
            <div className="brand-title">Personal Assistant</div>
            <div className="brand-subtitle">Agenda Aggregator</div>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${active === item.id ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="avatar">{user?.email?.[0]?.toUpperCase() || "U"}</div>
            <div className="user-meta">
              <strong>{user?.full_name || "User"}</strong>
              <span>{user?.email}</span>
            </div>
          </div>
          <button className="ghost-button full" onClick={onLogout}>Logout</button>
        </div>
      </aside>

      <main className="main-area">
        <div className="topbar">
          <div>
            <p className="eyebrow">AI Personal Assistant</p>
            <h1>{navItems.find((item) => item.id === active)?.label || "Dashboard"}</h1>
          </div>
          <div className="status-pill"><span /> Backend connected</div>
        </div>
        {children}
      </main>
    </div>
  );
}
