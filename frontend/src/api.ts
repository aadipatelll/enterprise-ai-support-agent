import type { AskResponse, SourceDocument, Ticket, TicketCreate } from "./types";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** FastAPI returns `detail` as a string, or as a list of validation errors. */
function detailMessage(body: unknown): string | undefined {
  if (typeof body !== "object" || body === null || !("detail" in body)) return undefined;
  const { detail } = body as { detail: unknown };
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  return undefined;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new ApiError("Can't reach the support API. Is the backend running?", 0);
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(
      detailMessage(body) ?? `Request failed (${response.status})`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export const api = {
  ask: (question: string) =>
    request<AskResponse>("/ask", { method: "POST", body: JSON.stringify({ question }) }),
  getDocument: (source: string) =>
    request<SourceDocument>(`/documents/${encodeURIComponent(source)}`),
  createTicket: (data: TicketCreate) =>
    request<Ticket>("/tickets", { method: "POST", body: JSON.stringify(data) }),
  getTicket: (id: number) => request<Ticket>(`/tickets/${id}`),
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
