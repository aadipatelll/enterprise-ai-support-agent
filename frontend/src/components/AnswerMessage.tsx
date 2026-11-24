import { Fragment } from "react";

import type { AskResponse, Citation, TicketDraft } from "../types";

interface AnswerMessageProps {
  messageId: string;
  response: AskResponse;
  onOpenCitation: (citation: Citation) => void;
  onCreateTicket: (draft: TicketDraft) => void;
}

const citationAnchor = (messageId: string, id: number) => `${messageId}-cite-${id}`;

/** Turns "[1]" markers in the answer into links to the matching citation. */
function AnswerText({ messageId, text, citations }: {
  messageId: string;
  text: string;
  citations: Citation[];
}) {
  const citedIds = new Set(citations.map((citation) => citation.id));
  const parts = text.split(/(\[\d+\])/);
  return (
    <p className="answer-text">
      {parts.map((part, index) => {
        const id = Number(part.match(/^\[(\d+)\]$/)?.[1]);
        if (!citedIds.has(id)) return <Fragment key={index}>{part}</Fragment>;
        return (
          <a
            key={index}
            className="citation-marker"
            href={`#${citationAnchor(messageId, id)}`}
            aria-label={`Source ${id}`}
          >
            [{id}]
          </a>
        );
      })}
    </p>
  );
}

export function AnswerMessage({
  messageId,
  response,
  onOpenCitation,
  onCreateTicket,
}: AnswerMessageProps) {
  const { suggested_ticket: draft } = response;
  return (
    <div className="message assistant">
      <AnswerText messageId={messageId} text={response.answer} citations={response.citations} />

      {response.citations.length > 0 && (
        <section aria-label="Sources">
          <h3 className="sources-heading">Sources</h3>
          <ol className="citation-list">
            {response.citations.map((citation) => (
              <li key={citation.id} id={citationAnchor(messageId, citation.id)}>
                <button
                  type="button"
                  className="link-button"
                  onClick={() => onOpenCitation(citation)}
                >
                  [{citation.id}] {citation.title} — {citation.section}
                </button>
              </li>
            ))}
          </ol>
        </section>
      )}

      {!response.answered && draft && (
        <button type="button" className="secondary" onClick={() => onCreateTicket(draft)}>
          Create a support ticket
        </button>
      )}
    </div>
  );
}
