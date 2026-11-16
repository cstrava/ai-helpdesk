import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Chat from "./Chat";
import { clearUnsaved, readUnsaved, saveUnsaved } from "./unsaved";
import { request } from "./api";

const draft = {
  conversation_id: "conversation-1",
  last_message_id: 2,
  title: "Account blocked",
  description: "Cannot sign in",
  predicted_category: "Access",
  model_version: "test",
};
const ticket = {
  id: "ticket-1",
  conversation_id: "conversation-1",
  title: draft.title,
  text: draft.description,
  predicted_category: "Access",
  final_category: "Access",
  model_version: "test",
  status: "open",
  created_at: "2026-11-13T12:00:00Z",
};
const messages = [
  { id: 1, role: "user", content: "Cannot sign in" },
  { id: 2, role: "assistant", content: "What error?" },
];
function backend(failure = "none") {
  let created = false;
  let attempts = 0;
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input);
      const json = (data: unknown, status = 200) =>
        new Response(JSON.stringify(data), { status });
      if (path.includes("/conversations?")) return json([]);
      if (path === "/api/conversations/conversation-1")
        return json({ ticket: created ? ticket : null });
      if (path.endsWith("/messages") && options?.method === "GET")
        return json(messages);
      if (path.endsWith("/messages"))
        return json({
          user_message: messages[0],
          assistant_message: messages[1],
        });
      if (path === "/api/conversations") return json({ id: "conversation-1" });
      if (path.endsWith("/ticket-draft")) return json(draft);
      if (path.endsWith("/tickets")) {
        attempts++;
        if (failure === "before-save" && attempts === 1)
          throw new TypeError("offline");
        if (created) return json({ detail: "Already created" }, 409);
        created = true;
        if (failure === "network") throw new TypeError("response lost");
        if (failure === "proxy")
          return new Response("Bad Gateway", { status: 502 });
        if (failure === "invalid-json")
          return new Response("<html>proxy</html>");
        if (failure === "invalid-ticket") return json({});
        return json(ticket);
      }
      throw new Error(`Unexpected path: ${path}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
function chat(accountId = "account-1") {
  return render(
    <Chat accountId={accountId} onCreated={vi.fn()} onViewTickets={vi.fn()} />,
  );
}
async function prepare() {
  const user = userEvent.setup();
  await user.type(
    await screen.findByLabelText("Mesajul tău"),
    "Cannot sign in",
  );
  await user.click(screen.getByRole("button", { name: "Trimite" }));
  await screen.findByText("What error?");
  await user.click(screen.getByRole("button", { name: "Pregătește tichetul" }));
  await screen.findByLabelText("Titlu");
  return user;
}
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it.each(["network", "proxy", "invalid-json", "invalid-ticket"])(
  "recovers a saved ticket after %s without a second POST",
  async (failure) => {
    const fetchMock = backend(failure);
    chat();
    const user = await prepare();
    await user.click(
      screen.getByRole("button", { name: "Confirmă și creează" }),
    );
    await screen.findByText("TICHET CREAT");
    expect(
      fetchMock.mock.calls.filter(([path]) =>
        String(path).endsWith("/tickets"),
      ),
    ).toHaveLength(1);
    expect(readUnsaved("account-1", "conversation-1").draft).toBeNull();
  },
);

it("requires server verification before retrying an uncertain confirmation", async () => {
  const fetchMock = backend("before-save");
  chat();
  const user = await prepare();
  await user.click(screen.getByRole("button", { name: "Confirmă și creează" }));
  const check = await screen.findByRole("button", {
    name: "Verifică rezultatul",
  });
  expect(
    (
      screen.getByRole("button", {
        name: "Confirmă și creează",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(screen.queryByText("TICHET CREAT")).toBeNull();
  await user.click(check);
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: "Confirmă și creează",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
  await user.click(screen.getByRole("button", { name: "Confirmă și creează" }));
  await screen.findByText("TICHET CREAT");
  expect(
    fetchMock.mock.calls.filter(([path]) => String(path).endsWith("/tickets")),
  ).toHaveLength(2);
});

it("discards a stale draft when verification observes a newer message", async () => {
  const fetchMock = backend("before-save");
  chat();
  const user = await prepare();
  await user.click(screen.getByRole("button", { name: "Confirmă și creează" }));
  const check = await screen.findByRole("button", {
    name: "Verifică rezultatul",
  });
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (input, options) => {
    if (String(input).endsWith("/messages") && options?.method === "GET")
      return new Response(
        JSON.stringify([
          ...messages,
          { id: 3, role: "user", content: "Correction" },
        ]),
      );
    return original(input, options);
  });
  await user.click(check);
  await screen.findByText(
    "Conversația s-a schimbat. Generează din nou ciorna.",
  );
  expect(screen.queryByLabelText("Titlu")).toBeNull();
  expect(screen.queryByText("TICHET CREAT")).toBeNull();
  expect(
    fetchMock.mock.calls.filter(([path]) => String(path).endsWith("/tickets")),
  ).toHaveLength(1);
});

it("restores an edited draft after refresh and removes it after confirmation", async () => {
  backend();
  const view = chat();
  const user = await prepare();
  await user.clear(screen.getByLabelText("Titlu"));
  await user.type(screen.getByLabelText("Titlu"), "Edited title");
  await user.clear(screen.getByLabelText("Descriere"));
  await user.type(screen.getByLabelText("Descriere"), "Edited description");
  view.unmount();
  chat();
  expect(
    ((await screen.findByLabelText("Titlu")) as HTMLInputElement).value,
  ).toBe("Edited title");
  expect(
    (screen.getByLabelText("Descriere") as HTMLTextAreaElement).value,
  ).toBe("Edited description");
  await user.click(screen.getByRole("button", { name: "Confirmă și creează" }));
  await screen.findByText("TICHET CREAT");
  expect(readUnsaved("account-1", "conversation-1")).toEqual({
    text: "",
    draft: null,
    uncertain: false,
  });
});

it("restores unsent text before a conversation exists, then clears it after send", async () => {
  backend();
  const view = chat();
  const user = userEvent.setup();
  await user.type(
    await screen.findByLabelText("Mesajul tău"),
    "Unsent problem",
  );
  view.unmount();
  chat();
  await waitFor(() =>
    expect(
      (screen.getByLabelText("Mesajul tău") as HTMLTextAreaElement).value,
    ).toBe("Unsent problem"),
  );
  await user.click(screen.getByRole("button", { name: "Trimite" }));
  await screen.findByText("What error?");
  expect(readUnsaved("account-1", null).text).toBe("");
  expect(readUnsaved("account-1", "conversation-1").text).toBe("");
});

it("does not restore a stale draft or another account's content", async () => {
  backend();
  localStorage.setItem("helpdesk-conversation-account-1", "conversation-1");
  saveUnsaved("account-1", "conversation-1", {
    text: "Private text",
    draft: { ...draft, last_message_id: 1 },
    uncertain: false,
  });
  const view = chat();
  await screen.findByText(/Conversația s-a schimbat/);
  expect(screen.queryByLabelText("Titlu")).toBeNull();
  expect(
    (screen.getByLabelText("Mesajul tău") as HTMLTextAreaElement).value,
  ).toBe("Private text");
  view.unmount();
  chat("account-2");
  await waitFor(() =>
    expect(
      (screen.getByLabelText("Mesajul tău") as HTMLTextAreaElement).value,
    ).toBe(""),
  );
});

it("never restores a draft over an already converted conversation", async () => {
  backend("network");
  const view = chat();
  const user = await prepare();
  await user.click(screen.getByRole("button", { name: "Confirmă și creează" }));
  await screen.findByText("TICHET CREAT");
  view.unmount();
  saveUnsaved("account-1", "conversation-1", {
    text: "old",
    draft,
    uncertain: true,
  });
  chat();
  await screen.findByText("TICHET CREAT");
  expect(screen.queryByLabelText("Titlu")).toBeNull();
  expect(readUnsaved("account-1", "conversation-1").draft).toBeNull();
});

it("keeps conversations separate and clears only application editor storage", () => {
  saveUnsaved("a", "one", { text: "one", draft: null, uncertain: false });
  saveUnsaved("a", "two", { text: "two", draft: null, uncertain: false });
  sessionStorage.setItem("unrelated", "keep");
  expect(readUnsaved("a", "one").text).toBe("one");
  expect(readUnsaved("a", "two").text).toBe("two");
  clearUnsaved();
  expect(readUnsaved("a", "one").text).toBe("");
  expect(sessionStorage.getItem("unrelated")).toBe("keep");
});

it("aborts a request that exceeds the client timeout", async () => {
  vi.useFakeTimers();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_path, options) =>
        new Promise((_resolve, reject) => {
          options.signal.addEventListener("abort", () =>
            reject(new DOMException("timeout", "AbortError")),
          );
        }),
    ),
  );
  const result = request("/conversations/c/tickets", "POST", {}).catch(
    (error) => error,
  );
  await vi.advanceTimersByTimeAsync(150_000);
  expect(((await result) as { status: number }).status).toBe(0);
});
