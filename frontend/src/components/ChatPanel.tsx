import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import type { ChatMessage, Citation, TicketDraft } from "../types";
import { AnswerMessage } from "./AnswerMessage";

interface ChatPanelProps {
  messages: ChatMessage[];
  pending: boolean;
  onAsk: (question: string) => void;
  onOpenCitation: (citation: Citation) => void;
  onCreateTicket: (draft: TicketDraft) => void;
}

const MIN_QUESTION_LENGTH = 3;

export function ChatPanel({
  messages,
  pending,
  onAsk,
  onOpenCitation,
  onCreateTicket,
}: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const logEnd = useRef<HTMLDivElement>(null);
  const canSend = !pending && question.trim().length >= MIN_QUESTION_LENGTH;

  useEffect(() => {
    logEnd.current?.scrollIntoView?.({ block: "end" });
  }, [messages, pending]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!canSend) return;
    onAsk(question.trim());
    setQuestion("");
  };

  // Enter sends; Shift+Enter inserts a new line.
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) submit(event);
  };

  return (
    <section className="panel chat" aria-labelledby="chat-heading">
      <h2 id="chat-heading">Ask a question</h2>

      <div className="message-log" role="log" aria-live="polite" aria-busy={pending}>
        {messages.length === 0 && (
          <p className="hint">
            Ask about IT, HR, security, or expense policies, e.g. “How many PTO days carry over?”
          </p>
        )}
        {messages.map((message) => {
          if (message.role === "user") {
            return (
              <p key={message.id} className="message user">
                <span className="visually-hidden">You asked: </span>
                {message.text}
              </p>
            );
          }
          if (message.role === "error") {
            return (
              <p key={message.id} className="message error" role="alert">
                {message.text}
              </p>
            );
          }
          return (
            <AnswerMessage
              key={message.id}
              messageId={message.id}
              response={message.response}
              onOpenCitation={onOpenCitation}
              onCreateTicket={onCreateTicket}
            />
          );
        })}
        {pending && <p className="message status">Searching the documents…</p>}
        <div ref={logEnd} />
      </div>

      <form className="ask-form" onSubmit={submit}>
        <label htmlFor="question">Your question</label>
        <textarea
          id="question"
          value={question}
          rows={2}
          maxLength={1000}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-describedby="question-help"
        />
        <p id="question-help" className="hint">
          Press Enter to send, Shift+Enter for a new line.
        </p>
        <button type="submit" disabled={!canSend}>
          {pending ? "Sending…" : "Send"}
        </button>
      </form>
    </section>
  );
}
