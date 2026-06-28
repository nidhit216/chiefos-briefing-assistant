"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import Toast from "@/app/components/Toast";
import type { SearchResult, ChatResponse, DraftPayload } from "@/types";

const FILTERS = [
  { value: "", label: "All" },
  { value: "email", label: "Emails" },
  { value: "calendar_event", label: "Calendar" },
  { value: "note", label: "Notes" },
];

const SUGGESTIONS = [
  "What should I focus on today?",
  "Any blockers I'm missing?",
  "Summarise my emails this week",
  "What deadlines are coming up?",
];

const SOURCE_LABEL: Record<string, string> = {
  email: "Email",
  calendar_event: "Calendar",
  note: "Note",
};

const SOURCE_BADGE_STYLE: Record<string, string> = {
  email: "bg-blue-100 text-blue-700",
  calendar_event: "bg-green-100 text-green-700",
  note: "bg-amber-100 text-amber-700",
};

const markdownComponents = {
  p: ({ ...props }) => <p className="mb-3 last:mb-0" {...props} />,
  ul: ({ ...props }) => <ul className="list-disc pl-5 mb-3 space-y-0.5" {...props} />,
  ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-0.5" {...props} />,
  li: ({ ...props }) => <li {...props} />,
  strong: ({ ...props }) => <strong className="font-semibold" {...props} />,
  a: ({ ...props }) => <a className="text-primary-700 underline" target="_blank" rel="noreferrer" {...props} />,
  code: ({ ...props }) => <code className="bg-cream-200 rounded px-1 py-0.5 text-xs" {...props} />,
  table: ({ ...props }) => (
    <div className="overflow-x-auto mb-3 border border-ink/10 rounded-md">
      <table className="w-full text-sm border-collapse" {...props} />
    </div>
  ),
  thead: ({ ...props }) => <thead className="bg-cream-100" {...props} />,
  th: ({ ...props }) => (
    <th className="text-left font-semibold px-3 py-2 border-b border-ink/10 align-top whitespace-normal" {...props} />
  ),
  td: ({ ...props }) => (
    <td className="px-3 py-2 border-b border-ink/5 align-top whitespace-normal break-words" {...props} />
  ),
};

function cardTitle(content: string) {
  const firstLine = content.split("\n").find((l) => l.trim().length > 0) || content;
  return firstLine.length > 72 ? `${firstLine.slice(0, 72)}…` : firstLine;
}

interface Turn {
  id: string;
  query: string;
  answer?: string;
  sources: SearchResult[];
  draft?: DraftPayload;
  loading: boolean;
  error?: string;
}

function FilterPills({ filter, onChange }: { filter: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-2">
      {FILTERS.map((f) => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
            filter === f.value
              ? "bg-primary-700 text-white border-primary-700"
              : "border-ink/15 text-ink-muted hover:bg-cream-200"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

function AskInputBar({
  size = "compact",
  placeholder,
  value,
  onChange,
  onSubmit,
  disabled,
}: {
  size?: "large" | "compact";
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  const large = size === "large";
  return (
    <div className="flex gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        placeholder={placeholder}
        disabled={disabled}
        className={`flex-1 border border-ink/20 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent bg-white ${
          large ? "px-5 py-4 text-base" : "px-4 py-2.5 text-sm"
        }`}
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className={`bg-primary-700 text-white rounded-md hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
          large ? "px-6 py-4" : "px-5 py-2.5 text-sm"
        }`}
      >
        Ask
      </button>
    </div>
  );
}

function DraftCard({
  draft,
  onChange,
}: {
  draft: DraftPayload;
  onChange: (field: keyof DraftPayload, value: string) => void;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(draft.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const mailtoHref = `mailto:${encodeURIComponent(draft.to)}?subject=${encodeURIComponent(
    draft.subject
  )}&body=${encodeURIComponent(draft.body)}`;

  return (
    <div className="border border-primary-300 rounded-md p-4 bg-primary-50">
      <p className="font-mono text-[10px] uppercase tracking-widest text-primary-700 mb-3">Draft Email</p>
      <div className="space-y-2 mb-3">
        <input
          value={draft.to}
          onChange={(e) => onChange("to", e.target.value)}
          placeholder="To"
          className="w-full text-sm px-3 py-2 rounded-md border border-ink/15 bg-white focus:outline-none focus:ring-2 focus:ring-primary-600"
        />
        <input
          value={draft.subject}
          onChange={(e) => onChange("subject", e.target.value)}
          placeholder="Subject"
          className="w-full text-sm px-3 py-2 rounded-md border border-ink/15 bg-white focus:outline-none focus:ring-2 focus:ring-primary-600"
        />
        <textarea
          value={draft.body}
          onChange={(e) => onChange("body", e.target.value)}
          rows={8}
          className="w-full text-sm px-3 py-2 rounded-md border border-ink/15 bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 whitespace-pre-wrap"
        />
      </div>
      <div className="flex gap-2">
        <a
          href={mailtoHref}
          className="text-sm px-4 py-2 rounded-md bg-primary-700 text-white hover:bg-primary-800 transition-colors"
        >
          Open in email
        </a>
        <button
          onClick={copy}
          className="text-sm px-4 py-2 rounded-md border border-ink/15 hover:bg-cream-200 transition-colors"
        >
          {copied ? "Copied" : "Copy body"}
        </button>
      </div>
    </div>
  );
}

function SourceCard({ result }: { result: SearchResult }) {
  const label = SOURCE_LABEL[result.source_type] || result.source_type;
  const badgeClass = SOURCE_BADGE_STYLE[result.source_type] || "bg-cream-200 text-ink-muted";
  return (
    <div className="border border-ink/10 rounded-md p-4 bg-cream-50">
      <div className="flex items-center justify-between mb-2">
        <span className={`text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded ${badgeClass}`}>
          {label}
        </span>
        <span className="text-xs text-ink-muted">{Math.round(result.similarity * 100)}% match</span>
      </div>
      <p className="text-sm font-medium text-ink mb-1">{cardTitle(result.content)}</p>
      <p className="text-sm text-ink-muted line-clamp-2 whitespace-pre-line">{result.content}</p>
    </div>
  );
}

export default function AskPage() {
  const router = useRouter();
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) router.push("/login");
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const runQuery = useCallback(
    async (raw: string) => {
      const q = raw.trim();
      if (!q || submitting) return;

      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

      setTurns((prev) => [...prev, { id, query: q, sources: [], loading: true }]);
      setInput("");
      setSubmitting(true);

      try {
        const chatRes = await apiFetch("/chat/", {
          method: "POST",
          body: JSON.stringify({ message: q, session_id: sessionId, source_type: filter || undefined }),
        });

        if (chatRes.ok) {
          const data: ChatResponse = await chatRes.json();
          setSessionId(data.session_id);
          setTurns((prev) =>
            prev.map((t) =>
              t.id === id
                ? { ...t, answer: data.reply || undefined, sources: data.sources || [], draft: data.draft || undefined, loading: false }
                : t
            )
          );
        } else {
          const err = await chatRes.json().catch(() => null);
          setTurns((prev) =>
            prev.map((t) =>
              t.id === id ? { ...t, error: err?.detail || "Something went wrong", loading: false } : t
            )
          );
        }
      } catch (_) {
        setTurns((prev) =>
          prev.map((t) => (t.id === id ? { ...t, error: "Could not reach the server", loading: false } : t))
        );
        setToast("Could not reach the server");
      } finally {
        setSubmitting(false);
      }
    },
    [filter, sessionId, submitting]
  );

  const updateDraft = useCallback((turnId: string, field: keyof DraftPayload, value: string) => {
    setTurns((prev) =>
      prev.map((t) => (t.id === turnId && t.draft ? { ...t, draft: { ...t.draft, [field]: value } } : t))
    );
  }, []);

  const empty = turns.length === 0;

  return (
    <PageShell maxWidth="max-w-3xl">
      {toast && <Toast message={toast} onClose={() => setToast(null)} type="error" />}

      {empty ? (
        <div className="min-h-[70vh] flex flex-col items-center justify-center gap-6">
          <div className="text-center">
            <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-2">Ask ChiefOS</p>
            <h1 className="font-serif text-3xl text-ink">What do you want to know?</h1>
          </div>

          <FilterPills filter={filter} onChange={setFilter} />

          <div className="w-full">
            <AskInputBar
              size="large"
              placeholder="Search or ask anything about your emails, calendar, notes..."
              value={input}
              onChange={setInput}
              onSubmit={() => runQuery(input)}
              disabled={submitting}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => runQuery(s)}
                className="text-sm text-left bg-cream-100 border border-ink/10 rounded-md p-3 hover:border-primary-300 hover:bg-primary-50 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div>
          <div className="mb-6">
            <FilterPills filter={filter} onChange={setFilter} />
          </div>

          <div className="py-6 pb-28">
            {turns.map((turn) => (
              <div key={turn.id} className="pb-8 mb-8 border-b border-ink/10 last:border-0 last:pb-0 last:mb-0">
                <p className="font-serif text-xl text-ink mb-3">{turn.query}</p>

                {turn.loading && (
                  <div className="flex gap-1 mb-4">
                    <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                )}

                {turn.error && <p className="text-sm text-rose-700 mb-4">{turn.error}</p>}

                {turn.answer && (
                  <div className="text-ink text-[15px] leading-relaxed mb-5">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw, [rehypeSanitize, defaultSchema]]}
                      components={markdownComponents}
                    >
                      {turn.answer}
                    </ReactMarkdown>
                  </div>
                )}

                {turn.draft && (
                  <div className="mb-5">
                    <DraftCard draft={turn.draft} onChange={(field, value) => updateDraft(turn.id, field, value)} />
                  </div>
                )}

                {turn.sources.length > 0 && (
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-2">Sources</p>
                    <div className="space-y-3">
                      {turn.sources.map((s) => (
                        <SourceCard key={s.id} result={s} />
                      ))}
                    </div>
                  </div>
                )}

                {!turn.loading && !turn.error && !turn.answer && !turn.draft && turn.sources.length === 0 && (
                  <p className="text-sm text-ink-muted/70">No results found.</p>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="fixed bottom-0 left-0 right-0 md:left-60 z-20 bg-cream-50/95 backdrop-blur-sm border-t border-ink/10">
            <div className="max-w-3xl mx-auto px-8 py-4">
              <AskInputBar
                placeholder="Ask a follow-up..."
                value={input}
                onChange={setInput}
                onSubmit={() => runQuery(input)}
                disabled={submitting}
              />
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
