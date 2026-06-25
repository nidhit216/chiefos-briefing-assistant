"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import type { ChatMessage, ChatResponse, ChatSession, Memory } from "@/types";

const markdownComponents = {
  p: ({ ...props }) => <p className="mb-2 last:mb-0" {...props} />,
  ul: ({ ...props }) => <ul className="list-disc pl-5 mb-2 space-y-0.5" {...props} />,
  ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5" {...props} />,
  li: ({ ...props }) => <li {...props} />,
  strong: ({ ...props }) => <strong className="font-semibold" {...props} />,
  a: ({ ...props }) => <a className="text-primary-700 underline" target="_blank" rel="noreferrer" {...props} />,
  code: ({ ...props }) => <code className="bg-cream-200 rounded px-1 py-0.5 text-xs" {...props} />,
  table: ({ ...props }) => <table className="border-collapse border border-ink/10 mb-2 text-xs" {...props} />,
  th: ({ ...props }) => <th className="border border-ink/10 px-2 py-1 bg-cream-100 text-left" {...props} />,
  td: ({ ...props }) => <td className="border border-ink/10 px-2 py-1" {...props} />,
};

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sourcesUsed, setSourcesUsed] = useState(0);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [showMemory, setShowMemory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadSessions = useCallback(async () => {
    const res = await apiFetch("/chat/history");
    if (res.ok) setSessions(await res.json());
  }, []);

  const loadMemories = useCallback(async () => {
    const res = await apiFetch("/memories/");
    if (res.ok) setMemories(await res.json());
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadSessions();
    loadMemories();
  }, [router, loadSessions, loadMemories]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setSourcesUsed(0);
  };

  const openSession = async (id: string) => {
    const res = await apiFetch(`/chat/history?session_id=${id}`);
    if (res.ok) {
      const history: { role: "user" | "assistant"; content: string; created_at: string }[] =
        await res.json();
      setMessages(history.map((m) => ({ role: m.role, content: m.content, created_at: m.created_at })));
      setSessionId(id);
      setSourcesUsed(0);
    }
  };

  const deleteMemory = async (id: string) => {
    await apiFetch(`/memories/${id}`, { method: "DELETE" });
    setMemories((prev) => prev.filter((m) => m.id !== id));
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await apiFetch("/chat/", {
        method: "POST",
        body: JSON.stringify({
          message: input,
          session_id: sessionId,
        }),
      });

      if (res.ok) {
        const data: ChatResponse = await res.json();
        setSessionId(data.session_id);
        setSourcesUsed(data.sources_used);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.reply },
        ]);
        loadSessions();
        loadMemories();
      } else {
        const err = await res.json().catch(() => null);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${err?.detail || "Something went wrong"}`,
          },
        ]);
      }
    } catch (_) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Could not reach the server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
    <div className="flex gap-6 h-[calc(100vh-4rem)]">
      {/* Session list + memory panel */}
      <div className="hidden lg:flex flex-col w-56 flex-shrink-0 gap-4 overflow-y-auto">
        <div>
          <button
            onClick={startNewChat}
            className="w-full text-sm bg-primary-700 text-white px-3 py-2 rounded-md hover:bg-primary-800 transition-colors mb-2"
          >
            + New chat
          </button>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => openSession(s.session_id)}
                className={`w-full text-left text-xs px-2 py-2 rounded-md transition-colors truncate ${
                  sessionId === s.session_id
                    ? "bg-primary-50 text-primary-800"
                    : "text-ink-muted hover:bg-cream-200"
                }`}
                title={s.last_message}
              >
                {s.last_message || "New conversation"}
              </button>
            ))}
            {sessions.length === 0 && (
              <p className="text-xs text-ink-muted/70 px-2">No past chats yet.</p>
            )}
          </div>
        </div>

        <div>
          <button
            onClick={() => setShowMemory((v) => !v)}
            className="text-xs font-medium text-ink-muted hover:text-ink-muted mb-2"
          >
            {showMemory ? "▾" : "▸"} What ChiefOS remembers ({memories.length})
          </button>
          {showMemory && (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {memories.map((m) => (
                <div
                  key={m.id}
                  className="flex items-start justify-between gap-1 text-xs bg-cream-100 rounded-md px-2 py-1.5"
                >
                  <span className="text-ink-muted">{m.content}</span>
                  <button
                    onClick={() => deleteMemory(m.id)}
                    className="text-ink-muted/70 hover:text-red-500 flex-shrink-0"
                    title="Forget this"
                  >
                    ✕
                  </button>
                </div>
              ))}
              {memories.length === 0 && (
                <p className="text-xs text-ink-muted/70 px-2">Nothing remembered yet.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chat */}
      <div className="flex flex-col flex-1 min-w-0 h-full">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-serif text-3xl text-ink">Chat with your data</h1>
          {sourcesUsed > 0 && (
            <span className="text-xs bg-primary-100 text-primary-800 px-2 py-1 rounded">
              {sourcesUsed} sources used
            </span>
          )}
        </div>

        <p className="text-sm text-ink-muted mb-4">
          Ask questions about your emails, calendar, and notes. Powered by RAG semantic search.
        </p>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-cream-50 border border-ink/10 rounded-md p-4 mb-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-ink-muted/70">
              <p className="text-lg">Ask me anything about your data</p>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 max-w-md mx-auto">
                {[
                  "What should I focus on today?",
                  "When is my next meeting with the team?",
                  "Summarize my recent emails",
                  "What deadlines are coming up?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="text-sm text-left bg-cream-100 border border-ink/10 rounded-md p-2 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`mb-3 flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-md px-4 py-2 ${
                  msg.role === "user"
                    ? "bg-primary-700 text-white"
                    : "bg-white border border-ink/10 text-ink"
                }`}
              >
                {msg.role === "assistant" ? (
                  <div className="text-sm">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start mb-3">
              <div className="bg-white border border-ink/10 rounded-md px-4 py-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-ink-muted rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask about your emails, calendar, notes..."
            className="flex-1 border border-ink/20 rounded-md px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-primary-700 text-white px-6 py-3 rounded-md hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    </PageShell>
  );
}
