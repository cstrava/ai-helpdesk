import type { Draft } from "./api";

const prefix = "helpdesk-unsaved:";
const key = (accountId: string, conversationId: string | null) =>
  `${prefix}${accountId}:${conversationId ?? "new"}`;

export type Unsaved = { text: string; draft: Draft | null; uncertain: boolean };

export function readUnsaved(
  accountId: string,
  conversationId: string | null,
): Unsaved {
  const empty = { text: "", draft: null, uncertain: false };
  try {
    const value = JSON.parse(
      sessionStorage.getItem(key(accountId, conversationId)) ?? "null",
    );
    if (!value || typeof value.text !== "string" || value.text.length > 1000)
      return empty;
    const d = value.draft;
    const draft =
      d &&
      d.conversation_id === conversationId &&
      typeof d.title === "string" &&
      d.title.length <= 160 &&
      typeof d.description === "string" &&
      d.description.length <= 2000 &&
      Number.isSafeInteger(d.last_message_id) &&
      d.last_message_id > 0 &&
      typeof d.predicted_category === "string" &&
      typeof d.model_version === "string"
        ? (d as Draft)
        : null;
    return { text: value.text, draft, uncertain: value.uncertain === true };
  } catch {
    return empty;
  }
}

export function saveUnsaved(
  accountId: string,
  conversationId: string | null,
  value: Unsaved,
) {
  try {
    if (!value.text && !value.draft && !value.uncertain)
      sessionStorage.removeItem(key(accountId, conversationId));
    else
      sessionStorage.setItem(
        key(accountId, conversationId),
        JSON.stringify(value),
      );
  } catch {
    /* Storage may be disabled; the in-memory editor remains usable. */
  }
}

export function clearUnsaved(accountId?: string) {
  try {
    const start = accountId ? `${prefix}${accountId}:` : prefix;
    for (const name of Object.keys(sessionStorage))
      if (name.startsWith(start)) sessionStorage.removeItem(name);
  } catch {
    /* Storage may be disabled. */
  }
}
