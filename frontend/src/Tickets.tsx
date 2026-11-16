import TicketThread from "./TicketThread";
import Dialog from "./Dialog";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Download,
  Check,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Search,
  Ticket as TicketIcon,
  X,
} from "lucide-react";
import { categories, downloadCsv, errorText, request, statusLabels } from "./api";
import type { Status, Ticket } from "./api";
const date = (value: string) =>
  new Intl.DateTimeFormat("ro-RO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
type CategoryReview = {
  id: string;
  verified_category: (typeof categories)[number];
  model_version: string;
  text_sha256: string;
  reason: string | null;
  reviewed_at: string;
};
export default function Tickets({
  refresh,
  support,
  initialTicketId,
}: {
  refresh: number;
  support: boolean;
  initialTicketId?: string | null;
}) {
  const [dashboard, setDashboard] = useState<{
    days: number;
    status_counts: { status: string; count: number }[];
    unassigned_count: number;
    category_counts: { category: string; count: number }[];
    priority_counts: { priority: string; count: number }[];
    avg_first_reply_seconds: number | null; without_public_support_reply: number;
    avg_first_resolution_seconds: number | null; without_first_resolution_event: number;
  } | null>(null);
  const [dashboardError, setDashboardError] = useState("");
  const [review, setReview] = useState<CategoryReview | null>(null);
  const [reviewCategory, setReviewCategory] = useState<(typeof categories)[number]>("Access");
  const [reviewReason, setReviewReason] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportError, setExportError] = useState("");
  const reviewRequestId = useRef<string | null>(null);
  const [rows, setRows] = useState<Ticket[]>([]);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [assignmentFilter, setAssignmentFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [priority, setPriority] = useState<Ticket["priority"]>("normal");
  const [events, setEvents] = useState<
    {
      id: number;
      field: string;
      old_value: string;
      new_value: string;
      actor: string;
      created_at: string;
    }[]
  >([]);
  const [eventsError, setEventsError] = useState("");
  const [eventsLoading, setEventsLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState<Status>("open");
  const [resolution, setResolution] = useState("");
  const resolutionId = useRef<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [notice, setNotice] = useState("");
  const saveLock = useRef(false);
  useEffect(() => {
    let active = true;
    if (!initialTicketId) return;
    request<Ticket>(`/tickets/${initialTicketId}`)
      .then((ticket) => {
        if (!active) return;
        setSelected(ticket);
        setCategory(ticket.final_category);
        setStatus(ticket.status);
        setPriority(ticket.priority ?? "normal");
      })
      .catch((cause) => {
        if (active) setError(errorText(cause));
      });
    return () => {
      active = false;
    };
  }, [initialTicketId]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setRows([]);
    const query = new URLSearchParams({
      limit: "21",
      offset: String(page * 20),
    });
    if (filter) query.set("status", filter);
    if (categoryFilter) query.set("category", categoryFilter);
    if (priorityFilter) query.set("priority", priorityFilter);
    if (assignmentFilter === "mine") query.set("assigned_to_me", "true");
    if (assignmentFilter === "unassigned") query.set("unassigned", "true");
    if (search) query.set("search", search);
    request<Ticket[]>(`/tickets?${query}`)
      .then((result) => {
        if (active) setRows(result);
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
  }, [
    filter,
    categoryFilter,
    priorityFilter,
    assignmentFilter,
    search,
    page,
    reload,
    refresh,
  ]);
  useEffect(() => {
    if (!support) return;
    request<NonNullable<typeof dashboard>>("/support/dashboard?days=30")
      .then((data) => {
        setDashboard(data);
        setDashboardError("");
      })
      .catch((cause) => {
        setDashboard(null);
        setDashboardError(errorText(cause));
      });
  }, [support, reload, refresh]);
  useEffect(() => {
    let active = true;
    if (!selected) return;
    setEvents([]);
    setEventsError("");
    setEventsLoading(true);
    request<typeof events>(`/tickets/${selected.id}/events`)
      .then((rows) => {
        if (active) setEvents(rows);
      })
      .catch((cause) => {
        if (active) setEventsError(errorText(cause));
      })
      .finally(() => {
        if (active) setEventsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  useEffect(() => {
    let active = true;
    if (!selected || !support) {
      setReview(null);
      return;
    }
    setReview(null);
    setReviewCategory(selected.final_category as (typeof categories)[number]);
    setReviewReason("");
    setReviewError("");
    request<{ review: CategoryReview | null }>(
      `/tickets/${selected.id}/category-review`,
    )
      .then(({ review: data }) => {
        if (!active) return;
        setReview(data);
        if (data) {
          setReviewCategory(data.verified_category);
          setReviewReason(data.reason ?? "");
        }
      })
      .catch((cause) => {
        if (active) setReviewError(errorText(cause));
      });
    return () => {
      active = false;
    };
  }, [selected, support]);
  function open(ticket: Ticket) {
    setSelected(ticket);
    setCategory(ticket.final_category);
    setStatus(ticket.status);
    setPriority(ticket.priority ?? "normal");
    setSaveError("");
    setResolution("");
    resolutionId.current = null;
    setNotice("");
    reviewRequestId.current = null;
  }
  async function saveCategoryReview(event: FormEvent) {
    event.preventDefault();
    if (!selected || reviewBusy) return;
    setReviewBusy(true);
    setReviewError("");
    reviewRequestId.current ??= crypto.randomUUID();
    try {
      const result = await request<CategoryReview>(
        `/tickets/${selected.id}/category-review`,
        "POST",
        {
          verified_category: reviewCategory,
          reason: reviewReason.trim() || null,
          request_id: reviewRequestId.current,
        },
      );
      setReview(result);
      reviewRequestId.current = null;
    } catch (cause) {
      setReviewError(errorText(cause));
    } finally {
      setReviewBusy(false);
    }
  }
  async function exportReviewed() {
    if (exportBusy) return;
    setExportBusy(true);
    setExportError("");
    try {
      await downloadCsv(
        "/support/category-review-export",
        "ai-helpdesk-reviewed-examples.csv",
      );
    } catch (cause) {
      setExportError(errorText(cause));
    } finally {
      setExportBusy(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected || saveLock.current) return;
    saveLock.current = true;
    setSaving(true);
    setSaveError("");
    try {
      const resolving = status === "resolved" && selected.status !== "resolved";
      if (resolving) resolutionId.current ??= crypto.randomUUID();
      await request<Ticket>(`/tickets/${selected.id}`, "PATCH", {
        final_category: category,
        status,
        priority,
        expected_version: selected.version,
        ...(resolving
          ? {
              resolution_message: resolution.trim(),
              request_id: resolutionId.current,
            }
          : {}),
      });
      setSelected(null);
      setNotice("Modificările au fost salvate.");
      setReload((value) => value + 1);
    } catch (cause) {
      setSaveError(errorText(cause));
    } finally {
      setSaving(false);
      saveLock.current = false;
    }
  }
  const pageRows = rows.slice(0, 20);
  const visible = pageRows;
  return (
    <div className="page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">ORGANIZARE ȘI URMĂRIRE</p>
          <h1>Suportul, într-un singur loc.</h1>
          <p className="lead">
            {support
              ? "Urmărește cererile și ajustează categoria atunci când este nevoie."
              : "Urmărește starea cererilor tale de suport."}
          </p>
        </div>
        <button
          className="button secondary"
          disabled={loading}
          onClick={() => setReload((value) => value + 1)}
        >
          <RefreshCw size={16} />
          Actualizează
        </button>
        {support && (
          <button
            className="button secondary"
            disabled={exportBusy}
            onClick={() => void exportReviewed()}
          >
            <Download size={16} />
            {exportBusy ? "Se exportă…" : "Exportă exemple revizuite"}
          </button>
        )}
      </header>
      {support && exportError && <p className="error" role="alert">Exportul a eșuat: {exportError}</p>}
      <div className="ticket-intro">
        <span className="assistant-mark">
          <TicketIcon size={22} />
        </span>
        <div>
          <strong>De la cerere la rezolvare</strong>
          <p>Deschis → În lucru → Rezolvat</p>
        </div>
        <span className="badge subtle">Cele mai recente primele</span>
      </div>
      {support && dashboard && (
        <section
          className="card support-dashboard"
          aria-label={`Rezumat support pe ultimele ${dashboard.days} de zile`}
        >
          <h2>Rezumat · ultimele {dashboard.days} zile</h2>
          <div className="dashboard-grid">
            <div>
              <strong>{dashboard.unassigned_count}</strong>
              <span>Neatribuite</span>
            </div>
            {dashboard.status_counts.map((item) => (
              <div key={item.status}>
                <strong>{item.count}</strong>
                <span>{statusLabels[item.status as Status] ?? item.status}</span>
              </div>
            ))}
            <div>
              <strong>
                {dashboard.avg_first_reply_seconds === null
                  ? "—"
                  : `${Math.round(dashboard.avg_first_reply_seconds / 60)} min`}
              </strong>
              <span>
                Primul răspuns public · {dashboard.without_public_support_reply} fără
                răspuns
              </span>
            </div>
            <div>
              <strong>
                {dashboard.avg_first_resolution_seconds === null
                  ? "—"
                  : `${Math.round(dashboard.avg_first_resolution_seconds / 3600)} h`}
              </strong>
              <span>
                Prima rezolvare · {dashboard.without_first_resolution_event} fără eveniment
              </span>
            </div>
          </div>
          <p className="muted">
            Metrici descriptive, nu SLA-uri. Media include numai evenimente cunoscute;
            notele interne și răspunsurile utilizatorilor sunt excluse.
          </p>
          <p className="muted">
            Categorii: {dashboard.category_counts.map((x) => `${x.category} ${x.count}`).join(" · ") || "—"} ·
            Priorități: {dashboard.priority_counts.map((x) => `${x.priority} ${x.count}`).join(" · ") || "—"}
          </p>
        </section>
      )}
      {support && dashboardError && (
        <p className="error" role="alert">
          Rezumatul nu este disponibil: {dashboardError}. Folosește Actualizează pentru
          retry.
        </p>
      )}
      <section className="card ticket-list">
        <div className="list-toolbar">
          <div>
            <h2>Tichete</h2>
            <p className="muted">
              {loading
                ? "Se încarcă…"
                : `${pageRows.length} înregistrări pe această pagină`}
            </p>
          </div>
          <div className="filters">
            <label>
              Categorie
              <select
                aria-label="Filtrează după categorie"
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(0);
                }}
              >
                <option value="">Toate categoriile</option>
                {categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            {support && (
              <label>
                Prioritate
                <select
                  aria-label="Filtrează după prioritate"
                  value={priorityFilter}
                  onChange={(event) => {
                    setPriorityFilter(event.target.value);
                    setPage(0);
                  }}
                >
                  <option value="">Toate prioritățile</option>
                  {["low", "normal", "high", "urgent"].map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </label>
            )}
            {support && (
              <label>
                Atribuire
                <select
                  aria-label="Filtrează după atribuire"
                  value={assignmentFilter}
                  onChange={(event) => {
                    setAssignmentFilter(event.target.value);
                    setPage(0);
                  }}
                >
                  <option value="">Toate tichetele</option>
                  <option value="mine">Atribuite mie</option>
                  <option value="unassigned">Neatribuite</option>
                </select>
              </label>
            )}
            <label className="search-field">
              <Search size={17} />
              <input
                aria-label="Caută în toate tichetele"
                placeholder="Caută în toate tichetele"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(0);
                }}
              />
            </label>
            <select
              aria-label="Filtrează după status"
              value={filter}
              onChange={(event) => {
                setFilter(event.target.value);
                setPage(0);
                setSearch("");
              }}
            >
              <option value="">Toate statusurile</option>
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>
        {notice && (
          <div className="notice" role="status">
            <Check size={17} />
            {notice}
          </div>
        )}
        {error ? (
          <div className="list-empty">
            <CircleAlert size={28} />
            <p role="alert">{error}</p>
            <button
              className="button secondary"
              onClick={() => setReload((value) => value + 1)}
            >
              Încearcă din nou
            </button>
          </div>
        ) : loading ? (
          <div className="list-empty" role="status">
            <LoaderCircle className="spin" size={28} />
            <p>Încărcăm tichetele…</p>
          </div>
        ) : !visible.length ? (
          <div className="list-empty">
            <TicketIcon size={32} />
            <h3>
              {search
                ? "Niciun rezultat în pagina curentă"
                : "Niciun tichet pe această pagină"}
            </h3>
            <p>
              {search
                ? "Încearcă alt text sau golește căutarea."
                : "Creează un tichet din conversație sau schimbă filtrul."}
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>TICHET</th>
                  <th>CATEGORIE</th>
                  <th>STATUS</th>
                  <th>CREAT</th>
                  <th>
                    <span className="sr-only">Detalii</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>
                      <button
                        className="ticket-title"
                        onClick={() => open(ticket)}
                      >
                        {ticket.title || ticket.text.slice(0, 90)}
                      </button>
                      <small className="ticket-id">
                        #{ticket.id.slice(0, 8)}
                      </small>
                    </td>
                    <td>
                      <span className="badge subtle">
                        {ticket.final_category}
                      </span>
                    </td>
                    <td>
                      <span className={`status ${ticket.status}`}>
                        <i />
                        {statusLabels[ticket.status]}
                      </span>
                    </td>
                    <td className="date-cell">{date(ticket.created_at)}</td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Detalii tichet ${ticket.id}`}
                        onClick={() => open(ticket)}
                      >
                        <ArrowRight size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pagination">
          <span>Pagina {page + 1}</span>
          <div>
            <button
              className="button secondary"
              disabled={!page || loading}
              onClick={() => {
                setPage((value) => value - 1);
                setSearch("");
              }}
            >
              <ArrowLeft size={15} />
              Înapoi
            </button>
            <button
              className="button secondary"
              disabled={rows.length <= 20 || loading || !!error}
              onClick={() => {
                setPage((value) => value + 1);
                setSearch("");
              }}
            >
              Înainte
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </section>
      {selected && (
        <Dialog
          wide
          label="ticket-detail-title"
          onClose={() => {
            if (!saveLock.current) setSelected(null);
          }}
        >
          <button
            className="icon-button close"
            aria-label="Închide detaliile"
            disabled={saving}
            onClick={() => setSelected(null)}
          >
            <X size={20} />
          </button>
          <p className="eyebrow">DETALII TICHET</p>
          <h2 id="ticket-detail-title">
            {selected.title || "Cerere de suport"}
          </h2>
          <p className="hint mono">{selected.id}</p>
          <div className="ticket-body preserve">{selected.text}</div>
          <p>
            Impact declarat: {
              ({ individual: "Doar eu", team: "Echipa mea", organization: "Organizația" } as Record<string, string>)[selected.impact ?? ""] ?? "Nespecificat"
            }
          </p>
          <dl className="metadata">
            <dt>Creat</dt>
            <dd>{date(selected.created_at)}</dd>
            {support && (
              <>
                <dt>Predicție originală</dt>
                <dd>{selected.predicted_category}</dd>
                <dt>Versiune model</dt>
                <dd>{selected.model_version}</dd>
              </>
            )}
          </dl>
          {support && (
            <form className="category-review" onSubmit={saveCategoryReview}>
              <h3>Revizuire explicită pentru evaluare ML</h3>
              <p className="hint">
                Corectarea categoriei tichetului nu aprobă automat acest exemplu.
                Confirmă separat eticheta și verifică textul înainte de export.
              </p>
              {review && (
                <p role="status">
                  Exemplu revizuit la {date(review.reviewed_at)} · {review.model_version}
                </p>
              )}
              {reviewError && <p role="alert" className="error">{reviewError}</p>}
              <label htmlFor="verified-category">Etichetă verificată</label>
              <select
                id="verified-category"
                value={reviewCategory}
                disabled={reviewBusy}
                onChange={(event) => {
                  setReviewCategory(event.target.value as (typeof categories)[number]);
                  reviewRequestId.current = null;
                }}
              >
                {categories.map((item) => <option key={item}>{item}</option>)}
              </select>
              <label htmlFor="review-reason">Motiv (opțional)</label>
              <textarea
                id="review-reason"
                maxLength={1000}
                value={reviewReason}
                disabled={reviewBusy}
                onChange={(event) => {
                  setReviewReason(event.target.value);
                  reviewRequestId.current = null;
                }}
              />
              <button className="button secondary" disabled={reviewBusy}>
                {reviewBusy ? "Se salvează…" : "Marchează ca revizuit"}
              </button>
            </form>
          )}
          <TicketThread
            key={selected.id}
            ticket={selected}
            support={support}
            onChanged={(updated) => {
              setSelected(updated);
              setCategory((current) =>
                current === selected.final_category
                  ? updated.final_category
                  : current,
              );
              setStatus((current) =>
                current === selected.status ? updated.status : current,
              );
              setReload((value) => value + 1);
            }}
          />
          <h3>Istoricul modificărilor</h3>
          {eventsLoading && <p role="status">Se încarcă istoricul…</p>}
          {eventsError && (
            <p role="alert" className="error">
              {eventsError}
            </p>
          )}
          {!eventsLoading && !eventsError && !events.length && (
            <p className="muted">Nu există modificări.</p>
          )}
          <ul className="audit-list">
            {events.map((event) => (
              <li key={event.id}>
                {date(event.created_at)} · {event.actor} ·{" "}
                {{
                  status: "Status",
                  final_category: "Categorie",
                  assignee_id: "Responsabil",
                  priority: "Prioritate",
                }[event.field] ?? event.field}
                : {event.old_value} → {event.new_value}
              </li>
            ))}
          </ul>
          {!support && (
            <p>
              Categorie: {selected.final_category} · Status:{" "}
              {statusLabels[selected.status]}
            </p>
          )}
          {support && (
            <form onSubmit={save}>
              <div className="edit-grid">
                <div>
                  <label htmlFor="edit-category">Categoria finală</label>
                  <select
                    id="edit-category"
                    value={category}
                    disabled={saving}
                    onChange={(event) => setCategory(event.target.value)}
                  >
                    {categories.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="edit-priority">Prioritate</label>
                  <select
                    id="edit-priority"
                    value={priority}
                    disabled={saving}
                    onChange={(event) =>
                      setPriority(event.target.value as Ticket["priority"])
                    }
                  >
                    <option value="low">Scăzută</option>
                    <option value="normal">Normală</option>
                    <option value="high">Ridicată</option>
                    <option value="urgent">Urgentă</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="edit-status">Status</label>
                  <select
                    id="edit-status"
                    value={status}
                    disabled={saving}
                    onChange={(event) =>
                      setStatus(event.target.value as Status)
                    }
                  >
                    {Object.entries(statusLabels)
                      .filter(
                        ([value]) =>
                          selected.status !== "resolved" ||
                          value === "resolved",
                      )
                      .map(([value, label]) => (
                        <option value={value} key={value}>
                          {label}
                        </option>
                      ))}
                  </select>
                </div>
              </div>
              {status === "resolved" && selected.status !== "resolved" && (
                <>
                  <label htmlFor="resolution-message">Mesaj de rezolvare</label>
                  <textarea
                    id="resolution-message"
                    required
                    maxLength={4000}
                    disabled={saving}
                    value={resolution}
                    onChange={(event) => {
                      setResolution(event.target.value);
                      resolutionId.current = null;
                    }}
                  />
                </>
              )}
              <p className="hint">
                Corectarea categoriei păstrează predicția originală a modelului.
              </p>
              {saveError && (
                <div className="error" role="alert">
                  {saveError}
                </div>
              )}
              <div className="actions">
                <button
                  type="button"
                  className="button secondary"
                  disabled={saving}
                  onClick={() => setSelected(null)}
                >
                  Închide
                </button>
                <button
                  className="button primary"
                  disabled={
                    saving ||
                    (status === "resolved" &&
                      selected.status !== "resolved" &&
                      !resolution.trim()) ||
                    (category === selected.final_category &&
                      status === selected.status)
                  }
                >
                  {saving ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <Check size={16} />
                  )}
                  Salvează modificările
                </button>
              </div>
            </form>
          )}
        </Dialog>
      )}
    </div>
  );
}
