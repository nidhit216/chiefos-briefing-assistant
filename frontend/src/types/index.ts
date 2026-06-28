export interface User {
  id: string;
  email: string;
  name: string;
  google_id: string;
  google_connected: boolean;
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
  attention_required: string[];
  recommendations: { morning?: string; afternoon?: string; evening?: string };
  focus_breakdown: { label: string; percent: number }[];
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

export interface DraftPayload {
  to: string;
  subject: string;
  body: string;
}

export interface ChatResponse {
  reply: string | null;
  session_id: string;
  sources_used: number;
  sources?: SearchResult[] | null;
  draft?: DraftPayload | null;
}

export interface BriefTask {
  id: string;
  category: "attention_required";
  task: string;
  date_label: string | null;
  completed: boolean;
  created_at: string;
}
