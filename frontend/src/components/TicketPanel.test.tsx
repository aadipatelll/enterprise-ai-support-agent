import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../api";
import { draft, ticket } from "../test/fixtures";
import { TicketPanel } from "./TicketPanel";

describe("TicketPanel", () => {
  it("prefills the form from a chat draft and creates the ticket", async () => {
    const createSpy = vi.spyOn(api, "createTicket").mockResolvedValue(ticket);
    render(<TicketPanel request={{ id: 1, draft }} />);

    expect(screen.getByLabelText("Title")).toHaveValue("Who won the chili contest?");
    expect(screen.getByLabelText("Title")).toHaveFocus();

    await userEvent.selectOptions(screen.getByLabelText("Priority"), "high");
    await userEvent.click(screen.getByRole("button", { name: "Create ticket" }));

    expect(createSpy).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Who won the chili contest?", priority: "high" }),
    );
    expect(await screen.findByRole("article", { name: "Ticket 7" })).toHaveTextContent("Open");
    expect(screen.getByRole("status")).toHaveTextContent("Ticket #7 created.");
  });

  it("shows an error when ticket creation fails", async () => {
    vi.spyOn(api, "createTicket").mockRejectedValue(
      new ApiError("Ticket service is unavailable", 502),
    );
    render(<TicketPanel request={{ id: 1, draft }} />);

    await userEvent.click(screen.getByRole("button", { name: "Create ticket" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ticket service is unavailable");
  });

  it("looks up a ticket's status by number", async () => {
    const getSpy = vi
      .spyOn(api, "getTicket")
      .mockResolvedValue({ ...ticket, status: "in_progress" });
    render(<TicketPanel request={null} />);

    await userEvent.type(screen.getByLabelText("Ticket number"), "7{Enter}");

    expect(getSpy).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("article", { name: "Ticket 7" })).toHaveTextContent(
      "In progress",
    );
  });

  it("reports an unknown ticket number", async () => {
    vi.spyOn(api, "getTicket").mockRejectedValue(
      new ApiError("NOT_FOUND: Ticket 99 does not exist", 404),
    );
    render(<TicketPanel request={null} />);

    await userEvent.type(screen.getByLabelText("Ticket number"), "99{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent("Ticket 99 does not exist");
  });
});
