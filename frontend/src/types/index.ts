export interface User {
  id: string;
  email: string;
  name: string;
  google_id: string;
}

export interface Email {
  id: string;
  gmail_message_id: string;
  sender: string;
  subject: string;
  snippet: string;
  received_at: string;
}

export interface CalendarEvent {
  id: string;
  google_event_id: string;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  attendees: string | null;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[] | null;
  due_date: string | null;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface BriefContent {
  executive_summary: string;
  priorities: string[];
  focus_areas: string[];
  attention_required: string[];
  time_critical: { task: string; date: string }[];
  coming_soon: { task: string; date: string }[];
  recommendations: { morning?: string; afternoon?: string; evening?: string };
}

export interface DailyBrief {
  id: string;
  brief_date: string;
  content: string;
  created_at: string;
}

export interface SearchResult {
  id: string;
  source_type: string;
  source_id: string;
  content: string;
  similarity: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  sources_used: number;
}

export interface ChatSession {
  session_id: string;
  last_message: string;
  last_at: string;
}

export interface Memory {
  id: string;
  content: string;
  brief_id: string | null;
  created_at: string;
}

export interface BriefTask {
  id: string;
  category: "priorities" | "focus_areas" | "attention_required" | "time_critical" | "coming_soon";
  task: string;
  date_label: string | null;
  completed: boolean;
  created_at: string;
}
