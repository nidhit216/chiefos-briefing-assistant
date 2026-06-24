"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import AppHeader from "@/app/components/AppHeader";
import PageShell from "@/app/components/PageShell";
import Toast from "@/app/components/Toast";
import type {
  User,
  Email,
  CalendarEvent,
  Note,
  DailyBrief,
  BriefContent,
  BriefTask,
} from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [brief, setBrief] = useState<BriefContent | null>(null);
  const [emails, setEmails] = useState<Email[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [tasks, setTasks] = useState<BriefTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [syncingEmails, setSyncingEmails] = useState(false);
  const [syncingCalendar, setSyncingCalendar] = useState(false);
  const [refreshingNotes, setRefreshingNotes] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [briefMode, setBriefMode] = useState<"agent" | "simple">("agent");
  const briefAbortRef = useRef<AbortController | null>(null);
  const calendarAbortRef = useRef<AbortController | null>(null);
  const emailsAbortRef = useRef<AbortController | null>(null);

  function isAbortError(err: unknown) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  const archiveEmail = useCallback(async (id: string) => {
    await apiFetch(`/emails/${id}/archive`, { method: "POST" });
    setEmails((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const archiveEvent = useCallback(async (id: string) => {
    await apiFetch(`/calendar/${id}/archive`, { method: "POST" });
    setEvents((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const sortedNotes = useMemo(
    () => [...notes].sort((a, b) => Number(a.completed) - Number(b.completed)).slice(0, 6),
    [notes]
  );

  const toggleNoteCompleted = useCallback(async (note: Note) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === note.id ? { ...n, completed: !n.completed } : n))
    );
    await apiFetch(`/notes/${note.id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: note.title,
        content: note.content,
        tags: note.tags,
        due_date: note.due_date,
        completed: !note.completed,
      }),
    });
  }, []);

  const toggleTaskCompleted = useCallback(async (task: BriefTask) => {
    setTasks((prev) =>
      prev
        .map((t) => (t.id === task.id ? { ...t, completed: !t.completed } : t))
        .sort((a, b) => Number(a.completed) - Number(b.completed))
    );
    await apiFetch(`/briefs/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: !task.completed }),
    });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadDashboard() {
      try {
        const [userRes, briefRes, emailsRes, eventsRes, notesRes, tasksRes] =
          await Promise.all([
            apiFetch("/auth/me"),
            apiFetch("/briefs/today"),
            apiFetch("/emails/"),
            apiFetch("/calendar/"),
            apiFetch("/notes/"),
            apiFetch("/briefs/tasks"),
          ]);

        setUser(await userRes.json());

        if (briefRes.ok) {
          const briefData: DailyBrief | null = await briefRes.json();
          if (briefData) {
            const parsed = JSON.parse(briefData.content);
            setBrief({
              priorities: parsed.priorities || [],
              focus_areas: parsed.focus_areas || [],
              time_critical: parsed.time_critical || [],
              coming_soon: parsed.coming_soon || [],
            });
          }
        }

        if (emailsRes.ok) setEmails(await emailsRes.json());
        if (eventsRes.ok) setEvents(await eventsRes.json());
        if (notesRes.ok) setNotes(await notesRes.json());
        if (tasksRes.ok) setTasks(await tasksRes.json());
      } catch (_) {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading your dashboard...</p>
      </main>
    );
  }

  return (
    <PageShell>
      <AppHeader userName={user?.name?.split(" ")[0]} />
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Brief */}
        <section className="bg-white rounded-xl shadow p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Today&apos;s Brief
            </h2>
            <div className="flex items-center gap-2">
              <select
                value={briefMode}
                onChange={(e) => setBriefMode(e.target.value as "agent" | "simple")}
                className="text-xs border border-gray-200 rounded-md px-2 py-1 text-gray-600"
                title="Brief generation mode"
              >
                <option value="agent">Agent (RAG)</option>
                <option value="simple">Simple</option>
              </select>
              {generating ? (
                <button
                  onClick={() => briefAbortRef.current?.abort()}
                  className="text-xs px-2 py-1 rounded-md bg-red-50 text-red-600 hover:bg-red-100 transition-colors flex items-center gap-1"
                  title="Stop generating"
                >
                  <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Stop
                </button>
              ) : (
                <button
                  onClick={async () => {
                    setError(null);
                    setGenerating(true);
                    const controller = new AbortController();
                    briefAbortRef.current = controller;
                    try {
                      const res = await apiFetch(`/briefs/generate?mode=${briefMode}`, {
                        method: "POST",
                        signal: controller.signal,
                      });
                      if (res.ok) {
                        const data: DailyBrief = await res.json();
                        const parsed = JSON.parse(data.content);
                        setBrief({
                          priorities: parsed.priorities || [],
                          focus_areas: parsed.focus_areas || [],
                          time_critical: parsed.time_critical || [],
                          coming_soon: parsed.coming_soon || [],
                        });
                        const tasksRes = await apiFetch("/briefs/tasks");
                        if (tasksRes.ok) setTasks(await tasksRes.json());
                      } else {
                        const err = await res.json().catch(() => null);
                        setError(
                          err?.detail ||
                            `Something went wrong (${res.status}). Please try again.`
                        );
                      }
                    } catch (err) {
                      if (!isAbortError(err)) {
                        setError(
                          "Could not reach the server. Please check that the backend is running."
                        );
                      }
                    } finally {
                      setGenerating(false);
                      briefAbortRef.current = null;
                    }
                  }}
                  className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
                  title="Generate / Regenerate brief"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              )}
            </div>
          </div>
          {brief ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-medium text-green-700 mb-2">Priorities for Today</h3>
                <ul className="space-y-1">
                  {tasks
                    .filter((t) => t.category === "priorities")
                    .map((item) => (
                      <motion.li layout key={item.id} className="flex items-start gap-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => toggleTaskCompleted(item)}
                            className="mt-1 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                          />
                          <span className={item.completed ? "line-through text-gray-400" : "text-green-700"}>
                            {item.task}
                          </span>
                        </label>
                      </motion.li>
                    ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-2">Focus Areas</h3>
                <ul className="space-y-1">
                  {tasks
                    .filter((t) => t.category === "focus_areas")
                    .map((item) => (
                      <motion.li layout key={item.id} className="flex items-start gap-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => toggleTaskCompleted(item)}
                            className="mt-1 h-4 w-4 rounded border-gray-300 text-gray-600 focus:ring-gray-500"
                          />
                          <span className={item.completed ? "line-through text-gray-400" : "text-gray-700"}>
                            {item.task}
                          </span>
                        </label>
                      </motion.li>
                    ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-rose-900 mb-2">Time Critical</h3>
                <ul className="space-y-1">
                  {tasks
                    .filter((t) => t.category === "time_critical")
                    .map((item) => (
                      <motion.li layout key={item.id} className="flex items-start justify-between gap-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => toggleTaskCompleted(item)}
                            className="mt-1 h-4 w-4 rounded border-gray-300 text-rose-700 focus:ring-rose-500"
                          />
                          <span className={item.completed ? "line-through text-gray-400" : "text-rose-900"}>
                            {item.task}
                          </span>
                        </label>
                        {item.date_label && (
                          <span className="text-xs bg-rose-100 text-rose-800 px-2 py-0.5 rounded whitespace-nowrap">
                            {item.date_label}
                          </span>
                        )}
                      </motion.li>
                    ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-2">Coming Soon</h3>
                <ul className="space-y-1">
                  {tasks
                    .filter((t) => t.category === "coming_soon")
                    .map((item) => (
                      <motion.li layout key={item.id} className="flex items-start justify-between gap-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => toggleTaskCompleted(item)}
                            className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className={item.completed ? "line-through text-gray-400" : "text-gray-600"}>
                            {item.task}
                          </span>
                        </label>
                        {item.date_label && (
                          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded whitespace-nowrap">
                            {item.date_label}
                          </span>
                        )}
                      </motion.li>
                    ))}
                </ul>
              </div>
            </div>
          ) : (
            <>
            <p className="text-gray-500">
              No brief generated yet today. Click the refresh icon above to generate one.
            </p>
            {error && (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex items-start gap-3">
                  <span className="text-red-500 text-lg">⚠️</span>
                  <div>
                    <p className="font-medium text-red-800">
                      Failed to generate brief
                    </p>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}
            </>
          )}
        </section>

        {/* Notes */}
        <section className="bg-white rounded-xl shadow p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Personal Notes
            </h2>
            <div className="flex items-center gap-3">
              <button
                onClick={async () => {
                  setRefreshingNotes(true);
                  try {
                    const res = await apiFetch("/notes/");
                    if (res.ok) {
                      setNotes(await res.json());
                      setToast("Notes refreshed");
                    }
                  } catch (_) {}
                  setRefreshingNotes(false);
                }}
                disabled={refreshingNotes}
                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
                title="Refresh notes"
              >
                <svg className={`w-5 h-5 ${refreshingNotes ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              <Link
                href="/notes"
                className="text-primary-600 text-sm hover:underline"
              >
                View All
              </Link>
            </div>
          </div>
          {notes.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {sortedNotes.map((note) => (
                <div
                  key={note.id}
                  className="border border-gray-200 rounded-lg p-3"
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={note.completed}
                      onChange={() => toggleNoteCompleted(note)}
                      className="mt-0.5 h-3.5 w-3.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <p
                      className={`font-medium text-sm ${
                        note.completed ? "line-through text-gray-400" : "text-gray-900"
                      }`}
                    >
                      {note.title}
                    </p>
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {note.content.replace(/<[^>]+>/g, " ")}
                  </p>
                  {note.tags && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {note.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No notes yet.</p>
          )}
        </section>

        {/* Upcoming Meetings */}
        <section className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Upcoming Meetings
            </h2>
            {syncingCalendar ? (
              <button
                onClick={() => calendarAbortRef.current?.abort()}
                className="text-xs px-2 py-1 rounded-md bg-red-50 text-red-600 hover:bg-red-100 transition-colors flex items-center gap-1"
                title="Stop syncing"
              >
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Stop
              </button>
            ) : (
              <button
                onClick={async () => {
                  setSyncingCalendar(true);
                  const controller = new AbortController();
                  calendarAbortRef.current = controller;
                  try {
                    const res = await apiFetch("/calendar/sync", {
                      method: "POST",
                      signal: controller.signal,
                    });
                    if (res.ok) {
                      setEvents(await res.json());
                      setToast("Calendar synced successfully");
                    }
                  } catch (err) {
                    if (!isAbortError(err)) setToast("Could not sync calendar");
                  }
                  setSyncingCalendar(false);
                  calendarAbortRef.current = null;
                }}
                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
                title="Sync calendar from Google"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            )}
          </div>
          {events.length > 0 ? (
            <ul className="space-y-3">
              {events.slice(0, 5).map((event) => {
                const start = new Date(event.start_time);
                const end = new Date(event.end_time);
                const sameDay = start.toDateString() === end.toDateString();
                const dateStr = sameDay
                  ? start.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) + " · " + start.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
                  : start.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " – " + end.toLocaleDateString(undefined, { month: "short", day: "numeric" });
                return (
                  <li key={event.id} className="border-l-4 border-primary-500 pl-3 flex justify-between items-start group">
                    <div>
                      <p className="font-medium text-gray-900">{event.title}</p>
                      <p className="text-sm text-gray-500">{dateStr}</p>
                    </div>
                    <button
                      onClick={() => archiveEvent(event.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
                      title="Archive"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                      </svg>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-gray-500">No upcoming meetings.</p>
          )}
        </section>

        {/* Recent Emails */}
        <section className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Recent Emails
            </h2>
            {syncingEmails ? (
              <button
                onClick={() => emailsAbortRef.current?.abort()}
                className="text-xs px-2 py-1 rounded-md bg-red-50 text-red-600 hover:bg-red-100 transition-colors flex items-center gap-1"
                title="Stop syncing"
              >
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Stop
              </button>
            ) : (
              <button
                onClick={async () => {
                  setSyncingEmails(true);
                  const controller = new AbortController();
                  emailsAbortRef.current = controller;
                  try {
                    const res = await apiFetch("/emails/sync", {
                      method: "POST",
                      signal: controller.signal,
                    });
                    if (res.ok) {
                      setEmails(await res.json());
                      setToast("Emails synced successfully");
                    }
                  } catch (err) {
                    if (!isAbortError(err)) setToast("Could not sync emails");
                  }
                  setSyncingEmails(false);
                  emailsAbortRef.current = null;
                }}
                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
                title="Sync emails from Gmail"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            )}
          </div>
          {emails.length > 0 ? (
            <ul className="space-y-3">
              {emails.slice(0, 5).map((email) => (
                <li key={email.id} className="border-b border-gray-100 pb-2 flex justify-between items-start group">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900 text-sm">
                      {email.subject}
                    </p>
                    <p className="text-xs text-gray-500">{email.sender}</p>
                    <p className="text-xs text-gray-400 truncate">
                      {email.snippet}
                    </p>
                  </div>
                  <button
                    onClick={() => archiveEmail(email.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity flex-shrink-0 ml-2"
                    title="Archive"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">No emails synced yet.</p>
          )}
        </section>
      </div>
    </PageShell>
  );
}
