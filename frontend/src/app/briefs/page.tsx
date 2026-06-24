"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import AppHeader from "@/app/components/AppHeader";
import type { DailyBrief, BriefContent } from "@/types";

export default function BriefsPage() {
  const router = useRouter();
  const [briefs, setBriefs] = useState<DailyBrief[]>([]);
  const [selected, setSelected] = useState<BriefContent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await apiFetch("/briefs/");
        if (res.ok) setBriefs(await res.json());
        else if (res.status === 401) router.push("/login");
        else {
          const err = await res.json().catch(() => null);
          setError(err?.detail || `Failed to load briefs (${res.status}).`);
        }
      } catch (_) {
        setError("Could not reach the server. Please check that the backend is running.");
      }
    }
    load();
  }, [router]);

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <AppHeader />
      <h2 className="text-2xl font-bold text-gray-900 mb-8">Brief History</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {error && (
          <div className="md:col-span-3 rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-start gap-3">
              <span className="text-red-500 text-lg">⚠️</span>
              <div>
                <p className="font-medium text-red-800">Error</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}
        <div className="space-y-2">
          {briefs.map((brief) => (
            <button
              key={brief.id}
              onClick={() => {
                const parsed = JSON.parse(brief.content);
                setSelected({
                  priorities: parsed.priorities || [],
                  focus_areas: parsed.focus_areas || [],
                  time_critical: parsed.time_critical || [],
                  coming_soon: parsed.coming_soon || [],
                });
              }}
              className="w-full text-left bg-white rounded-lg shadow p-3 hover:ring-2 hover:ring-primary-500"
            >
              <p className="font-medium text-gray-900">{brief.brief_date}</p>
              <p className="text-xs text-gray-500">
                {new Date(brief.created_at).toLocaleString()}
              </p>
            </button>
          ))}
          {briefs.length === 0 && (
            <p className="text-gray-500">No briefs generated yet.</p>
          )}
        </div>

        <div className="md:col-span-2">
          {selected ? (
            <div className="bg-white rounded-xl shadow p-6 space-y-4">
              <div>
                <h3 className="font-medium text-green-700 mb-1">Priorities for Today</h3>
                <ul className="space-y-1">
                  {selected.priorities.map((p, i) => (
                    <li key={i} className="text-green-700">{p}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-1">Focus Areas</h3>
                <ul className="space-y-1">
                  {selected.focus_areas.map((f, i) => (
                    <li key={i} className="text-gray-600">{f}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-rose-900 mb-1">Time Critical</h3>
                <ul className="space-y-1">
                  {selected.time_critical.map((item, i) => (
                    <li key={i} className="text-rose-900 flex justify-between">
                      <span>{item.task}</span>
                      <span className="text-xs bg-rose-100 text-rose-800 px-2 py-0.5 rounded">{item.date}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-1">Coming Soon</h3>
                <ul className="space-y-1">
                  {selected.coming_soon.map((item, i) => (
                    <li key={i} className="text-gray-600 flex justify-between">
                      <span>{item.task}</span>
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{item.date}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow p-6 flex items-center justify-center min-h-[200px]">
              <p className="text-gray-400">Select a brief to view details</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
