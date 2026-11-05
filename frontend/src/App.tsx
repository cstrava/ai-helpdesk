import { useState } from "react";
import {
  Headphones,
  MessagesSquare,
  Ticket,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import Chat from "./Chat";
import Tickets from "./Tickets";
export default function App() {
  const [page, setPage] = useState<"chat" | "tickets">("chat");
  const [refresh, setRefresh] = useState(0);
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
            onClick={() => setPage("tickets")}
            aria-current={page === "tickets" ? "page" : undefined}
          >
            <Ticket size={19} />
            Tichete
          </button>
        </nav>
        <div className="side-bottom">
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
        </div>
        <div hidden={page !== "chat"}>
          <Chat
            onCreated={() => setRefresh((value) => value + 1)}
            onViewTickets={() => setPage("tickets")}
          />
        </div>
        {page === "tickets" && <Tickets refresh={refresh} />}
        <footer>
          HELPDESK AI{" "}
          <span>Suport mai simplu. De la conversație la tichet.</span>
        </footer>
      </main>
    </div>
  );
}
