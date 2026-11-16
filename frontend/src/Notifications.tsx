import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { errorText, request } from "./api";

type Notice = {
  id: string;
  ticket_id: string;
  kind: "reply" | "assignment" | "status";
  created_at: string;
  read_at: string | null;
  title: string | null;
};

export default function Notifications({
  onOpen,
}: {
  onOpen: (ticketId: string) => void;
}) {
  const [count, setCount] = useState(0);
  const [rows, setRows] = useState<Notice[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      const [unread, notifications] = await Promise.all([
        request<{ count: number }>("/notifications/unread-count"),
        request<Notice[]>("/notifications?limit=20"),
      ]);
      setCount(unread.count);
      setRows(notifications);
      setHasMore(notifications.length === 20);
      setError("");
    } catch (cause) {
      setError(errorText(cause));
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const labels = {
    reply: "Răspuns nou",
    assignment: "Atribuire actualizată",
    status: "Status actualizat",
  };

  return (
    <div className="notification-area">
      <button
        className="button secondary notification-toggle"
        aria-label={`Notificări necitite: ${count}`}
        aria-expanded={open}
        onClick={() => {
          setOpen(!open);
          void refresh();
        }}
      >
        <Bell size={17} />
        {count > 0 && <span className="notification-count">{count}</span>}
      </button>
      {open && (
        <section className="notification-popover" aria-label="Notificări">
          <h2>Notificări</h2>
          {error && <p role="alert">{error}</p>}
          {!rows.length && !error && <p className="muted">Nu ai notificări.</p>}
          <ul>
            {rows.map((notice) => (
              <li key={notice.id} className={notice.read_at ? "" : "unread"}>
                <button
                  onClick={async () => {
                    try {
                      await request(`/notifications/${notice.id}/read`, "PATCH", {});
                      setOpen(false);
                      onOpen(notice.ticket_id);
                      void refresh();
                    } catch (cause) {
                      setError(errorText(cause));
                    }
                  }}
                >
                  <strong>{labels[notice.kind]}</strong>
                  <span>{notice.title || "Tichet"}</span>
                  <small>{new Date(notice.created_at).toLocaleString("ro-RO")}</small>
                </button>
              </li>
            ))}
          </ul>
          {hasMore && (
            <button
              className="button secondary"
              onClick={async () => {
                try {
                  const more = await request<Notice[]>(
                    `/notifications?limit=20&offset=${rows.length}`,
                  );
                  setRows((current) => [...current, ...more]);
                  setHasMore(more.length === 20);
                } catch (cause) {
                  setError(errorText(cause));
                }
              }}
            >
              Notificări mai vechi
            </button>
          )}
        </section>
      )}
    </div>
  );
}
