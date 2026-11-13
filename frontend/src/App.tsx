import { useEffect, useState } from "react";
import {
  Headphones,
  MessagesSquare,
  Ticket,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import Auth from "./Auth";
import type { Account } from "./Auth";
import { request, setCsrfToken, errorText } from "./api";
import Chat from "./Chat";
import Tickets from "./Tickets";
export default function App() {
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(true);
  const [authError, setAuthError] = useState("");
  useEffect(() => {
    request<Account>("/auth/me")
      .then((user) => {
        setCsrfToken(user.csrf_token);
        setAccount(user);
      })
      .catch((cause) => {
        if (cause.status !== 401) setAuthError(errorText(cause));
      })
      .finally(() => setChecking(false));
    const expire = () => {
      setAccount(null);
      setTicketId(null);
      setPage("chat");
      setRefresh(0);
      setCsrfToken("");
    };
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  async function logout() {
    try {
      await request("/auth/logout", "POST", {});
      setAccount(null);
      setTicketId(null);
      setPage("chat");
      setRefresh(0);
      setCsrfToken("");
    } catch (cause) {
      if (cause instanceof Error && "status" in cause && cause.status === 401) {
        setAccount(null);
        setTicketId(null);
        setPage("chat");
        setRefresh(0);
        setCsrfToken("");
      } else setAuthError(errorText(cause));
    }
  }
  const [page, setPage] = useState<"chat" | "tickets">("chat");
  const [refresh, setRefresh] = useState(0);
  const [ticketId, setTicketId] = useState<string | null>(null);
  if (checking)
    return (
      <main className="page" role="status">
        Se verifică sesiunea…
      </main>
    );
  if (!account)
    return (
      <>
        {authError && (
          <p className="error" role="alert">
            {authError}
          </p>
        )}
        <Auth
          onLogin={(user) => {
            setCsrfToken(user.csrf_token);
            setAccount(user);
            setAuthError("");
          }}
        />
      </>
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(event) => {
            event.preventDefault();
            setPage("chat");
          }}
        >
          <span className="brand-mark">
            <Headphones size={23} />
          </span>
          <span>
            helpdesk<span className="brand-ai">ai</span>
          </span>
        </a>
        <p className="nav-caption">SPAȚIUL DE LUCRU</p>
        <nav aria-label="Navigare principală">
          <button
            className={page === "chat" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("chat")}
            aria-current={page === "chat" ? "page" : undefined}
          >
            <MessagesSquare size={19} />
            Asistent IT
            <ArrowUpRight size={16} />
          </button>
          <button
            className={page === "tickets" ? "nav-item active" : "nav-item"}
            onClick={() => {
              setTicketId(null);
              setPage("tickets");
            }}
            aria-current={page === "tickets" ? "page" : undefined}
          >
            <Ticket size={19} />
            Tichete
          </button>
        </nav>
        <div className="side-bottom">
          <p>
            {account.email} · {account.role}
          </p>
          <button className="button secondary" onClick={logout}>
            Deconectare
          </button>
          {authError && <p role="alert">{authError}</p>}
          <div className="side-card">
            <ShieldCheck size={23} />
            <strong>Tu ai ultimul cuvânt.</strong>
            <p>
              Verifici informațiile și confirmi înainte de crearea tichetului.
            </p>
          </div>
          <div className="workspace">
            <span>IT</span>
            <div>
              <strong>Workspace local</strong>
              <small>AI Helpdesk · Demo</small>
            </div>
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <span>
            Workspace <span className="slash">/</span>{" "}
            {page === "chat" ? "Asistent IT" : "Tichete"}
          </span>
          <span className="local-label">Procesare locală</span>
          <button className="button secondary mobile-logout" onClick={logout}>
            Deconectare
          </button>
        </div>
        <div hidden={page !== "chat"}>
          <Chat
            key={account.id}
            accountId={account.id}
            onCreated={() => setRefresh((value) => value + 1)}
            onViewTickets={(id) => {
              setTicketId(id ?? null);
              setPage("tickets");
            }}
          />
        </div>
        {page === "tickets" && (
          <Tickets
            refresh={refresh}
            support={account.role === "support"}
            initialTicketId={ticketId}
          />
        )}
        <footer>
          HELPDESK AI{" "}
          <span>Suport mai simplu. De la conversație la tichet.</span>
        </footer>
      </main>
    </div>
  );
}
