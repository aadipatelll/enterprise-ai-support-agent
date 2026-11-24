import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { ApiError, api } from "./api";
import { answered, unanswered } from "./test/fixtures";

async function askQuestion(text: string) {
  await userEvent.type(screen.getByLabelText("Your question"), `${text}{Enter}`);
}

describe("App", () => {
  it("sends a question with Enter and shows the cited answer", async () => {
    const askSpy = vi.spyOn(api, "ask").mockResolvedValue(answered);
    render(<App />);

    await askQuestion("How many PTO days carry over?");

    expect(askSpy).toHaveBeenCalledWith("How many PTO days carry over?");
    const log = screen.getByRole("log");
    expect(within(log).getByText("How many PTO days carry over?")).toBeInTheDocument();
    expect(await within(log).findByRole("link", { name: "Source 1" })).toBeInTheDocument();
    expect(within(log).getByText(/up to 5 unused pto days/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toHaveValue("");
  });

  it("opens the cited document in the source viewer and closes it with Escape", async () => {
    vi.spyOn(api, "ask").mockResolvedValue(answered);
    vi.spyOn(api, "getDocument").mockResolvedValue({
      source: "hr-pto-policy.md",
      title: "Paid Time Off Policy",
      text: "## Carryover\n\nUp to 5 unused PTO days carry over.",
    });
    render(<App />);
    await askQuestion("How many PTO days carry over?");

    await userEvent.click(await screen.findByRole("button", { name: /carryover/i }));

    const viewer = screen.getByRole("region", { name: "Paid Time Off Policy" });
    expect(await within(viewer).findByText(/up to 5 unused pto days/i)).toBeInTheDocument();
    expect(within(viewer).getByRole("heading", { name: "Paid Time Off Policy" })).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("region", { name: "Paid Time Off Policy" })).toBeNull();
  });

  it("moves an unanswered question into the ticket form", async () => {
    vi.spyOn(api, "ask").mockResolvedValue(unanswered);
    render(<App />);
    await askQuestion("Who won the chili contest?");

    await userEvent.click(await screen.findByRole("button", { name: "Create a support ticket" }));

    expect(screen.getByLabelText("Title")).toHaveValue("Who won the chili contest?");
    expect(screen.getByLabelText("Title")).toHaveFocus();
  });

  it("shows API failures as an alert in the chat", async () => {
    vi.spyOn(api, "ask").mockRejectedValue(new ApiError("Language model is unavailable", 503));
    render(<App />);

    await askQuestion("How many PTO days carry over?");

    expect(await screen.findByRole("alert")).toHaveTextContent("Language model is unavailable");
  });

  it("disables Send until the question is long enough", async () => {
    render(<App />);
    const send = screen.getByRole("button", { name: "Send" });

    expect(send).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Your question"), "VPN?");
    expect(send).toBeEnabled();
  });
});
