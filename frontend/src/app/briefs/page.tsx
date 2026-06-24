"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import type { DailyBrief, BriefContent } from "@/types";

export default function BriefsPage() {
  const router = useRouter();
  const [briefs, setBriefs] = useState<DailyBrief[]>([]);
  const [selected, setSelected] = useState<BriefContent | null>(null);
  const [selectedBriefId, setSelectedBriefId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

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

  function selectBrief(brief: DailyBrief) {
    const parsed = JSON.parse(brief.content);
    setSelected({
      priorities: parsed.priorities || [],
      focus_areas: parsed.focus_areas || [],
      time_critical: parsed.time_critical || [],
      coming_soon: parsed.coming_soon || [],
    });
    setSelectedBriefId(brief.id);
    setFeedback("");
    setFeedbackSent(false);
  }

  async function deleteBrief(id: string) {
    await apiFetch(`/briefs/${id}`, { method: "DELETE" });
    setBriefs((prev) => prev.filter((b) => b.id !== id));
    if (selectedBriefId === id) {
      setSelected(null);
      setSelectedBriefId(null);
    }
  }

  async function submitFeedback() {
    if (!selectedBriefId || !feedback.trim()) return;
    setSubmittingFeedback(true);
    try {
      const res = await apiFetch(`/briefs/${selectedBriefId}/feedback`, {
        method: "POST",
        body: JSON.stringify({ content: feedback.trim() }),
      });
      if (res.ok) {
        setFeedback("");
        setFeedbackSent(true);
      }
    } finally {
      setSubmittingFeedback(false);
    }
  }

  return (
    <PageShell maxWidth="max-w-4xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Brief History</h2>

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
            <div
              key={brief.id}
              className={`group w-full text-left bg-white rounded-lg shadow p-3 flex items-start justify-between gap-2 cursor-pointer hover:ring-2 hover:ring-primary-500 ${
                selectedBriefId === brief.id ? "ring-2 ring-primary-500" : ""
              }`}
              onClick={() => selectBrief(brief)}
            >
              <div>
                <p className="font-medium text-gray-900">{brief.brief_date}</p>
                <p className="text-xs text-gray-500">
                  {new Date(brief.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteBrief(brief.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity flex-shrink-0"
                title="Delete brief"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </button>
            </div>
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

              <div className="border-t border-gray-100 pt-4">
                <h3 className="font-medium text-gray-900 mb-1">Give feedback on this brief</h3>
                <p className="text-xs text-gray-500 mb-2">
                  ChiefOS will remember this and take it into account in future briefs.
                </p>
                <textarea
                  value={feedback}
                  onChange={(e) => {
                    setFeedback(e.target.value);
                    setFeedbackSent(false);
                  }}
                  placeholder="e.g. Don't include focus areas about email cleanup."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                />
                <div className="flex items-center gap-3 mt-2">
                  <button
                    onClick={submitFeedback}
                    disabled={submittingFeedback || !feedback.trim()}
                    className="bg-primary-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submittingFeedback ? "Saving..." : "Send feedback"}
                  </button>
                  {feedbackSent && (
                    <span className="text-sm text-green-600">Saved — thanks!</span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow p-6 flex items-center justify-center min-h-[200px]">
              <p className="text-gray-400">Select a brief to view details</p>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  );
}
