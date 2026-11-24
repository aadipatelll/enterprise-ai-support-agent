import { useEffect, useRef, useState } from "react";

import { api, errorMessage } from "../api";
import type { Citation, SourceDocument } from "../types";

interface SourceViewerProps {
  citation: Citation;
  onClose: () => void;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "loaded"; document: SourceDocument }
  | { kind: "failed"; message: string };

export function SourceViewer({ citation, onClose }: SourceViewerProps) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const heading = useRef<HTMLHeadingElement>(null);

  // The parent remounts this component (key=source) for each citation.
  useEffect(() => {
    let active = true;
    heading.current?.focus();
    api
      .getDocument(citation.source)
      .then((document) => active && setState({ kind: "loaded", document }))
      .catch((error: unknown) => active && setState({ kind: "failed", message: errorMessage(error) }));
    return () => {
      active = false;
    };
  }, [citation.source]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <section className="panel source-viewer" aria-labelledby="source-heading">
      <div className="panel-header">
        <h2 id="source-heading" ref={heading} tabIndex={-1}>
          {citation.title}
        </h2>
        <button type="button" className="secondary" onClick={onClose}>
          Close source
        </button>
      </div>
      <p className="hint">
        Press Escape to close. Section: <strong>{citation.section}</strong> · {citation.source} · relevance{" "}
        {citation.score.toFixed(2)}
      </p>
      {state.kind === "loading" && <p>Loading document…</p>}
      {state.kind === "failed" && <p role="alert">{state.message}</p>}
      {state.kind === "loaded" && <pre className="document-text">{state.document.text}</pre>}
    </section>
  );
}
