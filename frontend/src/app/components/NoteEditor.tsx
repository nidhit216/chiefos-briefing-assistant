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
        class: "prose-sm max-w-none min-h-[120px] focus:outline-none px-4 py-2 text-sm text-gray-800",
      },
    },
  });

  if (!editor) return null;

  const toolbarBtn = (active: boolean) =>
    `px-2 py-1 text-xs rounded-md ${active ? "bg-primary-100 text-primary-700" : "text-gray-500 hover:bg-gray-100"}`;

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden mb-3 focus-within:ring-2 focus-within:ring-primary-500">
      <div className="flex items-center gap-1 border-b border-gray-200 bg-gray-50 px-2 py-1">
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
