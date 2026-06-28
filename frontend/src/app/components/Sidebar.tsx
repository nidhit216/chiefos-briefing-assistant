"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { User } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConnectedApp {
  name: string;
  letter: string;
  color: string;
  comingSoon?: boolean;
}

const CONNECTED_APPS: ConnectedApp[] = [
  { name: "Gmail", letter: "M", color: "bg-red-100 text-red-700" },
  { name: "Google Calendar", letter: "C", color: "bg-blue-100 text-blue-700" },
  { name: "Slack", letter: "S", color: "bg-purple-100 text-purple-700", comingSoon: true },
  { name: "Notion", letter: "N", color: "bg-ink/10 text-ink", comingSoon: true },
  { name: "Jira", letter: "J", color: "bg-sky-100 text-sky-700", comingSoon: true },
];

const navLinks = [
  {
    href: "/dashboard",
    label: "Today's Brief",
    subtitle: "Tell me what matters.",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1h3a1 1 0 001-1V10M9 21h6" />
    ),
  },
  {
    href: "/ask",
    label: "Ask Anything",
    subtitle: "Find or understand anything.",
    icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" />,
  },
  {
    href: "/notes",
    label: "Notes",
    subtitle: "Capture new information.",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    ),
  },
  {
    href: "/briefs",
    label: "History",
    subtitle: "See what happened over time.",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
  },
];

function initials(name?: string) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    apiFetch("/auth/me")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data && setUser(data))
      .catch(() => {});
  }, []);

  function logout() {
    localStorage.removeItem("chiefos_token");
    router.push("/login");
  }

  return (
    <aside className="hidden md:flex fixed left-0 top-0 h-screen w-60 flex-col border-r border-ink/10 bg-cream-50">
      <div className="px-6 pt-7 pb-5 border-b border-ink/10">
        <span className="font-serif text-xl text-primary-700">ChiefOS</span>
        <p className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
          Office of the CEO
        </p>
      </div>

      <nav className="flex flex-col gap-0.5 px-3 pt-4 flex-1 overflow-y-auto">
        {navLinks.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`nav-item flex items-start gap-3 border-l-2 px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "border-primary-700 bg-primary-50 text-primary-800"
                  : "border-transparent text-ink-muted hover:bg-cream-200 hover:text-ink"
              }`}
            >
              <svg className="w-[18px] h-[18px] flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {link.icon}
              </svg>
              <div className="nav-text flex flex-col">
                <span className={`nav-label leading-tight ${active ? "font-medium text-primary-800" : "text-ink"}`}>
                  {link.label}
                </span>
                <span className="nav-subtitle text-xs text-ink-muted leading-tight mt-0.5">
                  {link.subtitle}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-ink/10 px-3 pt-3 pb-1">
        <p className="px-2 pb-2 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
          Connected Apps
        </p>
        <ul className="space-y-0.5">
          {CONNECTED_APPS.map((app) => {
            const isGoogle = app.name === "Gmail" || app.name === "Google Calendar";
            const connected = isGoogle && !!user?.google_connected;
            return (
              <li
                key={app.name}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 ${
                  app.comingSoon ? "opacity-50" : ""
                }`}
              >
                <span
                  className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-medium ${app.color}`}
                >
                  {app.letter}
                </span>
                <span className="min-w-0 flex-1 truncate text-xs text-ink">{app.name}</span>
                {app.comingSoon ? (
                  <span className="font-mono text-[9px] uppercase tracking-widest text-ink-muted">
                    Soon
                  </span>
                ) : connected ? (
                  <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" title="Connected" />
                ) : (
                  <a
                    href={`${API_URL}/auth/login`}
                    className="flex-shrink-0 font-mono text-[9px] uppercase tracking-widest text-primary-700 hover:underline"
                  >
                    Connect
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border-t border-ink/10 p-3">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-800 font-serif text-xs">
            {initials(user?.name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{user?.name || "..."}</p>
            <p className="truncate font-mono text-[11px] text-ink-muted">{user?.email || ""}</p>
          </div>
        </div>
        <Link
          href="/settings"
          className={`mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors ${
            pathname === "/settings"
              ? "bg-primary-50 text-primary-800"
              : "text-ink-muted hover:bg-cream-200 hover:text-ink"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
        </Link>
        <button
          onClick={logout}
          className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-ink-muted hover:bg-cream-200 hover:text-rose-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Logout
        </button>
      </div>
    </aside>
  );
}
