'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

type Source = {
  id: string;
  provider: string;
  name: string;
  external_id: string;
  is_enabled: boolean;
  last_synced_at?: string | null;
};

export default function IntegrationsPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [icsName, setIcsName] = useState('Apple Calendar');
  const [icsUrl, setIcsUrl] = useState('');
  const [icsProvider, setIcsProvider] = useState('apple_ics');
  const [status, setStatus] = useState('');
  const [events, setEvents] = useState<any[]>([]);

  async function load() {
    try {
      const data = await apiFetch('/calendars/sources');
      setSources(data);
      const ev = await apiFetch('/calendars/events');
      setEvents(ev);
    } catch (e: any) {
      setStatus(e.message);
    }
  }

  useEffect(() => { load(); }, []);

  async function connectOutlook() {
    try {
      const data = await apiFetch('/calendars/outlook/connect');
      window.location.href = data.authorization_url;
    } catch (e: any) { setStatus(e.message); }
  }

  async function addIcs() {
    try {
      await apiFetch('/calendars/ics-sources', {
        method: 'POST',
        body: JSON.stringify({ name: icsName, ics_url: icsUrl, provider: icsProvider }),
      });
      setStatus('ICS calendar saved.');
      await load();
    } catch (e: any) { setStatus(e.message); }
  }

  async function testSource(id: string) {
    try {
      const data = await apiFetch(`/calendars/sources/${id}/test`, { method: 'POST' });
      setStatus(data.message);
    } catch (e: any) { setStatus(e.message); }
  }

  async function syncSource(id: string) {
    try {
      const data = await apiFetch(`/calendars/sources/${id}/sync`, { method: 'POST' });
      setStatus(`Synced ${data.synced_count} events from ${data.provider}.`);
      await load();
    } catch (e: any) { setStatus(e.message); }
  }

  async function syncAll() {
    try {
      const data = await apiFetch('/calendars/sync-all', { method: 'POST' });
      setStatus(`Sync completed. Total synced: ${data.total_synced}`);
      await load();
    } catch (e: any) { setStatus(e.message); }
  }

  return (
    <main className="min-h-screen bg-[#f7f0e4] p-8 text-slate-900">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-amber-600">AI Personal Assistant</p>
            <h1 className="text-4xl font-black">Calendar Integrations</h1>
            <p className="mt-2 text-slate-600">Connect Outlook and add Apple/Generic ICS calendar feeds.</p>
          </div>
          <button onClick={syncAll} className="rounded-2xl bg-slate-950 px-5 py-3 font-bold text-white shadow-lg">Sync all calendars</button>
        </header>

        {status && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 font-semibold text-amber-900">{status}</div>}

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-black">Outlook / Microsoft 365</h2>
              <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">OAuth</span>
            </div>
            <p className="mb-6 text-slate-600">Use Microsoft OAuth and Graph Calendar API. Username/password is not required.</p>
            <button onClick={connectOutlook} className="rounded-2xl bg-blue-600 px-5 py-3 font-bold text-white">Connect Outlook</button>
          </div>

          <div className="rounded-3xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-black">Apple / Generic ICS</h2>
              <span className="rounded-full bg-yellow-50 px-3 py-1 text-sm font-bold text-yellow-700">Free</span>
            </div>
            <div className="space-y-3">
              <select value={icsProvider} onChange={(e) => setIcsProvider(e.target.value)} className="w-full rounded-xl border p-3">
                <option value="apple_ics">Apple Calendar ICS</option>
                <option value="generic_ics">Generic ICS</option>
              </select>
              <input value={icsName} onChange={(e) => setIcsName(e.target.value)} placeholder="Calendar name" className="w-full rounded-xl border p-3" />
              <input value={icsUrl} onChange={(e) => setIcsUrl(e.target.value)} placeholder="https://.../calendar.ics" className="w-full rounded-xl border p-3" />
              <button onClick={addIcs} className="rounded-2xl bg-yellow-400 px-5 py-3 font-black text-slate-950">Save ICS Calendar</button>
            </div>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-xl">
          <h2 className="mb-4 text-2xl font-black">Connected calendar sources</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {sources.map((s) => (
              <div key={s.id} className="rounded-2xl border p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-black">{s.name}</h3>
                    <p className="text-sm text-slate-500">{s.provider}</p>
                    <p className="mt-1 truncate text-xs text-slate-400">{s.external_id}</p>
                    <p className="mt-2 text-xs text-slate-500">Last sync: {s.last_synced_at || 'Never'}</p>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">{s.is_enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div className="mt-4 flex gap-2">
                  <button onClick={() => testSource(s.id)} className="rounded-xl bg-slate-100 px-4 py-2 font-bold">Test</button>
                  <button onClick={() => syncSource(s.id)} className="rounded-xl bg-slate-950 px-4 py-2 font-bold text-white">Sync</button>
                </div>
              </div>
            ))}
            {!sources.length && <p className="text-slate-500">No calendar sources connected yet.</p>}
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-xl">
          <h2 className="mb-4 text-2xl font-black">Synced events</h2>
          <div className="space-y-3">
            {events.slice(0, 12).map((e) => (
              <div key={e.id} className="rounded-2xl bg-slate-50 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-black">{e.title}</h3>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-600">{e.provider_name}</span>
                </div>
                <p className="text-sm text-slate-500">{new Date(e.starts_at).toLocaleString()} → {new Date(e.ends_at).toLocaleString()}</p>
                {e.location && <p className="text-sm text-slate-500">{e.location}</p>}
              </div>
            ))}
            {!events.length && <p className="text-slate-500">No synced events yet.</p>}
          </div>
        </section>
      </div>
    </main>
  );
}
