import { test, expect } from "@playwright/test";

test("login → conversation → editable draft → confirmation → ticket → restored history", async ({
  page,
}, testInfo) => {
  const title = `Pontaj blocat — ${testInfo.project.name}`;
  const email = `browser-${testInfo.project.name}@example.test`;
  await page.goto("/");
  await page.getByRole("button", { name: "Cont nou", exact: true }).click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-test-password");
  await page
    .getByRole("button", { name: "Înregistrează-te", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Cont creat");
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-test-password");
  await page
    .getByRole("button", { name: "Autentificare", exact: true })
    .click();
  await page.getByLabel("Mesajul tău").fill("Nu mă pot conecta la pontaj.");
  await page.getByRole("button", { name: "Trimite", exact: true }).click();
  await expect(page.getByRole("log")).toContainText(
    "Ce mesaj de eroare apare?",
  );
  await page.getByRole("button", { name: "Pregătește tichetul" }).click();
  await page.getByLabel("Titlu", { exact: true }).fill(title);
  await expect(page.getByText("CIORNĂ · NESALVATĂ")).toBeVisible();
  const before = await page.request.get("/api/tickets");
  expect(await before.json()).toEqual([]);
  await page.getByRole("button", { name: "Confirmă și creează" }).click();
  await expect(page.getByText("TICHET CREAT", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("TICHET CREAT", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Conversația este închisă", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Vezi tichetele", exact: true })
    .click();

  await expect(
    page.getByRole("heading", { name: "Istoricul modificărilor" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Categoria finală", { exact: true }),
  ).toHaveCount(0);
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press(i % 2 ? "Shift+Tab" : "Tab");
    expect(
      await page.evaluate(() =>
        document
          .querySelector('[role="dialog"]')
          ?.contains(document.activeElement),
      ),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("tickets.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Deconectare", exact: true })
    .filter({ visible: true })
    .click();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await page
    .getByLabel("Email", { exact: true })
    .fill("browser-support@example.test");
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-support-password");
  await page
    .getByRole("button", { name: "Autentificare", exact: true })
    .click();
  await page.getByRole("button", { name: "Tichete", exact: true }).click();
  await page.getByLabel("Caută în toate tichetele").fill(title);
  await page.getByRole("button", { name: title, exact: true }).click();
  await page
    .getByLabel("Categoria finală", { exact: true })
    .selectOption("Hardware");
  await page
    .getByRole("button", { name: "Preia tichetul", exact: true })
    .click();
  await page
    .getByLabel("Răspuns public", { exact: true })
    .fill("Please retry signing in.");
  await page
    .getByRole("button", { name: "Trimite răspunsul", exact: true })
    .click();
  await expect(
    page.getByText("Please retry signing in.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("checkbox").check();
  await page
    .getByLabel("Notă internă", { exact: true })
    .fill("Synthetic private diagnosis");
  await page.getByRole("button", { name: "Adaugă nota", exact: true }).click();
  await expect(
    page.getByText("Synthetic private diagnosis", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Status", { exact: true }).selectOption("resolved");
  await page
    .getByLabel("Mesaj de rezolvare", { exact: true })
    .fill("Your account has been unlocked.");
  await page.getByRole("button", { name: "Salvează modificările" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: title, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: title, exact: true }).click();
  await expect(page.locator(".audit-list")).toContainText("Access → Hardware");
  await expect(page.locator(".audit-list")).toContainText("open → resolved");
  await expect(page.locator(".audit-list")).toContainText(
    "browser-support@example.test",
  );
  await page.screenshot({
    path: testInfo.outputPath("support-audit.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Închide detaliile", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Deconectare", exact: true })
    .filter({ visible: true })
    .click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-test-password");
  await page
    .getByRole("button", { name: "Autentificare", exact: true })
    .click();
  await page.getByRole("button", { name: "Tichete", exact: true }).click();
  await page.getByRole("button", { name: title, exact: true }).click();
  await expect(
    page.getByText("Your account has been unlocked.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic private diagnosis", { exact: true })).toHaveCount(0);
  await page.getByLabel("Răspuns public", { exact: true }).fill("I tried again and it is still blocked.");
  await page.getByRole("button", { name: "Trimite răspunsul", exact: true }).click();
  await expect(page.getByText("I tried again and it is still blocked.", { exact: true })).toBeVisible();
  await page
    .getByLabel("Motivul redeschiderii")
    .fill("The account is locked again.");
  await page
    .getByRole("button", { name: "Redeschide tichetul", exact: true })
    .click();
  await expect(page.locator(".audit-list")).toContainText("resolved → open");
  await expect(
    page.getByText("The account is locked again.", { exact: true }),
  ).toBeVisible();
});

test("restores unsaved work and recovers a committed ticket after a proxy error", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cont nou", exact: true }).click();
  await page
    .getByLabel("Email", { exact: true })
    .fill(`recovery-${testInfo.project.name}@example.test`);
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-test-password");
  await page
    .getByRole("button", { name: "Înregistrează-te", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Cont creat");
  await page
    .getByLabel("Parolă", { exact: true })
    .fill("browser-test-password");
  await page
    .getByRole("button", { name: "Autentificare", exact: true })
    .click();
  await page
    .getByLabel("Mesajul tău")
    .fill("Nu funcționează portalul de pontaj.");
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.values(sessionStorage).some((value) =>
          value.includes("Nu funcționează portalul"),
        ),
      ),
    )
    .toBe(true);
  await page.reload();
  await expect(page.getByLabel("Mesajul tău")).toHaveValue(
    "Nu funcționează portalul de pontaj.",
  );
  await page.getByRole("button", { name: "Trimite", exact: true }).click();
  await expect(page.getByRole("log")).toContainText(
    "Ce mesaj de eroare apare?",
  );
  await page.getByRole("button", { name: "Pregătește tichetul" }).click();
  await page.getByLabel("Titlu", { exact: true }).fill("Edited recovery draft");
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.values(sessionStorage).some((value) =>
          value.includes("Edited recovery draft"),
        ),
      ),
    )
    .toBe(true);
  await page.reload();
  await expect(page.getByLabel("Titlu", { exact: true })).toHaveValue(
    "Edited recovery draft",
  );
  let confirmations = 0;
  await page.route("**/api/conversations/*/tickets", async (route) => {
    confirmations++;
    const committed = await route.fetch();
    expect(committed.status()).toBe(201);
    await route.fulfill({
      status: 502,
      contentType: "text/html",
      body: "Upstream response lost",
    });
  });
  await page.getByRole("button", { name: "Confirmă și creează" }).click();
  await expect(page.getByText("TICHET CREAT", { exact: true })).toBeVisible();
  expect(confirmations).toBe(1);
  const tickets = await (await page.request.get("/api/tickets")).json();
  expect(tickets).toHaveLength(1);
  expect(tickets[0].title).toBe("Edited recovery draft");
  await page.reload();
  await expect(page.getByText("TICHET CREAT", { exact: true })).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          Object.keys(sessionStorage).filter((key) =>
            key.startsWith("helpdesk-unsaved:"),
          ).length,
      ),
    )
    .toBe(0);
});
