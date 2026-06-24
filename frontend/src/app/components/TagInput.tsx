"use client";

import { useState } from "react";

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
}

export default function TagInput({ tags, onChange }: TagInputProps) {
  const [draft, setDraft] = useState("");

  function commitDraft() {
    const value = draft.trim();
    if (value && !tags.includes(value)) {
      onChange([...tags, value]);
    }
    setDraft("");
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="border border-gray-300 rounded-lg px-3 py-2 mb-3 focus-within:ring-2 focus-within:ring-primary-500">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 text-xs bg-primary-50 text-primary-700 px-2 py-1 rounded"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-primary-500 hover:text-primary-800"
              aria-label={`Remove ${tag}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              commitDraft();
            } else if (e.key === "Backspace" && !draft && tags.length > 0) {
              removeTag(tags[tags.length - 1]);
            }
          }}
          onBlur={commitDraft}
          placeholder={tags.length === 0 ? "Add tags..." : ""}
          className="flex-1 min-w-[100px] text-sm outline-none py-0.5"
        />
      </div>
    </div>
  );
}
