import type { AskResponse, Ticket, TicketDraft } from "../types";

export const answered: AskResponse = {
  answer: "Up to 5 unused PTO days carry over [1].",
  answered: true,
  citations: [
    {
      id: 1,
      title: "Paid Time Off Policy",
      section: "Carryover",
      source: "hr-pto-policy.md",
      score: 0.82,
    },
  ],
  suggested_ticket: null,
};

export const draft: TicketDraft = {
  title: "Who won the chili contest?",
  description: "The knowledge base could not answer this employee question.",
};

export const unanswered: AskResponse = {
  answer: "I couldn't find this in the company documents, so I won't guess.",
  answered: false,
  citations: [],
  suggested_ticket: draft,
};

export const ticket: Ticket = {
  id: 7,
  title: "Who won the chili contest?",
  description: "The knowledge base could not answer this employee question.",
  priority: "medium",
  status: "open",
  requester: null,
  notes: [],
  created_at: "2026-11-24T10:00:00Z",
  updated_at: "2026-11-24T10:00:00Z",
};
