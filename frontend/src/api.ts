let csrfToken = "";
export const setCsrfToken = (value: string) => {
  csrfToken = value;
};
export const categories = [
  "Access",
  "Administrative rights",
  "HR Support",
  "Hardware",
  "Internal Project",
  "Miscellaneous",
  "Purchase",
  "Storage",
] as const;
export type Status = "open" | "in_progress" | "resolved";
export const statusLabels: Record<Status, string> = {
  open: "Deschis",
  in_progress: "În lucru",
  resolved: "Rezolvat",
};
export type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
};
export type Draft = {
  conversation_id: string;
  last_message_id: number;
  title: string;
  description: string;
  predicted_category: string;
  model_version: string;
};
export type Ticket = {
  id: string;
  title: string | null;
  text: string;
  predicted_category: string;
  final_category: string;
  model_version: string;
  status: Status;
  created_at: string;
  conversation_id: string | null;
  assignee_id: string | null;
  assignee_email: string | null;
  priority: "low" | "normal" | "high" | "urgent";
  version: number;
  updated_at: string | null;
  first_resolved_at: string | null;
  impact?: "individual" | "team" | "organization" | null;
};
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 150_000);
  let response: Response;
  let data: unknown;
  try {
    response = await fetch(`/api${path}`, {
      method,
      signal: controller.signal,
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    data = await response.json().catch(() => null);
  } catch {
    throw new ApiError(
      "Conexiunea cu serverul a fost întreruptă. Verifică serviciile Docker.",
      0,
    );
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    const detail = (data as { detail?: unknown } | null)?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item: { msg?: string }) => item.msg ?? "Date invalide")
              .join("; ")
          : `Serverul a răspuns cu eroarea ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  if (data === null)
    throw new ApiError("Serverul a trimis un răspuns nevalid.", 502);
  return data as T;
}
export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : "A apărut o eroare neașteptată.";

export function isTicket(value: unknown): value is Ticket {
  if (!value || typeof value !== "object") return false;
  const t = value as Ticket;
  return (
    typeof t.id === "string" &&
    typeof t.text === "string" &&
    (t.title === null || typeof t.title === "string") &&
    typeof t.conversation_id === "string" &&
    typeof t.created_at === "string" &&
    typeof t.predicted_category === "string" &&
    typeof t.final_category === "string" &&
    typeof t.model_version === "string" &&
    ["open", "in_progress", "resolved"].includes(t.status)
  );
}
