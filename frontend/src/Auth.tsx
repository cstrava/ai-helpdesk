import { useState } from "react";
import type { FormEvent } from "react";
import { errorText, request } from "./api";
export type Account = {
  id: string;
  email: string;
  role: "user" | "support";
  csrf_token: string;
};
export default function Auth({
  onLogin,
}: {
  onLogin: (account: Account) => void;
}) {
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (register) {
        await request("/auth/register", "POST", { email, password });
        setRegister(false);
        setNotice("Cont creat. Autentifică-te.");
        setPassword("");
      } else
        onLogin(
          await request<Account>("/auth/login", "POST", { email, password }),
        );
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="page auth-page">
      <section className="card draft-form">
        <p className="eyebrow">HELPDESK AI · RO / EN</p>
        <h1>{register ? "Creează un cont" : "Bine ai revenit"}</h1>
        <p className="muted">
          Descrie problema. Verifică ciorna. Confirmă tichetul.
        </p>
        <form onSubmit={submit}>
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="username"
            required
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={busy}
          />
          <label htmlFor="auth-password">Parolă</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={10}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
          />
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {notice && <p role="status">{notice}</p>}
          <div className="actions">
            <button className="button primary" disabled={busy}>
              {busy
                ? "Se procesează…"
                : register
                  ? "Înregistrează-te"
                  : "Autentificare"}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={() => {
                setRegister(!register);
                setError("");
                setNotice("");
              }}
            >
              {register ? "Am deja cont" : "Cont nou"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
