'use client';

import { useEffect, useMemo, useState } from 'react';
import { api, clearToken, getToken, setToken } from '../lib/api';

type Status = { type: 'ok' | 'error' | 'info'; text: string } | null;
const today = new Date().toISOString().slice(0, 10);

function pretty(value: any): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function IntegrationCard({
  title,
  subtitle,
  badge,
  children,
}: {
  title: string;
  subtitle: string;
  badge: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card integration-card">
      <div className="card-head">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="badge">{badge}</span>
      </div>
      <div className="card-body">{children}</div>
    </section>
  );
}

export default function Page() {
  const [active, setActive] = useState('dashboard');
  const [jwt, setJwt] = useState('');
  const [status, setStatus] = useState<Status>(null);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [agendaDate, setAgendaDate] = useState(today);
  const [agenda, setAgenda] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [secrets, setSecrets] = useState<any[]>([]);
  const [calendarSources, setCalendarSources] = useState<any[]>([]);
  const [monitoring, setMonitoring] = useState<any>(null);
  const [reminderLeadMinutes, setReminderLeadMinutes] = useState('15');

  const [auth, setAuth] = useState({
    email: 'salehimohammad331@gmail.com',
    password: 'mohammad1377',
    full_name: 'Mohammad Salehi',
  });

  const [telegram, setTelegram] = useState({
    bot_token: '',
    chat_id: '',
    message: '✅ Telegram test from AI Personal Assistant',
  });

  const [email, setEmail] = useState({
    smtp_host: 'smtp.gmail.com',
    smtp_port: '587',
    smtp_username: '',
    smtp_password: '',
    smtp_from_email: '',
    to_email: '',
    message: '✅ Email test from AI Personal Assistant',
  });

  const [notion, setNotion] = useState({ notion_token: '', database_id: '' });
  const [jira, setJira] = useState({
    jira_base_url: '',
    jira_email: '',
    jira_api_token: '',
    jira_project_key: '',
  });
  const [outlook, setOutlook] = useState({
    outlook_access_token: '',
    tenant_id: '',
    client_id: '',
    client_secret: '',
  });
  const [ics, setIcs] = useState({
    name: 'Apple / Generic ICS',
    ics_url: '',
  });

  useEffect(() => {
    setJwt(getToken());
  }, []);

  async function run(label: string, fn: () => Promise<any>) {
    setLoading(true);
    setStatus({ type: 'info', text: `${label}...` });
    try {
      const result = await fn();
      setOutput(result?.data ?? result);
      if (result?.ok === false) {
        setStatus({ type: 'error', text: `${label} failed: ${result.message}` });
      } else {
        setStatus({ type: 'ok', text: `${label} successful` });
      }
      return result;
    } catch (err: any) {
      setStatus({ type: 'error', text: `${label} failed: ${err?.message || err}` });
      setOutput(err?.message || String(err));
      return { ok: false, message: err?.message || String(err), data: null };
    } finally {
      setLoading(false);
    }
  }

  async function register() {
    await run('Register', () =>
      api('/auth/register', {
        method: 'POST',
        body: JSON.stringify(auth),
      }),
    );
  }

  async function login() {
    const res = await run('Login', () =>
      api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: auth.email, password: auth.password }),
      }),
    );
    if (res.ok && res.data?.access_token) {
      setToken(res.data.access_token);
      setJwt(res.data.access_token);
    }
  }

  async function loadDashboard() {
    const [a, n, c, s, sources] = await Promise.all([
      api(`/agenda/unified-daily?agenda_date=${agendaDate}`),
      api('/notifications/center'),
      api('/notifications/channels'),
      api('/secrets'),
      api('/calendar/sources'),
    ]);

    setAgenda(a.data);
    setNotifications(Array.isArray(n.data) ? n.data : []);
    setChannels(Array.isArray(c.data) ? c.data : []);
    setSecrets(Array.isArray(s.data) ? s.data : []);
    setCalendarSources(Array.isArray(sources.data) ? sources.data : []);

    return {
      ok: true,
      data: {
        agenda: a.data,
        notifications: n.data,
        channels: c.data,
        secrets: s.data,
        calendar_sources: sources.data,
      },
    };
  }

  async function googleConnect() {
    const res = await run('Google Calendar connect', () => api('/integrations/google/connect'));
    const url = res.data?.authorization_url;
    if (res.ok && url) window.location.href = url;
  }

  async function googleSync() {
    await run('Google Calendar sync', () =>
      api('/integrations/google/sync?past_days=30&future_days=30', { method: 'POST' }),
    );
    await loadDashboard();
  }

  async function addIcsSource() {
    await run('Save ICS source', () =>
      api('/calendar/sources', {
        method: 'POST',
        body: JSON.stringify({
          name: ics.name,
          provider: 'ics',
          ics_url: ics.ics_url,
        }),
      }),
    );
    await loadDashboard();
  }

  async function testIcsSource() {
    await run('Test ICS source', () =>
      api('/calendar/sources/test', {
        method: 'POST',
        body: JSON.stringify({
          name: ics.name,
          provider: 'ics',
          ics_url: ics.ics_url,
        }),
      }),
    );
  }

  async function syncAllCalendars() {
    await run('Sync all calendars', () =>
      api(`/calendar/sync-all?past_days=30&future_days=30`, { method: 'POST' }),
    );
    await loadDashboard();
  }

  async function generateReminders() {
    await run('Generate reminders', () =>
      api(`/automation/generate-reminders?agenda_date=${agendaDate}&lead_minutes=${Number(reminderLeadMinutes) || 15}`, { method: 'POST' }),
    );
    await loadDashboard();
  }

  async function runDueReminders() {
    await run('Run due reminders', () =>
      api('/automation/run-due-reminders?limit=100', { method: 'POST' }),
    );
    await loadDashboard();
  }

  async function sendDailyAgendaNow() {
    await run('Send daily agenda now', () =>
      api(`/automation/send-daily-agenda?agenda_date=${agendaDate}`, { method: 'POST' }),
    );
    await loadDashboard();
  }

  async function enqueueAutomation(kind: string) {
    const path =
      kind === 'generate'
        ? `/automation/enqueue/generate-reminders?days_ahead=1&lead_minutes=${Number(reminderLeadMinutes) || 15}`
        : kind === 'due'
          ? '/automation/enqueue/run-due-reminders?limit=100'
          : `/automation/enqueue/send-daily-agendas?agenda_date=${agendaDate}`;
    await run(`Queue ${kind}`, () => api(path, { method: 'POST' }));
  }

  async function loadMonitoring() {
    const [health, readiness, metrics, automation] = await Promise.all([
      api('/monitoring/health'),
      api('/monitoring/readiness'),
      api('/monitoring/metrics'),
      api('/automation/status'),
    ]);
    const data = {
      health: health.data,
      readiness: readiness.data,
      metrics: metrics.data,
      automation: automation.data,
    };
    setMonitoring(data);
    return { ok: true, data };
  }

  const metrics = useMemo(() => {
    const stats = agenda?.stats || {};
    return [
      ['Meetings', stats.meeting_count ?? 0],
      ['Tasks', stats.task_count ?? 0],
      ['Notifications', notifications.length],
      ['Channels', channels.length],
      ['Calendar sources', calendarSources.length],
    ];
  }, [agenda, notifications, channels, calendarSources]);

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">AI</div>
          <div>
            <strong>Personal Assistant</strong>
            <span>Agenda Aggregator</span>
          </div>
        </div>

        {['dashboard', 'agenda', 'notifications', 'integrations', 'automation', 'monitoring', 'settings'].map((item) => (
          <button
            key={item}
            className={active === item ? 'nav active' : 'nav'}
            onClick={() => setActive(item)}
          >
            {item}
          </button>
        ))}

        <div className="account">
          <div className="avatar">{auth.full_name.slice(0, 1)}</div>
          <div>
            <strong>{auth.full_name}</strong>
            <span>{auth.email}</span>
          </div>
        </div>

        <button
          className="nav"
          onClick={() => {
            clearToken();
            setJwt('');
          }}
        >
          Logout
        </button>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">AI Personal Assistant</p>
            <h1>{active === 'dashboard' ? 'Dashboard' : active[0].toUpperCase() + active.slice(1)}</h1>
          </div>
          <div className={jwt ? 'connection ok' : 'connection'}>
            <span />
            {jwt ? 'Authenticated' : 'Not logged in'}
          </div>
        </header>

        {status && <div className={`toast ${status.type}`}>{status.text}</div>}
        {loading && <div className="toast info">Working...</div>}

        {!jwt && (
          <section className="card auth-card">
            <h2>Login / Register</h2>
            <div className="grid three">
              <Field label="Email" value={auth.email} onChange={(v) => setAuth({ ...auth, email: v })} />
              <Field label="Password" type="password" value={auth.password} onChange={(v) => setAuth({ ...auth, password: v })} />
              <Field label="Full name" value={auth.full_name} onChange={(v) => setAuth({ ...auth, full_name: v })} />
            </div>
            <div className="actions">
              <button onClick={register}>Register</button>
              <button onClick={login}>Login</button>
            </div>
          </section>
        )}

        {active === 'dashboard' && (
          <>
            <div className="toolbar">
              <input type="date" value={agendaDate} onChange={(e) => setAgendaDate(e.target.value)} />
              <button onClick={() => run('Load dashboard', loadDashboard)}>Refresh dashboard</button>
              <button onClick={syncAllCalendars}>Sync all calendars</button>
            </div>

            <div className="metrics">
              {metrics.map(([k, v]) => (
                <div className="metric" key={k}>
                  <span>{k}</span>
                  <strong>{v as any}</strong>
                </div>
              ))}
            </div>

            <section className="card">
              <h2>Today summary</h2>
              <p>{agenda?.channel_messages?.[0]?.message || 'Load dashboard to see your daily agenda.'}</p>
            </section>
          </>
        )}

        {active === 'agenda' && (
          <section className="card">
            <div className="card-head">
              <div>
                <h2>Daily Agenda</h2>
                <p>Events and tasks from all connected sources.</p>
              </div>
              <button onClick={() => run('Load agenda', loadDashboard)}>Load</button>
            </div>

            <div className="timeline">
              {(agenda?.timeline || []).length === 0 && <p className="muted">No items for this day.</p>}
              {(agenda?.timeline || []).map((item: any, idx: number) => (
                <div className="timeline-item" key={idx}>
                  <span>{item.time || item.starts_at || item.due_at || 'Anytime'}</span>
                  <strong>{item.title}</strong>
                  <em>{item.source || item.provider_name}</em>
                </div>
              ))}
            </div>
          </section>
        )}

        {active === 'notifications' && (
          <section className="card">
            <div className="card-head">
              <div>
                <h2>Notification Center</h2>
                <p>Web notifications generated by your assistant.</p>
              </div>
              <button
                onClick={() =>
                  run('Create daily agenda notification', () =>
                    api(`/notifications/center/daily-agenda?agenda_date=${agendaDate}`, { method: 'POST' }),
                  ).then(loadDashboard)
                }
              >
                Generate
              </button>
            </div>

            <div className="notification-list">
              {notifications.length === 0 && <p className="muted">No notifications loaded.</p>}
              {notifications.map((n) => (
                <div className="notification" key={n.id}>
                  <strong>{n.title}</strong>
                  <p>{n.message}</p>
                  <span>{n.status}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {active === 'integrations' && (
          <div className="integrations-grid">
            <IntegrationCard title="Google Calendar" subtitle="OAuth connect and sync events." badge="OAuth">
              <div className="actions">
                <button onClick={googleConnect}>Connect Google</button>
                <button onClick={googleSync}>Sync + Test</button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Outlook Calendar" subtitle="Use Microsoft OAuth/Graph later; for MVP use ICS export URL here." badge="ICS/OAuth">
              <p className="muted">
                Username/password is not recommended. For now, add Outlook published ICS URL or use Microsoft Graph token test if your backend supports it.
              </p>
              <Field label="Outlook / Microsoft calendar ICS URL" value={ics.ics_url} onChange={(v) => setIcs({ ...ics, ics_url: v })} />
              <div className="actions">
                <button onClick={addIcsSource}>Save as ICS source</button>
                <button onClick={testIcsSource}>Test ICS</button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Apple / Generic ICS Calendar" subtitle="Save an ICS feed URL and sync events." badge="ICS">
              <Field label="Source name" value={ics.name} onChange={(v) => setIcs({ ...ics, name: v })} />
              <Field label="ICS URL" value={ics.ics_url} onChange={(v) => setIcs({ ...ics, ics_url: v })} />
              <div className="actions">
                <button onClick={addIcsSource}>Save ICS source</button>
                <button onClick={testIcsSource}>Test ICS</button>
                <button onClick={syncAllCalendars}>Sync all</button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Telegram" subtitle="Save bot token and chat id, then send a real test message." badge="Direct test">
              <Field label="Bot token" type="password" value={telegram.bot_token} onChange={(v) => setTelegram({ ...telegram, bot_token: v })} />
              <Field label="Chat ID" value={telegram.chat_id} onChange={(v) => setTelegram({ ...telegram, chat_id: v })} />
              <Field label="Test message" value={telegram.message} onChange={(v) => setTelegram({ ...telegram, message: v })} />
              <div className="actions">
                <button
                  onClick={() =>
                    run('Save Telegram', () =>
                      api('/integration-actions/telegram/save', {
                        method: 'POST',
                        body: JSON.stringify({
                          bot_token: telegram.bot_token,
                          chat_id: telegram.chat_id,
                          display_name: 'Telegram',
                        }),
                      }),
                    )
                  }
                >
                  Save
                </button>
                <button
                  onClick={() =>
                    run('Send Telegram test', () =>
                      api('/integration-actions/telegram/test', {
                        method: 'POST',
                        body: JSON.stringify({ message: telegram.message }),
                      }),
                    )
                  }
                >
                  Send test
                </button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Gmail / Email" subtitle="Save SMTP config and send a real test email." badge="SMTP">
              <div className="grid two">
                <Field label="SMTP host" value={email.smtp_host} onChange={(v) => setEmail({ ...email, smtp_host: v })} />
                <Field label="SMTP port" value={email.smtp_port} onChange={(v) => setEmail({ ...email, smtp_port: v })} />
                <Field label="SMTP username" value={email.smtp_username} onChange={(v) => setEmail({ ...email, smtp_username: v })} />
                <Field label="SMTP app password" type="password" value={email.smtp_password} onChange={(v) => setEmail({ ...email, smtp_password: v })} />
                <Field label="From email" value={email.smtp_from_email} onChange={(v) => setEmail({ ...email, smtp_from_email: v })} />
                <Field label="To email" value={email.to_email} onChange={(v) => setEmail({ ...email, to_email: v })} />
              </div>

              <div className="actions">
                <button
                  onClick={() =>
                    run('Save Email', () =>
                      api('/integration-actions/email/save', {
                        method: 'POST',
                        body: JSON.stringify({
                          smtp_host: email.smtp_host,
                          smtp_port: Number(email.smtp_port),
                          smtp_username: email.smtp_username,
                          smtp_password: email.smtp_password,
                          smtp_from_email: email.smtp_from_email,
                          to_email: email.to_email,
                        }),
                      }),
                    )
                  }
                >
                  Save
                </button>

                <button
                  onClick={() =>
                    run('Send Email test', () =>
                      api('/integration-actions/email/test', {
                        method: 'POST',
                        body: JSON.stringify({
                          message: email.message,
                        }),
                      }),
                    )
                  }
                >
                  Send test
                </button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Notion" subtitle="Save integration token and test with Notion API." badge="API">
              <Field label="Notion token" type="password" value={notion.notion_token} onChange={(v) => setNotion({ ...notion, notion_token: v })} />
              <Field label="Database ID optional" value={notion.database_id} onChange={(v) => setNotion({ ...notion, database_id: v })} />
              <div className="actions">
                <button onClick={() => run('Save Notion', () => api('/integration-actions/notion/save', { method: 'POST', body: JSON.stringify(notion) }))}>Save</button>
                <button onClick={() => run('Test Notion', () => api('/integration-actions/notion/test', { method: 'POST' }))}>Test</button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Jira" subtitle="Save Atlassian API token and verify connection." badge="API">
              <Field label="Base URL" placeholder="https://your-domain.atlassian.net" value={jira.jira_base_url} onChange={(v) => setJira({ ...jira, jira_base_url: v })} />
              <Field label="Email" value={jira.jira_email} onChange={(v) => setJira({ ...jira, jira_email: v })} />
              <Field label="API token" type="password" value={jira.jira_api_token} onChange={(v) => setJira({ ...jira, jira_api_token: v })} />
              <Field label="Project key optional" value={jira.jira_project_key} onChange={(v) => setJira({ ...jira, jira_project_key: v })} />
              <div className="actions">
                <button onClick={() => run('Save Jira', () => api('/integration-actions/jira/save', { method: 'POST', body: JSON.stringify(jira) }))}>Save</button>
                <button onClick={() => run('Test Jira', () => api('/integration-actions/jira/test', { method: 'POST' }))}>Test</button>
              </div>
            </IntegrationCard>

            <IntegrationCard title="Web Push" subtitle="Save and test browser push subscription foundation." badge="Free">
              <div className="actions">
                <button
                  onClick={() =>
                    run('Save demo subscription', () =>
                      api('/notifications/web-push/subscriptions', {
                        method: 'POST',
                        body: JSON.stringify({
                          endpoint: 'https://example.com/fake-push-endpoint-ui',
                          p256dh: 'fake-key',
                          auth: 'fake-auth',
                          user_agent: navigator.userAgent,
                        }),
                      }),
                    )
                  }
                >
                  Save demo subscription
                </button>
                <button onClick={() => run('Generate notification', () => api(`/notifications/center/daily-agenda?agenda_date=${agendaDate}`, { method: 'POST' }))}>
                  Generate notification
                </button>
              </div>
            </IntegrationCard>
          </div>
        )}

        {active === 'automation' && (
          <section className="card">
            <div className="card-head">
              <div>
                <h2>Automation Control Center</h2>
                <p>Run or enqueue production background jobs for reminders and daily agendas.</p>
              </div>
              <button onClick={() => run('Load automation status', () => api('/automation/status'))}>Status</button>
            </div>

            <div className="grid two">
              <Field label="Agenda date" value={agendaDate} onChange={setAgendaDate} />
              <Field label="Reminder lead minutes" value={reminderLeadMinutes} onChange={setReminderLeadMinutes} />
            </div>

            <div className="actions">
              <button onClick={generateReminders}>Generate reminders</button>
              <button onClick={runDueReminders}>Run due reminders now</button>
              <button onClick={sendDailyAgendaNow}>Send daily agenda now</button>
              <button onClick={() => enqueueAutomation('generate')}>Queue generate reminders</button>
              <button onClick={() => enqueueAutomation('due')}>Queue due reminders</button>
              <button onClick={() => enqueueAutomation('daily')}>Queue daily agenda</button>
            </div>

            <p className="muted">Celery Beat automatically generates reminders every 5 minutes, sends due reminders every minute, and sends the daily agenda at 07:00 Europe/Berlin.</p>
          </section>
        )}

        {active === 'monitoring' && (
          <section className="card">
            <div className="card-head">
              <div>
                <h2>Monitoring & Backup</h2>
                <p>Production diagnostics for API, database and automation services.</p>
              </div>
              <button onClick={() => run('Load monitoring', loadMonitoring)}>Refresh monitoring</button>
            </div>
            <div className="actions">
              <button onClick={() => run('Health', () => api('/monitoring/health'))}>Health</button>
              <button onClick={() => run('Readiness', () => api('/monitoring/readiness'))}>Readiness</button>
              <button onClick={() => run('Metrics', () => api('/monitoring/metrics'))}>Metrics</button>
            </div>
            <pre>{pretty(monitoring || 'Run monitoring refresh to see service status. For DB backup run: ./scripts/backup_postgres.sh')}</pre>
          </section>
        )}

        {active === 'settings' && (
          <section className="card">
            <div className="card-head">
              <div>
                <h2>Settings & Diagnostics</h2>
                <p>Check saved channels, secrets and calendar sources. Secret values are never shown.</p>
              </div>
              <button onClick={() => run('Refresh settings', loadDashboard)}>Refresh</button>
            </div>
            <div className="grid three">
              <pre>{pretty(channels)}</pre>
              <pre>{pretty(secrets)}</pre>
              <pre>{pretty(calendarSources)}</pre>
            </div>
          </section>
        )}

        {output && (
          <section className="card output">
            <h2>Last API response</h2>
            <pre>{pretty(output)}</pre>
          </section>
        )}
      </section>
    </main>
  );
}
