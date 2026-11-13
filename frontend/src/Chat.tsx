import Dialog from "./Dialog";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  CircleAlert,
  FileText,
  Laptop,
  LoaderCircle,
  LockKeyhole,
  MessageCircle,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { ApiError, errorText, request, statusLabels } from "./api";
import type { Draft, Message, Ticket } from "./api";
type Conversation = { id: string; title: string; ticket_id: string | null };
type Props = {
  accountId: string;
  onCreated: () => void;
  onViewTickets: (ticketId?: string) => void;
};
export default function Chat({ accountId, onCreated, onViewTickets }: Props) {
  const [history, setHistory] = useState<Conversation[]>([]);
  const [historyPage, setHistoryPage] = useState(0);
  const [historyError, setHistoryError] = useState("");
  const [restoring, setRestoring] = useState(true);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [id, setId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState<"message" | "draft" | "confirm" | null>(
    null,
  );
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [resetDialog, setResetDialog] = useState(false);
  const [confirmationBlocked, setConfirmationBlocked] = useState(false);
  const storageKey = `helpdesk-conversation-${accountId}`;
  useEffect(() => {
    let active = true;
    request<Conversation[]>(
      `/conversations?limit=21&offset=${historyPage * 20}`,
    )
      .then((rows) => {
        if (active) {
          setHistory(rows);
          setHistoryError("");
        }
      })
      .catch((cause) => {
        if (active) setHistoryError(errorText(cause));
      });
    return () => {
      active = false;
    };
  }, [historyPage, historyVersion]);
  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) void restore(saved).finally(() => setRestoring(false));
    else setRestoring(false);
    // Restore only when the authenticated account changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);
  async function restore(conversationId: string) {
    if (lock.current) return;
    lock.current = true;
    setBusy("message");
    setError("");
    try {
      const [detail, rows] = await Promise.all([
        request<{ ticket: Ticket | null }>(`/conversations/${conversationId}`),
        request<Message[]>(`/conversations/${conversationId}/messages`),
      ]);
      setId(conversationId);
      setMessages(rows);
      setTicket(detail.ticket);
      setDraft(null);
      setText("");
      setConfirmationBlocked(false);
      localStorage.setItem(storageKey, conversationId);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      lock.current = false;
      setBusy(null);
    }
  }
  const lock = useRef(false);
  const log = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages, busy]);
  function begin(operation: "message" | "draft" | "confirm") {
    if (lock.current) return false;
    lock.current = true;
    setBusy(operation);
    setError("");
    return true;
  }
  function end() {
    lock.current = false;
    setBusy(null);
    setPending("");
  }
  function reset() {
    localStorage.removeItem(storageKey);
    setId(null);
    setMessages([]);
    setText("");
    setDraft(null);
    setTicket(null);
    setError("");
    setConfirmationBlocked(false);
    setResetDialog(false);
  }
  async function send(event: FormEvent) {
    event.preventDefault();
    const content = text.trim();
    if (!content || draft || ticket || !begin("message")) return;
    setPending(content);
    try {
      let conversation = id;
      if (!conversation) {
        const result = await request<{ id: string }>(
          "/conversations",
          "POST",
          {},
        );
        conversation = result.id;
        setId(conversation);
        localStorage.setItem(storageKey, conversation);
      }
      const turn = await request<{
        user_message: Message;
        assistant_message: Message;
      }>(`/conversations/${conversation}/messages`, "POST", { content });
      setMessages((previous) => [
        ...previous,
        turn.user_message,
        turn.assistant_message,
      ]);
      setText("");
      setHistoryVersion((value) => value + 1);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      end();
    }
  }
  async function prepare() {
    if (!id || ticket || !begin("draft")) return;
    try {
      setDraft(
        await request<Draft>(`/conversations/${id}/ticket-draft`, "POST", {}),
      );
      setConfirmationBlocked(false);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      end();
    }
  }
  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (!id || !draft || ticket || confirmationBlocked || !begin("confirm"))
      return;
    try {
      const result = await request<Ticket>(
        `/conversations/${id}/tickets`,
        "POST",
        {
          title: draft.title.trim(),
          description: draft.description.trim(),
          last_message_id: draft.last_message_id,
          confirmed: true,
        },
      );
      setTicket(result);
      setDraft(null);
      onCreated();
      setHistoryVersion((value) => value + 1);
    } catch (cause) {
      setError(errorText(cause));
      if (
        cause instanceof ApiError &&
        (cause.status === 409 || cause.status === 0)
      )
        setConfirmationBlocked(true);
    } finally {
      end();
    }
  }
  const step = ticket ? 3 : draft ? 2 : 1;
  return (
    <div className="page">
      <section
        className="card history-bar"
        aria-label="Istoricul conversațiilor"
      >
        <label htmlFor="conversation-history">Conversațiile mele</label>
        <select
          id="conversation-history"
          value={history.some((row) => row.id === id) ? (id ?? "") : ""}
          disabled={!!busy || restoring}
          onChange={(e) => {
            if (e.target.value) {
              if (
                (text || draft) &&
                !window.confirm(
                  "Ciorna și mesajul nesent se vor pierde. Continui?",
                )
              )
                return;
              void restore(e.target.value);
            }
          }}
        >
          <option value="">Alege o conversație</option>
          {history.slice(0, 20).map((row) => (
            <option key={row.id} value={row.id}>
              {row.title}
              {row.ticket_id ? " · Tichet creat" : ""}
            </option>
          ))}
        </select>
        <button
          className="button secondary"
          disabled={!historyPage || !!busy}
          onClick={() => setHistoryPage((p) => p - 1)}
        >
          Mai recente
        </button>
        <button
          className="button secondary"
          disabled={history.length <= 20 || !!busy}
          onClick={() => setHistoryPage((p) => p + 1)}
        >
          Mai vechi
        </button>
        {historyError && <p role="alert">{historyError}</p>}
        {restoring && <p role="status">Se restaurează conversația…</p>}
      </section>
      <header className="page-heading">
        <div>
          <p className="eyebrow">ASISTENTUL TĂU IT</p>
          <h1>
            O problemă mai puțin.<span>Începe cu o conversație.</span>
          </h1>
          <p className="lead">
            Spune-ne ce se întâmplă. Pregătim împreună cererea de suport.
          </p>
        </div>
        <button
          className="button secondary"
          disabled={!!busy}
          onClick={() =>
            messages.length || text || draft ? setResetDialog(true) : reset()
          }
        >
          <Plus size={16} />
          Conversație nouă
        </button>
      </header>
      <ol className="steps">
        {["Descrie problema", "Verifică ciorna", "Confirmă tichetul"].map(
          (label, index) => (
            <li
              key={label}
              className={
                step === index + 1
                  ? "current"
                  : step > index + 1
                    ? "complete"
                    : ""
              }
            >
              <span>{step > index + 1 ? <Check size={13} /> : index + 1}</span>
              {label}
            </li>
          ),
        )}
      </ol>
      <div className="chat-layout">
        <section className="card chat-card">
          <div className="card-heading">
            <span className="assistant-mark">
              <Sparkles size={20} />
            </span>
            <div>
              <h2>Asistent Helpdesk</h2>
              <p>Clarificăm problema, pas cu pas.</p>
            </div>
            <span className="badge subtle">RO / EN</span>
          </div>
          <div
            className="message-log"
            ref={log}
            role="log"
            aria-label="Mesajele conversației"
            aria-live="polite"
          >
            {!messages.length && !pending && (
              <div className="empty-chat">
                <span className="empty-symbol">
                  <MessageCircle size={32} />
                </span>
                <h2>Cu ce te putem ajuta?</h2>
                <p>
                  O aplicație, un dispozitiv sau o cerere de acces.
                  <br />
                  Începe cu problema pe care o întâmpini.
                </p>
                <div className="suggestions">
                  {[
                    {
                      icon: LockKeyhole,
                      text: "Nu mă pot conecta la aplicația de pontaj.",
                    },
                    {
                      icon: Laptop,
                      text: "Laptopul meu se blochează în timpul ședințelor.",
                    },
                  ].map((item) => (
                    <button
                      key={item.text}
                      disabled={!!busy}
                      onClick={() => setText(item.text)}
                    >
                      <item.icon size={17} />
                      {item.text}
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message) => (
              <article key={message.id} className={`message ${message.role}`}>
                <small>{message.role === "user" ? "TU" : "ASISTENT"}</small>
                <p>{message.content}</p>
              </article>
            ))}
            {pending && (
              <article className="message user pending">
                <small>TU · SE TRIMITE</small>
                <p>{pending}</p>
              </article>
            )}
            {busy && (
              <p className="loading" role="status">
                <LoaderCircle className="spin" size={17} />
                {busy === "message"
                  ? "Asistentul pregătește răspunsul…"
                  : busy === "draft"
                    ? "Pregătim ciorna tichetului…"
                    : "Salvăm tichetul…"}
              </p>
            )}
          </div>
          {error && (
            <div role="alert" className="error">
              <CircleAlert size={18} />
              <div>
                {error}
                {confirmationBlocked && (
                  <p>
                    Verifică lista de tichete înainte să încerci din nou.
                    Conversația poate avea deja un tichet sau ciorna trebuie
                    regenerată.
                  </p>
                )}
              </div>
            </div>
          )}
          {!draft && !ticket && (
            <form className="composer" onSubmit={send}>
              <label htmlFor="chat-message">Mesajul tău</label>
              <textarea
                id="chat-message"
                placeholder="Descrie problema aici…"
                value={text}
                onChange={(event) => setText(event.target.value)}
                maxLength={1000}
                rows={3}
                disabled={!!busy}
              />
              <div className="composer-bottom">
                <small>
                  {text.length}/1000 · Fără parole sau coduri de autentificare.
                </small>
                <button
                  className="button primary"
                  disabled={!!busy || !text.trim()}
                >
                  <Send size={15} />
                  Trimite
                </button>
              </div>
            </form>
          )}
          {draft && (
            <form className="draft-form" onSubmit={confirm}>
              <div className="section-label">
                <FileText size={18} />
                CIORNĂ · NESALVATĂ
              </div>
              <h2>Verifică detaliile</h2>
              <p className="muted">
                Corectează informațiile înainte de creare.
              </p>
              <label htmlFor="draft-title">Titlu</label>
              <input
                id="draft-title"
                maxLength={160}
                required
                disabled={!!busy}
                value={draft.title}
                onChange={(event) =>
                  setDraft({ ...draft, title: event.target.value })
                }
              />
              <label htmlFor="draft-description">Descriere</label>
              <textarea
                id="draft-description"
                rows={6}
                maxLength={2000}
                required
                disabled={!!busy}
                value={draft.description}
                onChange={(event) =>
                  setDraft({ ...draft, description: event.target.value })
                }
              />
              <div className="category-line">
                Categorie propusă{" "}
                <span className="badge">{draft.predicted_category}</span>
              </div>
              <p className="hint">
                Categoria se recalculează la confirmare, folosind textul editat.
              </p>
              <div className="actions">
                <button
                  type="button"
                  className="button secondary"
                  disabled={!!busy}
                  onClick={() => {
                    setDraft(null);
                    setError("");
                    setConfirmationBlocked(false);
                  }}
                >
                  Continuă conversația
                </button>
                <button
                  className="button primary"
                  disabled={
                    !!busy ||
                    confirmationBlocked ||
                    !draft.title.trim() ||
                    !draft.description.trim()
                  }
                >
                  <Check size={16} />
                  Confirmă și creează
                </button>
              </div>
              {confirmationBlocked && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => onViewTickets(ticket?.id)}
                >
                  Verifică lista de tichete →
                </button>
              )}
            </form>
          )}
          {ticket && (
            <div className="success-panel" role="status">
              <CheckCircle2 size={36} />
              <p className="eyebrow">TICHET CREAT</p>
              <p>
                Conversația este închisă pentru mesaje noi. Pentru altă
                problemă, începe o conversație nouă.
              </p>
              <h2>{ticket.title}</h2>
              <p className="preserve">{ticket.text}</p>
              <div className="category-line">
                <span className="badge">{ticket.final_category}</span>
                <span className="badge subtle">
                  {statusLabels[ticket.status]}
                </span>
              </div>
              <p className="hint mono">ID: {ticket.id}</p>
              <button
                className="button primary"
                onClick={() => onViewTickets(ticket?.id)}
              >
                Vezi tichetele
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </section>
        <aside className="guide">
          <p className="eyebrow">UN TICHET CLAR, MAI UȘOR DE REZOLVAT</p>
          <h2>Detaliile fac diferența.</h2>
          <p>Ajută-ne să înțelegem situația fără să ghicim.</p>
          <ul>
            <li>
              <span>01</span>
              <div>
                <strong>Ce este afectat?</strong>
                <p>Numele aplicației sau dispozitivului.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Ce se întâmplă?</strong>
                <p>Mesajul de eroare și momentul apariției.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Cum te afectează?</strong>
                <p>Ce activitate nu poți continua.</p>
              </div>
            </li>
          </ul>
          {messages.length > 0 && !draft && !ticket && (
            <div className="prepare-box">
              <FileText size={22} />
              <strong>Ai oferit detaliile?</strong>
              <p>Pregătește un rezumat pe care îl poți edita.</p>
              <button
                className="button primary"
                onClick={prepare}
                disabled={!!busy || !!text.trim()}
              >
                Pregătește tichetul
                <ArrowRight size={15} />
              </button>
              {text.trim() && <small>Trimite sau șterge mesajul nesent.</small>}
            </div>
          )}
          <div className="privacy-note">
            <LockKeyhole size={16} />
            <p>
              Nu include parole, coduri de autentificare sau alte informații
              secrete.
            </p>
          </div>
        </aside>
      </div>
      {resetDialog && (
        <Dialog label="reset-title" onClose={() => setResetDialog(false)}>
          <button
            className="icon-button close"
            aria-label="Închide"
            onClick={() => setResetDialog(false)}
          >
            <X size={20} />
          </button>
          <h2 id="reset-title">Începi o conversație nouă?</h2>
          <p>
            Mesajele trimise rămân în istoric și poți redeschide conversația.
            Ciorna și mesajul nesent se pierd.
          </p>
          <div className="actions">
            <button
              autoFocus
              className="button secondary"
              onClick={() => setResetDialog(false)}
            >
              Rămân aici
            </button>
            <button className="button primary" onClick={reset}>
              Conversație nouă
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
