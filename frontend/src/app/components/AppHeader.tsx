"use client";

export default function AppHeader({ userName }: { userName?: string }) {
  if (!userName) return null;

  return (
    <header className="mb-6">
      <p className="text-gray-500">Good morning, {userName}</p>
    </header>
  );
}
