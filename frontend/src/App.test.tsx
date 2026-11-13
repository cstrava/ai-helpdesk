import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
const ticket = {
  id: "ticket-1",
  title: "Acces pontaj",
  text: "Nu funcționează autentificarea.",
  predicted_category: "Hardware",
  final_category: "Access",
  model_version: "xlm_roberta_helpdesk_v2",
  status: "open",
  created_at: "2026-11-05T10:00:00Z",
  conversation_id: "conversation-1",
  version: 0,
};
const draft = {
  conversation_id: "conversation-1",
  last_message_id: 2,
  title: "Acces pontaj",
  description: "Nu funcționează autentificarea.",
  predicted_category: "Access",
  model_version: "xlm_roberta_helpdesk_v2",
};
function mockApi(failMessage = false) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      let data: unknown;
      if (path === "/api/support/agents" || path.includes("/messages?"))
        data = [];
      else if (path === "/api/auth/me")
        data = {
          id: "account-1",
          email: "support@example.test",
          role: "support",
          csrf_token: "csrf-test",
        };
      else if (path === "/api/auth/logout") data = {};
      else if (path.startsWith("/api/conversations?")) data = [];
      else if (path.endsWith("/events")) data = [];
      else if (path === "/api/conversations") data = { id: "conversation-1" };
      else if (path.endsWith("/messages")) {
        if (failMessage)
          return new Response(
            JSON.stringify({ detail: "Ollama indisponibil" }),
            { status: 502 },
          );
        data = {
          user_message: { id: 1, role: "user", content: "Nu merge pontajul" },
          assistant_message: {
            id: 2,
            role: "assistant",
            content: "Ce eroare apare?",
          },
        };
      } else if (path.endsWith("/ticket-draft")) data = draft;
      else if (path === "/api/conversations/conversation-1/tickets")
        data = { ...ticket, title: JSON.parse(String(init?.body)).title };
      else if (path === "/api/tickets/ticket-1")
        data = { ...ticket, ...JSON.parse(String(init?.body)) };
      else if (path.startsWith("/api/tickets?")) data = [ticket];
      else throw new Error(`Rută neașteptată: ${path}`);
      return new Response(JSON.stringify(data), { status: 200 });
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});
describe("Helpdesk frontend", () => {
  it("creates a ticket only after reviewing and confirming the edited draft", async () => {
    const fetchMock = mockApi(),
      user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.type(screen.getByLabelText("Mesajul tău"), "Nu merge pontajul");
    await user.click(screen.getByRole("button", { name: "Trimite" }));
    await screen.findByText("Ce eroare apare?");
    await user.click(
      screen.getByRole("button", { name: /Pregătește tichetul/ }),
    );
    const title = await screen.findByLabelText("Titlu");
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).endsWith("/conversation-1/tickets"),
      ),
    ).toBe(false);
    await user.clear(title);
    await user.type(title, "Pontaj — cont blocat");
    await user.click(
      screen.getByRole("button", { name: /Confirmă și creează/ }),
    );
    await screen.findByText("TICHET CREAT");
    const call = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/conversation-1/tickets"),
    )!;
    expect(JSON.parse(String(call[1]?.body))).toEqual({
      title: "Pontaj — cont blocat",
      description: draft.description,
      last_message_id: 2,
      confirmed: true,
    });
    expect(screen.queryByLabelText("Mesajul tău")).toBeNull();
    expect(sessionStorage.getItem("helpdesk-unsaved:account-1:new")).toBeNull();
  });
  it("preserves unsent text when the model fails", async () => {
    mockApi(true);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.type(screen.getByLabelText("Mesajul tău"), "Nu merge pontajul");
    await user.click(screen.getByRole("button", { name: "Trimite" }));
    await screen.findByRole("alert");
    expect(
      (screen.getByLabelText("Mesajul tău") as HTMLTextAreaElement).value,
    ).toBe("Nu merge pontajul");
    expect(
      screen.queryByRole("button", { name: /Pregătește tichetul/ }),
    ).toBeNull();
  });
  it("updates final category and resolves with an explicit message", async () => {
    const fetchMock = mockApi(),
      user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.click(screen.getByRole("button", { name: "Tichete" }));
    await user.click(
      await screen.findByRole("button", { name: "Acces pontaj" }),
    );
    await user.selectOptions(
      screen.getByLabelText("Categoria finală"),
      "Purchase",
    );
    await user.selectOptions(screen.getByLabelText("Status"), "resolved");
    await user.type(
      screen.getByLabelText("Mesaj de rezolvare"),
      "Access restored.",
    );
    await user.click(
      screen.getByRole("button", { name: "Salvează modificările" }),
    );
    await screen.findByText("Modificările au fost salvate.");
    const call = fetchMock.mock.calls.find(
      ([, init]) => init?.method === "PATCH",
    )!;
    expect(JSON.parse(String(call[1]?.body))).toEqual({
      final_category: "Purchase",
      status: "resolved",
      expected_version: 0,
      resolution_message: "Access restored.",
      request_id: expect.any(String),
    });
  });
  it("sends status filtering to the server", async () => {
    const fetchMock = mockApi(),
      user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.click(screen.getByRole("button", { name: "Tichete" }));
    await user.selectOptions(
      screen.getByLabelText("Filtrează după status"),
      "resolved",
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("status=resolved"),
        ),
      ).toBe(true),
    );
  });
  it("keeps the current conversation when cancelling a reset", async () => {
    mockApi();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.type(screen.getByLabelText("Mesajul tău"), "Problema mea");
    await user.click(screen.getByRole("button", { name: "Conversație nouă" }));
    await user.click(screen.getByRole("button", { name: "Rămân aici" }));
    expect(
      (screen.getByLabelText("Mesajul tău") as HTMLTextAreaElement).value,
    ).toBe("Problema mea");
  });
  it("logs out and shows the authentication screen", async () => {
    mockApi();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    sessionStorage.setItem(
      "helpdesk-unsaved:account-1:new",
      JSON.stringify({ text: "private", draft: null, uncertain: false }),
    );
    await user.click(screen.getAllByRole("button", { name: "Deconectare" })[0]);
    await screen.findByLabelText("Email");
    expect(screen.queryByLabelText("Mesajul tău")).toBeNull();
    expect(sessionStorage.getItem("helpdesk-unsaved:account-1:new")).toBeNull();
  });
  it("sends category and global search filters to the server", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Mesajul tău");
    await user.click(screen.getByRole("button", { name: "Tichete" }));
    await user.selectOptions(
      screen.getByLabelText("Filtrează după categorie"),
      "Hardware",
    );
    await user.type(screen.getByLabelText("Caută în toate tichetele"), "SAP");
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url]) =>
            String(url).includes("category=Hardware") &&
            String(url).includes("search=SAP"),
        ),
      ).toBe(true),
    );
  });
});
