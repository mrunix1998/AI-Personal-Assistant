export type User = {
  id: string;
  email: string;
  full_name?: string | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type AgendaItem = {
  id?: string;
  type?: string;
  title: string;
  source?: string;
  starts_at?: string | null;
  ends_at?: string | null;
  due_at?: string | null;
  status?: string | null;
};

export type UnifiedAgenda = {
  date: string;
  timezone?: string;
  stats: {
    meeting_count: number;
    task_count: number;
    overdue_task_count?: number;
    completed_task_count?: number;
    total_count: number;
  };
  meetings: AgendaItem[];
  tasks: AgendaItem[];
  timeline: AgendaItem[];
  channel_messages?: Array<{ channel: string; subject?: string | null; message: string }>;
};

export type NotificationItem = {
  id: string;
  title: string;
  message: string;
  source?: string;
  channel?: string;
  status: "unread" | "read" | string;
  agenda_date?: string | null;
  created_at: string;
  read_at?: string | null;
};

export type Channel = {
  id: string;
  channel: string;
  destination: string;
  display_name?: string | null;
  is_enabled: boolean;
  created_at?: string;
};

export type WebPushSubscription = {
  id: string;
  endpoint: string;
  user_agent?: string | null;
  is_enabled: boolean;
  created_at?: string;
};

export type SecretItem = {
  id?: string;
  provider?: string;
  key?: string;
  secret_key?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};
