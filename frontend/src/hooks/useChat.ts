import { useCallback, useRef, useState } from "react";

import { api, errorMessage } from "../api";
import type { ChatMessage } from "../types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const nextId = useRef(0);

  const newId = () => `m${nextId.current++}`;

  const ask = useCallback(async (question: string) => {
    setMessages((current) => [...current, { id: newId(), role: "user", text: question }]);
    setPending(true);
    try {
      const response = await api.ask(question);
      setMessages((current) => [...current, { id: newId(), role: "assistant", response }]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { id: newId(), role: "error", text: errorMessage(error) },
      ]);
    } finally {
      setPending(false);
    }
  }, []);

  return { messages, pending, ask };
}
