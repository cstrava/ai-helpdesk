# Demo walkthrough

Use synthetic examples and the real local models for this walkthrough. Follow [Operations](OPERATIONS.md) to start the application and create accounts: two ordinary users and one support account. Public registration creates ordinary users; support accounts require the CLI. Use separate browser profiles for the ticket owner, the second user and support.

The interface remains in Romanian. The English instructions below describe its existing controls; quoted Romanian messages are intentional test inputs.

## Complete workflow: about 5–10 minutes

1. Sign in as the first user. Type a message without sending it, then refresh the same tab. The unsent message should return. Send it and inspect Qwen's reply.
2. Prepare a ticket draft. Edit its title and description, then refresh. The edits should return without creating a ticket. Check the text against what the user actually said; correct any invented or generalized details.
3. Confirm once and record the ticket ID, predicted category and `open` status. Refresh. The same ticket should remain linked to the conversation, and the converted conversation should reject further messages.
4. As support, find the ticket by ID and claim it. Add a public reply and an internal note. Change the category if appropriate, set `in_progress`, then resolve it with a resolution message. Inspect the audit history.
5. As the owner, check the public reply, status and resolution message. The internal note and support editing controls should be absent. Reopen the ticket with a reason. The second user should not be able to see the first user's conversation or ticket.
6. As support, combine the assigned-to-me and priority filters. Change priority and check its audit event. Open the 30-day dashboard and read its metric definitions. Check the owner's notification after the public reply; the internal note should not create one. Notifications are polled, so allow up to 30 seconds for the UI to refresh.
7. Explicitly review the category of a synthetic ticket and export reviewed examples. Change that ticket's category and check that its review becomes invalid. Keep exported data local; use only synthetic data in shared demo material.
8. Repeat a short conversation in English using the example below. Inspect the draft manually before confirming it.
9. Sign out, sign in again and check that unsaved content has been cleared. Saved database history should still be available.

## Romanian conversation and correction

Use these inputs in a new conversation, responding to the model's actual clarification questions as needed:

1. “Nu mă pot conecta la aplicația de pontaj de azi dimineață.”
2. “Apare «cont blocat». Colegii se pot conecta. Nu pot înregistra orele.”
3. “Corectez: problema a început ieri, nu azi.”

Prepare the draft and check that it retains the corrected start time and includes no unsupported details. The model's wording is not deterministic; this is a manual fidelity check, not an expected exact response.

## English conversation and language switching

Start a separate conversation:

1. “My USB headset is not detected on my laptop.”
2. “It stopped working after reconnecting it this morning. I cannot join calls. Another USB port did not help.”
3. “Te rog să continuăm în română. Corectez: este un microfon USB, nu căști.”

Prepare the draft. Check whether it follows the latest language request and describes a USB microphone rather than a headset. Edit it if needed, then confirm. Successful completion of this example does not establish general bilingual model accuracy; see [ML evaluation and limitations](ML_EVALUATION.md).

## Error handling and interface checks

In an isolated demo environment, temporarily stop Ollama and send a message. Check that the editor retains the text and shows an error. Restart Ollama and retry. Do not stop or modify a shared database to simulate failures. Timeout and invalid-model-response handling also have automated tests with simulated inference.

Check desktop and mobile layouts, empty lists, loading and error states, visible keyboard focus, Tab/Shift+Tab within dialogs, Escape to close dialogs, and logout. Mobile browser automation uses Pixel 7 emulation in Chromium; it is separate from testing a physical phone.

## Reproduce confirmation recovery

The Playwright recovery case sends a real confirmation to the isolated test backend, lets the backend create the ticket, then returns HTTP 502 to the browser. It checks that the UI retrieves the committed ticket through GET, makes only one confirmation POST, and restores the same result after refresh.

First prepare the Python environment, frontend dependencies, Chromium and isolated `ai_helpdesk_test` database as described in [Operations](OPERATIONS.md). With the test PostgreSQL instance listening on port `55434`, run from the repository root:

```bash
cd frontend
E2E_PYTHON=../.venv/bin/python POSTGRES_PORT=55434 npm run test:e2e
```

The browser server uses the test password `test-only`, a fixed test database name and temporary schemas. It runs on port `8001`; Vite runs on `5174`. This suite uses real authentication and SQL with simulated Qwen/XLM-R inference, so it does not replace the manual real-model checks above.
