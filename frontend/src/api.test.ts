import { describe, expect, it, vi } from "vitest";

import { API_URL, ApiError, api } from "./api";
import { answered } from "./test/fixtures";

function mockFetch(status: number, body: unknown) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

describe("api", () => {
  it("posts the question to /ask and returns the answer", async () => {
    const fetchSpy = mockFetch(200, answered);

    await expect(api.ask("How many PTO days carry over?")).resolves.toEqual(answered);
    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_URL}/ask`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question: "How many PTO days carry over?" }),
      }),
    );
  });

  it("uses the backend's error detail", async () => {
    mockFetch(503, { detail: "Language model is unavailable" });

    await expect(api.ask("Anything?")).rejects.toMatchObject({
      message: "Language model is unavailable",
      status: 503,
    });
  });

  it("reads the first validation error message", async () => {
    mockFetch(422, { detail: [{ msg: "String should have at least 3 characters" }] });

    await expect(api.ask("hi")).rejects.toThrow("String should have at least 3 characters");
  });

  it("reports an unreachable backend clearly", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    const error = await api.getTicket(1).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toMatch(/can't reach the support api/i);
  });

  it("encodes document names in the URL", async () => {
    const fetchSpy = mockFetch(200, { source: "a b.md", title: "A", text: "" });

    await api.getDocument("a b.md");

    expect(fetchSpy.mock.calls[0][0]).toBe(`${API_URL}/documents/a%20b.md`);
  });
});
