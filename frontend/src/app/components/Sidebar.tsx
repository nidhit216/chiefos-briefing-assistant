"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { User } from "@/types";
import { useMode } from "@/app/context/ModeContext";

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

const personalLabels: Record<string, { label: string; subtitle: string }> = {
  "/dashboard": { label: "Today", subtitle: "What matters to me." },
  "/ask": { label: "Ask", subtitle: "Find anything." },
  "/notes": { label: "Notes", subtitle: "Capture a thought." },
  "/briefs": { label: "Reflect", subtitle: "Look back." },
};

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
  const { mode, setMode } = useMode();

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
    <aside
      className="hidden md:flex fixed left-0 top-0 h-screen w-60 flex-col border-r"
      style={{ background: "var(--mode-bg-2)", borderColor: "var(--mode-border)" }}
    >
      <div className="px-5 pt-6 pb-4 border-b" style={{ borderColor: "var(--mode-border)" }}>
        <span className="font-serif text-xl" style={{ color: "var(--mode-accent)" }}>
          ChiefOS
        </span>
        <p
          className="mt-0.5 font-mono text-[9px] uppercase tracking-widest"
          style={{ color: "var(--mode-muted)" }}
        >
          {mode === "work" ? "Office of the CEO" : "Your personal space"}
        </p>
      </div>

      <div
        className="mx-3 mt-3 mb-1 flex rounded-lg p-0.5 gap-0.5 transition-colors duration-200"
        style={{ background: "var(--mode-toggle-bg)" }}
      >
        {(["work", "personal"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5
                       text-[11px] font-medium capitalize transition-all duration-150"
            style={
              mode === m
                ? {
                    background: "var(--mode-pill-bg)",
                    color: "var(--mode-pill-text)",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
                  }
                : {
                    background: "transparent",
                    color: "var(--mode-muted)",
                  }
            }
          >
            {m === "work" ? "💼" : "🍑"} {m === "work" ? "Work" : "Me"}
          </button>
        ))}
      </div>

      <nav className="flex flex-col gap-0.5 px-3 pt-4 flex-1 overflow-y-auto">
        {navLinks.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          const displayLabel =
            mode === "personal" && personalLabels[link.href]
              ? personalLabels[link.href].label
              : link.label;
          const displaySubtitle =
            mode === "personal" && personalLabels[link.href]
              ? personalLabels[link.href].subtitle
              : link.subtitle;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="nav-item flex items-start gap-3 border-l-2 px-3 py-2.5 text-sm transition-colors"
              style={
                active
                  ? {
                      borderLeftColor: "var(--mode-accent)",
                      background: "var(--mode-accent-light)",
                      color: "var(--mode-accent-text)",
                    }
                  : {
                      borderLeftColor: "transparent",
                      color: "var(--mode-muted)",
                    }
              }
            >
              <svg
                className="w-[18px] h-[18px] flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                style={{ color: active ? "var(--mode-accent)" : "var(--mode-muted)" }}
              >
                {link.icon}
              </svg>
              <div className="nav-text flex flex-col">
                <span
                  className="nav-label leading-tight"
                  style={{
                    fontWeight: active ? 500 : 400,
                    color: active ? "var(--mode-accent-text)" : "var(--mode-text)",
                  }}
                >
                  {displayLabel}
                </span>
                <span
                  className="nav-subtitle text-xs leading-tight mt-0.5"
                  style={{ color: "var(--mode-muted)" }}
                >
                  {displaySubtitle}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-3" style={{ borderColor: "var(--mode-border)" }}>
        <div className="flex items-center gap-2 px-2 py-2">
          <div
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full font-serif text-xs"
            style={{ background: "var(--mode-accent)", color: "var(--mode-pill-text)" }}
          >
            {initials(user?.name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium" style={{ color: "var(--mode-text)" }}>
              {user?.name || "..."}
            </p>
            <p className="truncate font-mono text-[11px]" style={{ color: "var(--mode-muted)" }}>
              {user?.email || ""}
            </p>
          </div>
        </div>
        <Link
          href="/settings"
          className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors"
          style={
            pathname === "/settings"
              ? { background: "var(--mode-accent-light)", color: "var(--mode-accent-text)" }
              : { color: "var(--mode-muted)" }
          }
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
        </Link>
        <button
          onClick={logout}
          className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:text-rose-700"
          style={{ color: "var(--mode-muted)" }}
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
