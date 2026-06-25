"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

interface NoteEditorProps {
  content: string;
  onChange: (html: string) => void;
}

export default function NoteEditor({ content, onChange }: NoteEditorProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content,
    immediatelyRender: false,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
    editorProps: {
      attributes: {
        class: "prose-sm max-w-none min-h-[120px] focus:outline-none px-4 py-2 text-sm text-ink",
      },
    },
  });

  if (!editor) return null;

  const toolbarBtn = (active: boolean) =>
    `px-2 py-1 text-xs rounded-md ${active ? "bg-primary-100 text-primary-700" : "text-ink-muted hover:bg-cream-200"}`;

  return (
    <div className="border border-ink/20 rounded-md overflow-hidden mb-3 focus-within:ring-2 focus-within:ring-primary-600">
      <div className="flex items-center gap-1 border-b border-ink/10 bg-cream-100 px-2 py-1">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={toolbarBtn(editor.isActive("bold"))}
        >
          <span className="font-bold">B</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={toolbarBtn(editor.isActive("italic"))}
        >
          <span className="italic">I</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={toolbarBtn(editor.isActive("heading", { level: 2 }))}
        >
          H2
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={toolbarBtn(editor.isActive("bulletList"))}
        >
          • List
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={toolbarBtn(editor.isActive("orderedList"))}
        >
          1. List
        </button>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
