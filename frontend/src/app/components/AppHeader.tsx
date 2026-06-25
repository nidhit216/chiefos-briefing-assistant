"use client";

export default function AppHeader({ userName }: { userName?: string }) {
  if (!userName) return null;

  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <header className="mb-8 pb-6 border-b border-ink/10">
      <h1 className="font-serif text-3xl text-ink">Good morning, {userName}</h1>
      <p className="mt-1.5 font-mono text-xs uppercase tracking-widest text-ink-muted">
        {today}
      </p>
    </header>
  );
}
