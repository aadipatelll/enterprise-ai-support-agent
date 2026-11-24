// Mirrors backend/app/schemas.py

export type Priority = "low" | "medium" | "high";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

export interface Citation {
  id: number;
  title: string;
  section: string;
  source: string;
  score: number;
}

export interface TicketDraft {
  title: string;
  description: string;
}

export interface AskResponse {
  answer: string;
  answered: boolean;
  citations: Citation[];
  suggested_ticket: TicketDraft | null;
}

export interface SourceDocument {
  source: string;
  title: string;
  text: string;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  priority: Priority;
  status: TicketStatus;
  requester: string | null;
  notes: string[];
  created_at: string;
  updated_at: string;
}

export interface TicketCreate {
  title: string;
  description: string;
  priority: Priority;
  requester?: string;
}

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; response: AskResponse }
  | { id: string; role: "error"; text: string };
