"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import Toast from "@/app/components/Toast";
import type { SearchResult } from "@/types";

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [embedding, setEmbedding] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) router.push("/login");
  }, [router]);

  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const params = new URLSearchParams({ q: query, limit: "15" });
      if (filter) params.set("source_type", filter);
      const res = await apiFetch(`/search/?${params}`);
      if (res.ok) {
        setResults(await res.json());
      } else {
        const err = await res.json().catch(() => null);
        setToast(err?.detail || "Search failed");
      }
    } catch (_) {
      setToast("Could not reach server");
    } finally {
      setSearching(false);
    }
  };

  const embedData = async () => {
    setEmbedding(true);
    try {
      const res = await apiFetch("/search/embed", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setToast(data.message);
      } else {
        const err = await res.json().catch(() => null);
        setToast(err?.detail || "Embedding failed");
      }
    } catch (_) {
      setToast("Could not reach server");
    } finally {
      setEmbedding(false);
    }
  };

  const sourceIcon = (type: string) => {
    switch (type) {
      case "email": return "📧";
      case "note": return "📝";
      case "calendar_event": return "📅";
      default: return "📄";
    }
  };

  return (
    <PageShell maxWidth="max-w-4xl">
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      <div className="flex items-center justify-between mb-4">
        <h1 className="font-serif text-3xl text-ink">Semantic Search</h1>
        <button
          onClick={embedData}
          disabled={embedding}
          className="text-sm bg-primary-100 text-primary-800 px-3 py-1.5 rounded-md hover:bg-primary-200 disabled:opacity-50 transition-colors"
        >
          {embedding ? "Embedding..." : "Re-embed all data"}
        </button>
      </div>

      <p className="text-sm text-ink-muted mb-6">
        Search across your emails, notes, and calendar using natural language. Results are ranked by relevance using vector similarity.
      </p>

      {/* Search bar */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="Search your data semantically..."
          className="flex-1 border border-ink/20 rounded-md px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent"
        />
        <button
          onClick={search}
          disabled={searching || !query.trim()}
          className="bg-primary-700 text-white px-6 py-3 rounded-md hover:bg-primary-800 disabled:opacity-50 transition-colors"
        >
          {searching ? "..." : "Search"}
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-6">
        {[
          { value: "", label: "All" },
          { value: "email", label: "📧 Emails" },
          { value: "note", label: "📝 Notes" },
          { value: "calendar_event", label: "📅 Calendar" },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`text-sm px-3 py-1 rounded-md transition-colors ${
              filter === f.value
                ? "bg-primary-700 text-white"
                : "bg-cream-200 text-ink-muted hover:bg-cream-300"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r) => (
            <div
              key={r.id}
              className="bg-cream-50 border border-ink/10 rounded-md p-4 hover:border-ink/20 transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ink-muted">
                  {sourceIcon(r.source_type)} {r.source_type.replace("_", " ")}
                </span>
                <span className="font-mono text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  {Math.round(r.similarity * 100)}% match
                </span>
              </div>
              <p className="text-sm text-ink whitespace-pre-line line-clamp-4">
                {r.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && query && !searching && (
        <p className="text-center text-ink-muted/70 mt-10">
          No results found. Try embedding your data first.
        </p>
      )}
    </PageShell>
  );
}
