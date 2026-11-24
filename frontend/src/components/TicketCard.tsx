import type { Ticket } from "../types";

const STATUS_LABELS: Record<Ticket["status"], string> = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <article className="ticket-card" aria-label={`Ticket ${ticket.id}`}>
      <h4>
        #{ticket.id} {ticket.title}
      </h4>
      <dl>
        <dt>Status</dt>
        <dd className={`status status-${ticket.status}`}>{STATUS_LABELS[ticket.status]}</dd>
        <dt>Priority</dt>
        <dd>{ticket.priority}</dd>
        <dt>Updated</dt>
        <dd>{new Date(ticket.updated_at).toLocaleString()}</dd>
      </dl>
      {ticket.notes.length > 0 && (
        <ul className="ticket-notes">
          {ticket.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </article>
  );
}
