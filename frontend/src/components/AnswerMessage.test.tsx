import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { answered, unanswered } from "../test/fixtures";
import { AnswerMessage } from "./AnswerMessage";

function renderAnswer(response = answered) {
  const handlers = { onOpenCitation: vi.fn(), onCreateTicket: vi.fn() };
  render(<AnswerMessage messageId="m1" response={response} {...handlers} />);
  return handlers;
}

describe("AnswerMessage", () => {
  it("links inline citation markers to the source list", () => {
    renderAnswer();

    expect(screen.getByRole("link", { name: "Source 1" })).toHaveAttribute("href", "#m1-cite-1");
    expect(document.getElementById("m1-cite-1")).toHaveTextContent("Paid Time Off Policy");
  });

  it("opens a citation when its button is clicked", async () => {
    const { onOpenCitation } = renderAnswer();

    await userEvent.click(
      screen.getByRole("button", { name: /paid time off policy — carryover/i }),
    );

    expect(onOpenCitation).toHaveBeenCalledWith(answered.citations[0]);
  });

  it("offers a ticket when the documents have no answer", async () => {
    const { onCreateTicket } = renderAnswer(unanswered);

    expect(screen.queryByRole("region", { name: "Sources" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Create a support ticket" }));

    expect(onCreateTicket).toHaveBeenCalledWith(unanswered.suggested_ticket);
  });

  it("does not offer a ticket for answered questions", () => {
    renderAnswer();

    expect(screen.queryByRole("button", { name: /create a support ticket/i })).toBeNull();
  });
});
