import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import TicketThread from "./TicketThread";
import type { Ticket } from "./api";
const ticket: Ticket = {
  id: "t1",
  title: "Access",
  text: "Account blocked",
  status: "open",
  predicted_category: "Access",
  final_category: "Access",
  model_version: "test",
  conversation_id: "c1",
  created_at: "2026-11-13T12:00:00Z",
  assignee_id: null,
  assignee_email: null,
  priority: "normal",
  version: 0,
  updated_at: null,
  first_resolved_at: null,
};
function setup(
  support = false,
  failOnce = false,
  status: Ticket["status"] = "open",
) {
  let attempts = 0;
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input);
      const json = (value: unknown) => new Response(JSON.stringify(value));
      if (path === "/api/support/agents")
        return json([{ id: "agent", email: "agent@example.test" }]);
      if (path.includes("/messages?")) return json([]);
      if (path.endsWith("/claim"))
        return json({
          ...ticket,
          version: 1,
          assignee_id: "agent",
          assignee_email: "agent@example.test",
        });
      if (path.endsWith("/reopen"))
        return json({ ...ticket, status: "open", version: 1 });
      if (path.endsWith("/messages")) {
        attempts++;
        if (failOnce && attempts === 1) throw new TypeError("response lost");
        const body = JSON.parse(String(options?.body));
        return json({
          id: "m1",
          content: body.content,
          visibility: body.visibility,
          kind: "reply",
          author: "agent@example.test",
          author_role: support ? "support" : "user",
          created_at: "2026-11-13T12:01:00Z",
        });
      }
      throw new Error(`Unexpected path ${path}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  function Wrapper() {
    const [current, setCurrent] = useState({ ...ticket, status });
    return (
      <TicketThread ticket={current} support={support} onChanged={setCurrent} />
    );
  }
  render(<Wrapper />);
  return fetchMock;
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("retries a public reply with the same idempotency key and preserves text on failure", async () => {
  const fetchMock = setup(false, true);
  const user = userEvent.setup();
  await screen.findByText("Nu există mesaje pe tichet.");
  await user.type(screen.getByLabelText("Răspuns public"), "Still blocked");
  await user.click(screen.getByRole("button", { name: "Trimite răspunsul" }));
  await screen.findByRole("alert");
  expect(
    (screen.getByLabelText("Răspuns public") as HTMLTextAreaElement).value,
  ).toBe("Still blocked");
  await user.click(screen.getByRole("button", { name: "Trimite răspunsul" }));
  await screen.findByText("Răspunsul a fost salvat.");
  const posts = fetchMock.mock.calls.filter(
    ([, options]) => options?.method === "POST",
  );
  expect(posts).toHaveLength(2);
  expect(JSON.parse(String(posts[0][1]?.body)).request_id).toBe(
    JSON.parse(String(posts[1][1]?.body)).request_id,
  );
  expect(screen.getAllByText("Still blocked")).toHaveLength(1);
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.queryByLabelText("Agent responsabil")).toBeNull();
});

it("lets support claim with a version check and visually distinguishes internal notes", async () => {
  const fetchMock = setup(true);
  const user = userEvent.setup();
  await screen.findByText("Nu există mesaje pe tichet.");
  await user.click(screen.getByRole("button", { name: "Preia tichetul" }));
  await screen.findByText("Atribuirea a fost salvată.");
  const claim = fetchMock.mock.calls.find(([path]) =>
    String(path).endsWith("/claim"),
  );
  expect(JSON.parse(String(claim?.[1]?.body))).toEqual({ expected_version: 0 });
  await user.click(screen.getByRole("checkbox"));
  await user.type(screen.getByLabelText("Notă internă"), "Internal diagnosis");
  await user.click(screen.getByRole("button", { name: "Adaugă nota" }));
  await screen.findByText("Nota internă a fost salvată.");
  expect(screen.getByText("Internal diagnosis").closest("li")?.className).toBe(
    "internal-note",
  );
  const post = fetchMock.mock.calls.find(([path]) =>
    String(path).endsWith("/messages"),
  );
  expect(JSON.parse(String(post?.[1]?.body)).visibility).toBe("internal");
});

it("requires a reopening reason and returns the ticket to open", async () => {
  const fetchMock = setup(false, false, "resolved");
  const user = userEvent.setup();
  await screen.findByText("Nu există mesaje pe tichet.");
  expect(
    (
      screen.getByRole("button", {
        name: "Redeschide tichetul",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  await user.type(
    screen.getByLabelText("Motivul redeschiderii"),
    "Problem returned",
  );
  await user.click(screen.getByRole("button", { name: "Redeschide tichetul" }));
  await screen.findByText("Tichetul a fost redeschis.");
  await waitFor(() =>
    expect(screen.queryByLabelText("Motivul redeschiderii")).toBeNull(),
  );
  const post = fetchMock.mock.calls.find(([path]) =>
    String(path).endsWith("/reopen"),
  );
  expect(JSON.parse(String(post?.[1]?.body))).toEqual({
    reason: "Problem returned",
    expected_version: 0,
    request_id: expect.any(String),
  });
});
