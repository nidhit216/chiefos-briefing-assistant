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
        <h1 className="text-2xl font-bold text-gray-900">Semantic Search</h1>
        <button
          onClick={embedData}
          disabled={embedding}
          className="text-sm bg-purple-100 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-200 disabled:opacity-50 transition-colors"
        >
          {embedding ? "Embedding..." : "Re-embed all data"}
        </button>
      </div>

      <p className="text-sm text-gray-500 mb-6">
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
          className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        />
        <button
          onClick={search}
          disabled={searching || !query.trim()}
          className="bg-purple-600 text-white px-6 py-3 rounded-xl hover:bg-purple-700 disabled:opacity-50 transition-colors"
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
            className={`text-sm px-3 py-1 rounded-lg transition-colors ${
              filter === f.value
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
              className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  {sourceIcon(r.source_type)} {r.source_type.replace("_", " ")}
                </span>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  {Math.round(r.similarity * 100)}% match
                </span>
              </div>
              <p className="text-sm text-gray-800 whitespace-pre-line line-clamp-4">
                {r.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && query && !searching && (
        <p className="text-center text-gray-400 mt-10">
          No results found. Try embedding your data first.
        </p>
      )}
    </PageShell>
  );
}
