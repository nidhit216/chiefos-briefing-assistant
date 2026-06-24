"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AppHeader({ userName }: { userName?: string }) {
  const pathname = usePathname();

  const navLinks = [
    { href: "/search", label: "Search" },
    { href: "/chat", label: "Chat" },
    { href: "/notes", label: "Notes" },
    { href: "/briefs", label: "Briefs" },
  ];

  return (
    <header className="flex justify-between items-center mb-8">
      <div>
        <Link href="/dashboard">
          <h1 className="text-3xl font-bold text-gray-900 hover:text-primary-600 transition-colors cursor-pointer">
            ChiefOS
          </h1>
        </Link>
        {userName && (
          <p className="text-gray-500">Good morning, {userName}</p>
        )}
      </div>
      <nav className="flex gap-4">
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`hover:underline ${pathname === link.href ? "text-primary-800 font-medium" : "text-primary-600"}`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
