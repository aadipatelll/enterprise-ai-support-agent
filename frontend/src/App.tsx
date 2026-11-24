import { useCallback, useState } from "react";

import { ChatPanel } from "./components/ChatPanel";
import { SourceViewer } from "./components/SourceViewer";
import { TicketPanel, type TicketRequest } from "./components/TicketPanel";
import { useChat } from "./hooks/useChat";
import type { Citation, TicketDraft } from "./types";

export function App() {
  const { messages, pending, ask } = useChat();
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);
  const closeSource = useCallback(() => setOpenCitation(null), []);
  const [ticketRequest, setTicketRequest] = useState<TicketRequest | null>(null);

  const requestTicket = (draft: TicketDraft) =>
    setTicketRequest((current) => ({ id: (current?.id ?? 0) + 1, draft }));

  return (
    <>
      <a className="skip-link" href="#question">
        Skip to question box
      </a>
      <header className="app-header">
        <h1>Corvane Labs Support Assistant</h1>
        <p>Answers from company policies, with sources. Can't find it? Open a ticket.</p>
      </header>
      <main className="layout">
        <ChatPanel
          messages={messages}
          pending={pending}
          onAsk={ask}
          onOpenCitation={setOpenCitation}
          onCreateTicket={requestTicket}
        />
        <aside className="sidebar" aria-label="Sources and tickets">
          {openCitation && (
            <SourceViewer
              key={`${openCitation.source}#${openCitation.section}`}
              citation={openCitation}
              onClose={closeSource}
            />
          )}
          <TicketPanel request={ticketRequest} />
        </aside>
      </main>
    </>
  );
}
