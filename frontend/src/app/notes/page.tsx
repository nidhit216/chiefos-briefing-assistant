"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import AppHeader from "@/app/components/AppHeader";
import type { Note } from "@/types";

export default function NotesPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<Note[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");

  useEffect(() => {
    loadNotes();
  }, []);

  async function loadNotes() {
    const res = await apiFetch("/notes/");
    if (res.ok) setNotes(await res.json());
    else router.push("/login");
  }

  async function createNote(e: React.FormEvent) {
    e.preventDefault();
    const res = await apiFetch("/notes/", {
      method: "POST",
      body: JSON.stringify({
        title,
        content,
        tags: tags ? tags.split(",").map((t) => t.trim()) : null,
      }),
    });
    if (res.ok) {
      setTitle("");
      setContent("");
      setTags("");
      setShowCreate(false);
      loadNotes();
    }
  }

  async function deleteNote(id: string) {
    await apiFetch(`/notes/${id}`, { method: "DELETE" });
    loadNotes();
  }

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <AppHeader />
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Notes</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
        >
          {showCreate ? "Cancel" : "+ New Note"}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={createNote} className="bg-white rounded-xl shadow p-6 mb-6">
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <textarea
            placeholder="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
            rows={5}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <input
            type="text"
            placeholder="Tags (comma separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            type="submit"
            className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700"
          >
            Save Note
          </button>
        </form>
      )}

      <div className="space-y-4">
        {notes.map((note) => (
          <div key={note.id} className="bg-white rounded-xl shadow p-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {note.title}
                </h2>
                <p className="text-gray-600 mt-1 whitespace-pre-wrap">
                  {note.content}
                </p>
                {note.tags && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {note.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-primary-50 text-primary-700 px-2 py-1 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-2">
                  Updated {new Date(note.updated_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => deleteNote(note.id)}
                className="text-red-500 text-sm hover:underline"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
        {notes.length === 0 && (
          <p className="text-gray-500 text-center py-8">
            No notes yet. Create your first note!
          </p>
        )}
      </div>
    </main>
  );
}
