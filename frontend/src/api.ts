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
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Conexiunea cu serverul a fost întreruptă. Verifică serviciile Docker.",
      0,
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    const detail = data?.detail;
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
