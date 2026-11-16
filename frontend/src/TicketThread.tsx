import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { errorText, request } from "./api";
import type { Ticket } from "./api";

type Entry = {
  id: string;
  content: string;
  author: string;
  author_role: string;
  visibility: "public" | "internal";
  kind: string;
  created_at: string;
};
type Agent = { id: string; email: string };
export default function TicketThread({
  ticket,
  support,
  onChanged,
}: {
  ticket: Ticket;
  support: boolean;
  onChanged: (ticket: Ticket) => void;
}) {
  const [messages, setMessages] = useState<Entry[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [assignee, setAssignee] = useState(ticket.assignee_id ?? "");
  const [text, setText] = useState("");
  const [internal, setInternal] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [more, setMore] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const replyId = useRef<string | null>(null);
  const reopenId = useRef<string | null>(null);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setAssignee(ticket.assignee_id ?? "");
    Promise.all([
      request<Entry[]>(`/tickets/${ticket.id}/messages?limit=50`),
      support ? request<Agent[]>("/support/agents") : Promise.resolve([]),
    ])
      .then(([rows, people]) => {
        if (active) {
          setMessages(rows);
          setCursor(rows.at(-1)?.id ?? null);
          setMore(rows.length === 50);
          setAgents(people);
          setError("");
        }
      })
      .catch((cause) => {
        if (active) setError(errorText(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [ticket.id, ticket.version, ticket.assignee_id, support, refresh]);
  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function send(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      replyId.current ??= crypto.randomUUID();
      const result = await request<Entry>(
        `/tickets/${ticket.id}/messages`,
        "POST",
        {
          content: text.trim(),
          visibility: internal ? "internal" : "public",
          request_id: replyId.current,
        },
      );
      setMessages((rows) =>
        [...rows.filter((row) => row.id !== result.id), result].sort(
          (a, b) =>
            a.created_at.localeCompare(b.created_at) ||
            a.id.localeCompare(b.id),
        ),
      );
      setText("");
      replyId.current = null;
      setNotice(
        internal ? "Nota internă a fost salvată." : "Răspunsul a fost salvat.",
      );
    });
  }
  function assign(claim: boolean) {
    void run(async () => {
      const updated = await request<Ticket>(
        `/tickets/${ticket.id}/${claim ? "claim" : "assignment"}`,
        claim ? "POST" : "PUT",
        {
          expected_version: ticket.version,
          ...(!claim ? { assignee_id: assignee || null } : {}),
        },
      );
      onChanged(updated);
      setNotice("Atribuirea a fost salvată.");
    });
  }
  function reopen(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      reopenId.current ??= crypto.randomUUID();
      const updated = await request<Ticket>(
        `/tickets/${ticket.id}/reopen`,
        "POST",
        {
          reason: reason.trim(),
          expected_version: ticket.version,
          request_id: reopenId.current,
        },
      );
      onChanged(updated);
      setNotice("Tichetul a fost redeschis.");
      setReason("");
      reopenId.current = null;
    });
  }
  return (
    <section className="ticket-thread" aria-label="Colaborare pe tichet">
      <dl className="metadata">
        <dt>Responsabil</dt>
        <dd>{ticket.assignee_email || ticket.assignee_id || "Neatribuit"}</dd>
        <dt>Prioritate</dt>
        <dd>
          {
            {
              low: "Scăzută",
              normal: "Normală",
              high: "Ridicată",
              urgent: "Urgentă",
            }[ticket.priority ?? "normal"]
          }
        </dd>
        <dt>Actualizat</dt>
        <dd>
          {ticket.updated_at
            ? new Date(ticket.updated_at).toLocaleString("ro-RO")
            : "Necunoscut pentru datele istorice"}
        </dd>
        <dt>Prima rezolvare</dt>
        <dd>
          {ticket.first_resolved_at
            ? new Date(ticket.first_resolved_at).toLocaleString("ro-RO")
            : "Neînregistrată"}
        </dd>
      </dl>
      {support && (
        <div className="assignment-controls">
          <label htmlFor="ticket-assignee">Agent responsabil</label>
          <select
            id="ticket-assignee"
            value={assignee}
            disabled={busy || loading}
            onChange={(event) => setAssignee(event.target.value)}
          >
            <option value="">Neatribuit</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.email}
              </option>
            ))}
          </select>
          <div className="actions">
            {!ticket.assignee_id && (
              <button
                type="button"
                className="button secondary"
                disabled={busy || loading}
                onClick={() => assign(true)}
              >
                Preia tichetul
              </button>
            )}
            <button
              type="button"
              className="button secondary"
              disabled={
                busy || loading || assignee === (ticket.assignee_id ?? "")
              }
              onClick={() => assign(false)}
            >
              Salvează atribuirea
            </button>
          </div>
        </div>
      )}
      <h3>Conversația de suport</h3>
      <p className="hint">
        Acest fir este separat de conversația inițială cu AI. Mesajele nu
        schimbă automat statusul.
      </p>
      {loading && <p role="status">Se încarcă mesajele…</p>}
      {!loading && !messages.length && !error && (
        <p className="muted">Nu există mesaje pe tichet.</p>
      )}
      <ol className="ticket-messages">
        {messages.map((entry) => (
          <li
            key={entry.id}
            className={
              entry.visibility === "internal" ? "internal-note" : "public-reply"
            }
          >
            <small>
              {entry.author} ·{" "}
              {new Date(entry.created_at).toLocaleString("ro-RO")} ·{" "}
              {entry.visibility === "internal"
                ? "NOTĂ INTERNĂ"
                : entry.kind === "resolution"
                  ? "REZOLVARE"
                  : entry.kind === "reopen"
                    ? "REDESCHIDERE"
                    : "RĂSPUNS PUBLIC"}
            </small>
            <p className="preserve">{entry.content}</p>
          </li>
        ))}
      </ol>
      {more && (
        <button
          type="button"
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const rows = await request<Entry[]>(
                `/tickets/${ticket.id}/messages?limit=50&after_id=${cursor ?? ""}`,
              );
              setMessages((previous) =>
                [
                  ...previous,
                  ...rows.filter(
                    (row) => !previous.some((item) => item.id === row.id),
                  ),
                ].sort(
                  (a, b) =>
                    a.created_at.localeCompare(b.created_at) ||
                    a.id.localeCompare(b.id),
                ),
              );
              setCursor(rows.at(-1)?.id ?? cursor);
              setMore(rows.length === 50);
            })
          }
        >
          Mai multe mesaje
        </button>
      )}
      <form onSubmit={send}>
        <label htmlFor="ticket-reply">
          {internal ? "Notă internă" : "Răspuns public"}
        </label>
        <textarea
          id="ticket-reply"
          rows={3}
          maxLength={4000}
          required
          value={text}
          disabled={busy}
          onChange={(event) => {
            setText(event.target.value);
            replyId.current = null;
          }}
        />
        {support && (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={internal}
              disabled={busy}
              onChange={(event) => {
                setInternal(event.target.checked);
                replyId.current = null;
              }}
            />{" "}
            Notă internă, vizibilă numai suportului
          </label>
        )}
        <button className="button primary" disabled={busy || !text.trim()}>
          {busy
            ? "Se salvează…"
            : internal
              ? "Adaugă nota"
              : "Trimite răspunsul"}
        </button>
      </form>
      {ticket.status === "resolved" && (
        <form onSubmit={reopen}>
          <label htmlFor="reopen-reason">Motivul redeschiderii</label>
          <textarea
            id="reopen-reason"
            rows={2}
            maxLength={4000}
            required
            disabled={busy}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              reopenId.current = null;
            }}
          />
          <button
            className="button secondary"
            disabled={busy || !reason.trim()}
          >
            Redeschide tichetul
          </button>
        </form>
      )}
      {notice && <p role="status">{notice}</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <button
        type="button"
        className="button secondary"
        disabled={busy || loading}
        onClick={() =>
          void run(async () => {
            onChanged(await request<Ticket>(`/tickets/${ticket.id}`));
            setRefresh((v) => v + 1);
          })
        }
      >
        Reîncarcă detaliile și mesajele
      </button>
    </section>
  );
}
