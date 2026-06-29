"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import AppHeader from "@/app/components/AppHeader";
import PageShell from "@/app/components/PageShell";
import Toast from "@/app/components/Toast";
import { useBriefGeneration } from "@/app/context/BriefGenerationContext";
import { useMode } from "@/app/context/ModeContext";
import type {
  User,
  Email,
  CalendarEvent,
  DailyBrief,
  BriefContent,
  BriefTask,
} from "@/types";

const DONUT_COLORS = ["#1B2A4A", "#5E7CA0", "#16A34A", "#D97706", "#BE123C"];
const DONUT_RADIUS = 15.91549430918954;

const SLOT_ORDER = ["morning", "afternoon", "evening"] as const;
const SLOT_ICON: Record<(typeof SLOT_ORDER)[number], string> = {
  morning: "🌅",
  afternoon: "☀️",
  evening: "🌙",
};

function getCurrentTimeSlot(): (typeof SLOT_ORDER)[number] {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

function LastUpdated({ at }: { at: Date | null }) {
  if (!at) return null;
  const seconds = Math.floor((Date.now() - at.getTime()) / 1000);
  let label: string;
  if (seconds < 60) label = "just now";
  else if (seconds < 3600) label = `${Math.floor(seconds / 60)}m ago`;
  else if (seconds < 86400) label = `${Math.floor(seconds / 3600)}h ago`;
  else label = at.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <p
      className="font-mono text-[10px] text-ink-muted/70"
      title={at.toLocaleString()}
    >
      Updated {label}
    </p>
  );
}

function FocusBreakdownDonut({ breakdown }: { breakdown: { label: string; percent: number }[] }) {
  let cumulative = 0;
  const topPercent = breakdown[0]?.percent ?? 0;

  return (
    <div className="flex items-center gap-5">
      <svg width="120" height="120" viewBox="0 0 42 42" className="flex-shrink-0">
        <circle cx="21" cy="21" r={DONUT_RADIUS} fill="transparent" stroke="#F2EDE0" strokeWidth="5" />
        {breakdown.map((slice, i) => {
          const dashoffset = 25 - cumulative;
          cumulative += slice.percent;
          return (
            <circle
              key={slice.label}
              cx="21"
              cy="21"
              r={DONUT_RADIUS}
              fill="transparent"
              stroke={DONUT_COLORS[i % DONUT_COLORS.length]}
              strokeWidth="5"
              strokeDasharray={`${slice.percent} ${100 - slice.percent}`}
              strokeDashoffset={dashoffset}
            />
          );
        })}
        <text
          x="21"
          y="21"
          textAnchor="middle"
          dominantBaseline="central"
          style={{ fill: "#1A1A1A", fontSize: "7px", fontWeight: 600 }}
        >
          {topPercent}%
        </text>
      </svg>
      <ul className="space-y-1.5">
        {breakdown.map((slice, i) => (
          <li key={slice.label} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
              style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }}
            />
            <span className="font-medium text-ink">{slice.percent}%</span>
            <span className="text-ink-muted">{slice.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const MOOD_EMOJIS = ["😔", "😐", "🙂", "😊", "🤩"];

function DropletIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2.69l5.66 5.66a8 8 0 11-11.32 0L12 2.69z" />
    </svg>
  );
}

function BarbellIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 7v10M3 9v6m18-6v6m-3-8v10M9 12h6" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2 3.5a1 1 0 011-1h2.4a1 1 0 01.985.81l.755 4.025a1 1 0 01-.272.93l-1.43 1.43a14.5 14.5 0 006.36 6.36l1.43-1.43a1 1 0 01.93-.272l4.025.755a1 1 0 01.81.985V20a1 1 0 01-1 1h-1.5C9.94 21 3 14.06 3 5.5V4" />
    </svg>
  );
}

function MapPinIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function BookOpenIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  );
}

interface HabitDotsProps {
  done: number;
  total: number;
  onToggle: (index: number) => void;
}

function HabitDots({ done, total, onToggle }: HabitDotsProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Array.from({ length: total }).map((_, i) => {
        const isDone = i < done;
        const isToday = i === done;
        return (
          <button
            key={i}
            onClick={() => onToggle(i)}
            className="rounded-full transition-colors"
            style={{
              width: 20,
              height: 20,
              background: isDone
                ? "var(--mode-accent)"
                : isToday
                ? "var(--mode-bg-3)"
                : "transparent",
              border: isDone
                ? "none"
                : isToday
                ? "1.5px solid var(--mode-muted)"
                : "1.5px solid var(--mode-border)",
            }}
          />
        );
      })}
    </div>
  );
}

interface HabitBlockProps {
  icon: React.ReactNode;
  name: string;
  done: number;
  total: number;
  unit: string;
  onToggle: (index: number) => void;
  onLog: () => void;
}

function HabitBlock({ icon, name, done, total, unit, onToggle, onLog }: HabitBlockProps) {
  return (
    <div
      className="flex-1 rounded-xl"
      style={{
        background: "var(--mode-bg-2)",
        border: "0.5px solid var(--mode-border)",
        padding: "14px 16px",
      }}
    >
      <div className="flex items-center gap-1.5" style={{ color: "var(--mode-accent)" }}>
        {icon}
        <span className="text-sm font-medium" style={{ color: "var(--mode-text)" }}>
          {name}
        </span>
      </div>
      <p className="mt-0.5 text-xs" style={{ color: "var(--mode-muted)" }}>
        {done} of {total} {unit}
      </p>
      <div className="mt-3">
        <HabitDots done={done} total={total} onToggle={onToggle} />
      </div>
      <button
        onClick={onLog}
        className="mt-3 text-xs font-medium hover:underline"
        style={{ color: "var(--mode-accent)" }}
      >
        Log
      </button>
    </div>
  );
}

// TODO: replace with API data from Apple Reminders / Google Maps / Books
const RADAR_ITEMS = [
  {
    icon: <PhoneIcon />,
    text: "You haven't called Mum since Sunday — 6 days ago",
    source: "Apple Reminders",
    tag: "family",
  },
  {
    icon: <MapPinIcon />,
    text: "Coorg trip — 3 stays bookmarked, prices rise after July",
    source: "Google Maps",
    tag: "personal",
  },
  {
    icon: <BookOpenIcon />,
    text: "Chapter 14 of Thinking, Fast and Slow — close to end of Part 2",
    source: "Apple Books",
    tag: "leisure",
  },
];

function PersonalDashboard() {
  const [mood, setMood] = useState<number | null>(null);
  const [moodNote, setMoodNote] = useState("");
  const [water, setWater] = useState(5);
  const [gym, setGym] = useState(3);
  const [reading, setReading] = useState(3);

  function toggleDot(current: number, set: (v: number) => void, index: number) {
    set(index < current ? index : index + 1);
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Mood check-in strip */}
      <div
        className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-xl"
        style={{
          background: "var(--mode-bg-2)",
          border: "1px solid var(--mode-border)",
          padding: "12px 16px",
        }}
      >
        <span className="text-sm font-medium flex-shrink-0" style={{ color: "var(--mode-text)" }}>
          How are you feeling today?
        </span>
        <div className="flex gap-1.5">
          {MOOD_EMOJIS.map((emoji, i) => (
            <button
              key={i}
              onClick={() => setMood(i)}
              className="flex h-9 w-9 items-center justify-center rounded-full text-lg transition-colors"
              style={
                mood === i
                  ? { border: "1.5px solid var(--mode-accent)", background: "var(--mode-bg-3)" }
                  : { border: "1.5px solid transparent", background: "transparent" }
              }
            >
              {emoji}
            </button>
          ))}
        </div>
        <input
          type="text"
          value={moodNote}
          onChange={(e) => setMoodNote(e.target.value)}
          placeholder="Anything on your mind?"
          className="flex-1 min-w-0 bg-transparent text-sm outline-none placeholder:opacity-60"
          style={{ color: "var(--mode-text)" }}
        />
      </div>

      {/* Habits */}
      <div>
        <h2
          className="font-mono text-[10px] font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--mode-muted)" }}
        >
          Today&apos;s habits
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <HabitBlock
            icon={<DropletIcon />}
            name="Water"
            done={water}
            total={8}
            unit="glasses today"
            onToggle={(i) => toggleDot(water, setWater, i)}
            onLog={() => setWater((v) => Math.min(8, v + 1))}
          />
          <HabitBlock
            icon={<BarbellIcon />}
            name="Gym"
            done={gym}
            total={5}
            unit="days this week"
            onToggle={(i) => toggleDot(gym, setGym, i)}
            onLog={() => setGym((v) => Math.min(5, v + 1))}
          />
          <HabitBlock
            icon={<BookIcon />}
            name="Reading"
            done={reading}
            total={7}
            unit="days this week"
            onToggle={(i) => toggleDot(reading, setReading, i)}
            onLog={() => setReading((v) => Math.min(7, v + 1))}
          />
        </div>
      </div>

      {/* Divider */}
      <div style={{ background: "var(--mode-border)", height: "0.5px", margin: "0" }} />

      {/* Gently on your radar */}
      <div>
        <h2
          className="font-mono text-[10px] font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--mode-muted)" }}
        >
          Gently on your radar
        </h2>
        <ul>
          {RADAR_ITEMS.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-3 py-3"
              style={{
                borderBottom:
                  i < RADAR_ITEMS.length - 1 ? "1px solid var(--mode-border-soft)" : "none",
              }}
            >
              <div
                className="flex flex-shrink-0 items-center justify-center"
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: 8,
                  background: "var(--mode-icon-bg)",
                  color: "var(--mode-icon-color)",
                }}
              >
                {item.icon}
              </div>
              <div className="min-w-0 flex-1">
                <p style={{ fontSize: 13.5, color: "var(--mode-text)", lineHeight: 1.5 }}>
                  {item.text}
                </p>
                <p className="mt-1" style={{ fontSize: 11, color: "var(--mode-muted)" }}>
                  {item.source}
                </p>
              </div>
              <span
                className="flex-shrink-0 rounded-full"
                style={{
                  fontSize: 10,
                  background: "var(--mode-bg-3)",
                  color: "var(--mode-accent)",
                  padding: "1px 8px",
                }}
              >
                {item.tag}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { mode } = useMode();
  const currentTimeSlot = useMemo(() => getCurrentTimeSlot(), []);
  const [user, setUser] = useState<User | null>(null);
  const [brief, setBrief] = useState<BriefContent | null>(null);
  const [emails, setEmails] = useState<Email[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [tasks, setTasks] = useState<BriefTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingEmails, setSyncingEmails] = useState(false);
  const [syncingCalendar, setSyncingCalendar] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<{
    brief: Date | null;
    calendar: Date | null;
    emails: Date | null;
  }>({ brief: null, calendar: null, emails: null });
  const calendarAbortRef = useRef<AbortController | null>(null);
  const emailsAbortRef = useRef<AbortController | null>(null);
  const { generating, generationVersion, generate, cancel } = useBriefGeneration();
  const seenGenerationVersion = useRef(generationVersion);

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

  const refreshBriefAndTasks = useCallback(async () => {
    const [briefRes, tasksRes] = await Promise.all([
      apiFetch("/briefs/today"),
      apiFetch("/briefs/tasks"),
    ]);

    if (briefRes.ok) {
      const briefData: DailyBrief | null = await briefRes.json();
      if (briefData) {
        const parsed = JSON.parse(briefData.content);
        setBrief({
          executive_summary: parsed.executive_summary || "",
          attention_required: parsed.attention_required || [],
          recommendations: parsed.recommendations || {},
          focus_breakdown: parsed.focus_breakdown || [],
        });
        setLastUpdated((prev) => ({ ...prev, brief: new Date(briefData.created_at) }));
      }
    }
    if (tasksRes.ok) setTasks(await tasksRes.json());
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadDashboard() {
      try {
        const [userRes, emailsRes, eventsRes] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/emails/"),
          apiFetch("/calendar/"),
        ]);

        setUser(await userRes.json());
        await refreshBriefAndTasks();

        const now = new Date();
        if (emailsRes.ok) {
          const emailsData = await emailsRes.json();
          setEmails(emailsData);
          if (emailsData.length > 0) {
            setLastUpdated((prev) => ({ ...prev, emails: now }));
          }
        }
        if (eventsRes.ok) {
          const eventsData = await eventsRes.json();
          setEvents(eventsData);
          if (eventsData.length > 0) {
            setLastUpdated((prev) => ({ ...prev, calendar: now }));
          }
        }
      } catch (_) {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [router, refreshBriefAndTasks]);

  // Brief generation can be kicked off from this page and finish after the user
  // navigates away; when it completes (tracked globally), pick up the fresh brief.
  useEffect(() => {
    if (generationVersion === seenGenerationVersion.current) return;
    seenGenerationVersion.current = generationVersion;
    refreshBriefAndTasks();
  }, [generationVersion, refreshBriefAndTasks]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="font-mono text-sm text-ink-muted">Loading your dashboard...</p>
      </main>
    );
  }

  if (mode === "personal") {
    return (
      <PageShell>
        <AppHeader userName={user?.name?.split(" ")[0]} />
        {toast && <Toast message={toast} onClose={() => setToast(null)} />}
        <PersonalDashboard />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <AppHeader userName={user?.name?.split(" ")[0]} />
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Brief */}
        <section className="bg-cream-50 border border-ink/10 rounded-md p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-1">
                Today&apos;s Briefing
              </p>
              <h2 className="font-serif text-2xl text-ink">
                Executive Summary
              </h2>
              <LastUpdated at={lastUpdated.brief} />
            </div>
            <div className="flex items-center gap-2">
              {generating ? (
                <button
                  onClick={cancel}
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
                  onClick={generate}
                  className="p-2 text-ink-muted hover:text-primary-700 hover:bg-cream-200 rounded-md transition-colors disabled:opacity-50"
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
            <>
            {(brief.executive_summary || brief.focus_breakdown?.length > 0) && (
              <div className="flex flex-col md:flex-row md:items-start gap-6 mb-5 pb-5 border-b border-ink/10">
                {brief.executive_summary && (
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-primary-700 mb-2">
                      Executive Summary
                    </p>
                    <p className="text-ink leading-relaxed">{brief.executive_summary}</p>
                  </div>
                )}
                {brief.focus_breakdown?.length > 0 && (
                  <div className="md:w-auto flex-shrink-0">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-2">
                      Focus Breakdown
                    </p>
                    <FocusBreakdownDonut breakdown={brief.focus_breakdown} />
                  </div>
                )}
              </div>
            )}
            {tasks.some((t) => t.category === "attention_required") && (
              <div className="pt-1">
                <h3 className="font-medium text-amber-800 mb-2 flex items-center gap-1.5">
                  <span aria-hidden>⚠️</span> Attention Required
                </h3>
                <ul className="space-y-1">
                  {tasks
                    .filter((t) => t.category === "attention_required")
                    .map((item) => (
                      <motion.li layout key={item.id} className="flex items-start gap-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => toggleTaskCompleted(item)}
                            className="mt-1 h-4 w-4 rounded border-ink/20 text-amber-700 focus:ring-amber-600"
                          />
                          <span className={item.completed ? "line-through text-ink-muted/60" : "text-amber-900"}>
                            {item.task}
                          </span>
                        </label>
                      </motion.li>
                    ))}
                </ul>
              </div>
            )}

            {(brief.recommendations.morning || brief.recommendations.afternoon || brief.recommendations.evening) && (
              <div className="mt-5 pt-5 border-t border-ink/10">
                <h3 className="font-medium text-ink mb-3">Your Day, Mapped Out</h3>
                <div className="space-y-3">
                  {(["morning", "afternoon", "evening"] as const)
                    .filter((slot) => brief.recommendations[slot])
                    .map((slot) => {
                      const isCurrent = slot === currentTimeSlot;
                      const isPast = SLOT_ORDER.indexOf(slot) < SLOT_ORDER.indexOf(currentTimeSlot);
                      return (
                        <div
                          key={slot}
                          className={`flex items-start gap-3 rounded-md border p-3 transition-colors ${
                            isCurrent
                              ? "border-primary-300 bg-primary-50"
                              : "border-ink/10 bg-transparent"
                          } ${isPast ? "opacity-50" : ""}`}
                        >
                          <span className="text-xl leading-none mt-0.5" aria-hidden>
                            {SLOT_ICON[slot]}
                          </span>
                          <div className="min-w-0">
                            <p
                              className={`font-mono text-[10px] font-semibold uppercase tracking-widest mb-1 ${
                                isCurrent ? "text-primary-700" : "text-ink-muted"
                              }`}
                            >
                              {slot}
                              {isCurrent && " · now"}
                            </p>
                            <p className="text-sm text-ink leading-relaxed">{brief.recommendations[slot]}</p>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
            </>
          ) : (
            <>
            <p className="text-ink-muted">
              No brief generated yet today. Click the refresh icon above to generate one.
            </p>
            </>
          )}
        </section>

        {/* Supporting Context: secondary to the brief — raw calendar/email feeds, not synthesis */}
        <section className="lg:col-span-2">
          <h2 className="font-mono text-[10px] font-semibold text-ink-muted uppercase tracking-widest mb-3">
            Supporting Context
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-cream-50 rounded-md border border-ink/10 p-5">
          <div className="flex justify-between items-center mb-3">
            <div>
              <h3 className="text-sm font-semibold text-ink">
                Upcoming Meetings
              </h3>
              <LastUpdated at={lastUpdated.calendar} />
            </div>
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
                      setLastUpdated((prev) => ({ ...prev, calendar: new Date() }));
                      setToast("Calendar synced successfully");
                    }
                  } catch (err) {
                    if (!isAbortError(err)) setToast("Could not sync calendar");
                  }
                  setSyncingCalendar(false);
                  calendarAbortRef.current = null;
                }}
                className="p-2 text-ink-muted hover:text-primary-700 hover:bg-cream-200 rounded-md transition-colors disabled:opacity-50"
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
                  <li key={event.id} className="border-l-2 border-primary-700 pl-3 flex justify-between items-start group">
                    <div>
                      <p className="font-medium text-ink">{event.title}</p>
                      <p className="font-mono text-xs text-ink-muted">{dateStr}</p>
                    </div>
                    <button
                      onClick={() => archiveEvent(event.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-ink-muted hover:text-red-600 transition-opacity"
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
            <p className="text-ink-muted">No upcoming meetings.</p>
          )}
          </div>

          <div className="bg-cream-50 rounded-md border border-ink/10 p-5">
          <div className="flex justify-between items-center mb-3">
            <div>
              <h3 className="text-sm font-semibold text-ink">
                Recent Emails
              </h3>
              <LastUpdated at={lastUpdated.emails} />
            </div>
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
                      setLastUpdated((prev) => ({ ...prev, emails: new Date() }));
                      setToast("Emails synced successfully");
                    }
                  } catch (err) {
                    if (!isAbortError(err)) setToast("Could not sync emails");
                  }
                  setSyncingEmails(false);
                  emailsAbortRef.current = null;
                }}
                className="p-2 text-ink-muted hover:text-primary-700 hover:bg-cream-200 rounded-md transition-colors disabled:opacity-50"
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
                <li key={email.id} className="border-b border-ink/10 pb-2 flex justify-between items-start group">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink text-sm">
                      {email.subject}
                    </p>
                    <p className="text-xs text-ink-muted">{email.sender}</p>
                    <p className="text-xs text-ink-muted/70 truncate">
                      {email.snippet}
                    </p>
                  </div>
                  <button
                    onClick={() => archiveEmail(email.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-ink-muted hover:text-red-600 transition-opacity flex-shrink-0 ml-2"
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
            <p className="text-ink-muted">No emails synced yet.</p>
          )}
          </div>
          </div>
        </section>
      </div>
    </PageShell>
  );
}
