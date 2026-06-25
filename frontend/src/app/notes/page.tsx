"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import DOMPurify from "dompurify";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import NoteEditor from "@/app/components/NoteEditor";
import TagInput from "@/app/components/TagInput";
import type { Note } from "@/types";

function isOverdue(dueDate: string | null) {
  if (!dueDate) return false;
  return new Date(dueDate) < new Date(new Date().toDateString());
}

export default function NotesPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<Note[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [dueDate, setDueDate] = useState("");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editDueDate, setEditDueDate] = useState("");

  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [dueBefore, setDueBefore] = useState("");

  const loadNotes = useCallback(async (filterTags: string[], filterDueBefore: string) => {
    const params = new URLSearchParams();
    filterTags.forEach((t) => params.append("tags", t));
    if (filterDueBefore) params.append("due_before", filterDueBefore);
    const qs = params.toString();
    const res = await apiFetch(`/notes/${qs ? `?${qs}` : ""}`);
    if (res.ok) setNotes(await res.json());
    else router.push("/login");
  }, [router]);

  useEffect(() => {
    loadNotes(selectedTags, dueBefore);
  }, [loadNotes, selectedTags, dueBefore]);

  const allTags = useMemo(() => {
    const set = new Set<string>();
    notes.forEach((n) => n.tags?.forEach((t) => set.add(t)));
    return Array.from(set).sort();
  }, [notes]);

  const sortedNotes = useMemo(
    () => [...notes].sort((a, b) => Number(a.completed) - Number(b.completed)),
    [notes]
  );

  async function toggleCompleted(note: Note) {
    setNotes((prev) =>
      prev.map((n) => (n.id === note.id ? { ...n, completed: !n.completed } : n))
    );
    const res = await apiFetch(`/notes/${note.id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: note.title,
        content: note.content,
        tags: note.tags,
        due_date: note.due_date,
        completed: !note.completed,
      }),
    });
    if (!res.ok) loadNotes(selectedTags, dueBefore);
  }

  function toggleTagFilter(tag: string) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function createNote(e: React.FormEvent) {
    e.preventDefault();
    const res = await apiFetch("/notes/", {
      method: "POST",
      body: JSON.stringify({
        title,
        content,
        tags: tags.length ? tags : null,
        due_date: dueDate || null,
      }),
    });
    if (res.ok) {
      setTitle("");
      setContent("");
      setTags([]);
      setDueDate("");
      setShowCreate(false);
      loadNotes(selectedTags, dueBefore);
    }
  }

  function startEdit(note: Note) {
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditContent(note.content);
    setEditTags(note.tags || []);
    setEditDueDate(note.due_date || "");
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(id: string) {
    const res = await apiFetch(`/notes/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: editTitle,
        content: editContent,
        tags: editTags,
        due_date: editDueDate || null,
      }),
    });
    if (res.ok) {
      setEditingId(null);
      loadNotes(selectedTags, dueBefore);
    }
  }

  async function deleteNote(id: string) {
    await apiFetch(`/notes/${id}`, { method: "DELETE" });
    loadNotes(selectedTags, dueBefore);
  }

  return (
    <PageShell maxWidth="max-w-4xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-serif text-3xl text-ink">Notes</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700"
        >
          {showCreate ? "Cancel" : "+ New Note"}
        </button>
      </div>

      {(allTags.length > 0 || notes.length > 0) && (
        <div className="bg-cream-50 border border-ink/10 rounded-md p-4 mb-6 flex flex-wrap items-center gap-3">
          {allTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {allTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTagFilter(tag)}
                  className={`text-xs px-2 py-1 rounded transition-colors ${
                    selectedTags.includes(tag)
                      ? "bg-primary-600 text-white"
                      : "bg-cream-200 text-ink-muted hover:bg-cream-300"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 ml-auto">
            <label className="text-xs text-ink-muted">Due by</label>
            <input
              type="date"
              value={dueBefore}
              onChange={(e) => setDueBefore(e.target.value)}
              className="text-xs border border-ink/20 rounded-md px-2 py-1"
            />
            {(selectedTags.length > 0 || dueBefore) && (
              <button
                onClick={() => {
                  setSelectedTags([]);
                  setDueBefore("");
                }}
                className="text-xs text-ink-muted hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <form onSubmit={createNote} className="bg-cream-50 border border-ink/10 rounded-md p-6 mb-6">
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full border border-ink/20 rounded-md px-4 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <NoteEditor content={content} onChange={setContent} />
          <TagInput tags={tags} onChange={setTags} />
          <div className="flex items-center gap-2 mb-4">
            <label className="text-sm text-ink-muted">Due date (optional)</label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="text-sm border border-ink/20 rounded-md px-2 py-1"
            />
            {dueDate && (
              <button
                type="button"
                onClick={() => setDueDate("")}
                className="text-xs text-ink-muted hover:underline"
              >
                Clear
              </button>
            )}
          </div>
          <button
            type="submit"
            className="bg-primary-600 text-white px-6 py-2 rounded-md hover:bg-primary-700"
          >
            Save Note
          </button>
        </form>
      )}

      <div className="space-y-4">
        {sortedNotes.map((note) =>
          editingId === note.id ? (
            <div key={note.id} className="bg-cream-50 border border-ink/10 rounded-md p-6">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full border border-ink/20 rounded-md px-4 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <NoteEditor content={editContent} onChange={setEditContent} />
              <TagInput tags={editTags} onChange={setEditTags} />
              <div className="flex items-center gap-2 mb-4">
                <label className="text-sm text-ink-muted">Due date (optional)</label>
                <input
                  type="date"
                  value={editDueDate}
                  onChange={(e) => setEditDueDate(e.target.value)}
                  className="text-sm border border-ink/20 rounded-md px-2 py-1"
                />
                {editDueDate && (
                  <button
                    type="button"
                    onClick={() => setEditDueDate("")}
                    className="text-xs text-ink-muted hover:underline"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => saveEdit(note.id)}
                  className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700"
                >
                  Save
                </button>
                <button
                  onClick={cancelEdit}
                  className="border border-ink/20 px-4 py-2 rounded-md hover:bg-cream-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div key={note.id} className="bg-cream-50 border border-ink/10 rounded-md p-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={note.completed}
                      onChange={() => toggleCompleted(note)}
                      className="mt-1.5 h-4 w-4 rounded border-ink/20 text-primary-600 focus:ring-primary-500"
                    />
                    <h2
                      className={`text-lg font-semibold ${
                        note.completed ? "line-through text-ink-muted/70" : "text-ink"
                      }`}
                    >
                      {note.title}
                    </h2>
                  </div>
                  <div
                    className="prose-sm max-w-none text-ink-muted mt-1"
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(note.content) }}
                  />
                  <div className="flex gap-2 mt-3 flex-wrap items-center">
                    {note.tags?.map((tag) => (
                      <span
                        key={tag}
                        className="font-mono text-[11px] bg-cream-200 text-ink-muted px-2 py-1 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {note.due_date && (
                      <span
                        className={`font-mono text-xs px-2 py-1 rounded ${
                          isOverdue(note.due_date)
                            ? "bg-red-50 text-red-700"
                            : "bg-primary-50 text-primary-700"
                        }`}
                      >
                        Due {new Date(note.due_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-xs text-ink-muted/70 mt-2">
                    Updated {new Date(note.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-3 flex-shrink-0 ml-4">
                  <button
                    onClick={() => startEdit(note)}
                    className="text-primary-600 text-sm hover:underline"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteNote(note.id)}
                    className="text-red-500 text-sm hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )
        )}
        {notes.length === 0 && (
          <p className="text-ink-muted text-center py-8">
            No notes yet. Create your first note!
          </p>
        )}
      </div>
    </PageShell>
  );
}
