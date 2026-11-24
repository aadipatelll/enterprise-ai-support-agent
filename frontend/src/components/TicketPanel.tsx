import { useEffect, useRef, useState, type FormEvent } from "react";

import { api, errorMessage } from "../api";
import type { Priority, Ticket, TicketDraft } from "../types";
import { TicketCard } from "./TicketCard";

export interface TicketRequest {
  id: number;
  draft: TicketDraft;
}

interface TicketPanelProps {
  request: TicketRequest | null;
}

const EMPTY_DRAFT: TicketDraft = { title: "", description: "" };

function CreateTicketForm({ draft, onCreated }: {
  draft: TicketDraft | null;
  onCreated: (ticket: Ticket) => void;
}) {
  const [form, setForm] = useState(draft ?? EMPTY_DRAFT);
  const [priority, setPriority] = useState<Priority>("medium");
  const [requester, setRequester] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleInput = useRef<HTMLInputElement>(null);

  // The panel remounts this form for each new chat draft; move focus to it.
  useEffect(() => {
    if (draft) titleInput.current?.focus();
  }, [draft]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const ticket = await api.createTicket({
        ...form,
        priority,
        requester: requester.trim() || undefined,
      });
      onCreated(ticket);
      setForm(EMPTY_DRAFT);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} aria-labelledby="create-ticket-heading">
      <h3 id="create-ticket-heading">Create a ticket</h3>
      <label htmlFor="ticket-title">Title</label>
      <input
        id="ticket-title"
        ref={titleInput}
        required
        minLength={3}
        maxLength={200}
        value={form.title}
        onChange={(event) => setForm({ ...form, title: event.target.value })}
      />
      <label htmlFor="ticket-description">Description</label>
      <textarea
        id="ticket-description"
        required
        rows={4}
        maxLength={5000}
        value={form.description}
        onChange={(event) => setForm({ ...form, description: event.target.value })}
      />
      <label htmlFor="ticket-priority">Priority</label>
      <select
        id="ticket-priority"
        value={priority}
        onChange={(event) => setPriority(event.target.value as Priority)}
      >
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
      <label htmlFor="ticket-requester">Your email (optional)</label>
      <input
        id="ticket-requester"
        type="email"
        value={requester}
        onChange={(event) => setRequester(event.target.value)}
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Creating…" : "Create ticket"}
      </button>
    </form>
  );
}

function TicketLookupForm({ onFound }: { onFound: (ticket: Ticket) => void }) {
  const [ticketId, setTicketId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      onFound(await api.getTicket(Number(ticketId)));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <form onSubmit={submit} aria-labelledby="lookup-heading">
      <h3 id="lookup-heading">Check ticket status</h3>
      <label htmlFor="ticket-id">Ticket number</label>
      <input
        id="ticket-id"
        type="number"
        min={1}
        required
        value={ticketId}
        onChange={(event) => setTicketId(event.target.value)}
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">Check status</button>
    </form>
  );
}

export function TicketPanel({ request }: TicketPanelProps) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [announcement, setAnnouncement] = useState("");

  const showTicket = (ticket: Ticket, verb: string) => {
    setTickets((current) => [ticket, ...current.filter((t) => t.id !== ticket.id)]);
    setAnnouncement(`Ticket #${ticket.id} ${verb}.`);
  };

  return (
    <section className="panel tickets" aria-labelledby="tickets-heading">
      <h2 id="tickets-heading">Support tickets</h2>
      <CreateTicketForm
        key={request?.id ?? "blank"}
        draft={request?.draft ?? null}
        onCreated={(ticket) => showTicket(ticket, "created")}
      />
      <TicketLookupForm onFound={(ticket) => showTicket(ticket, "loaded")} />
      <p className="visually-hidden" role="status">
        {announcement}
      </p>
      {tickets.length > 0 && (
        <div className="ticket-list">
          <h3>Your tickets</h3>
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}
    </section>
  );
}
