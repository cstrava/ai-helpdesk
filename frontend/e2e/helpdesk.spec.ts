import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

async function expectReadableContrast(page: import("@playwright/test").Page) {
  const failures = await page.evaluate(() => {
    const luminance = (color: number[]) => {
      const channels = color.map((channel) => {
        const value = channel / 255;
        return value <= 0.04045
          ? value / 12.92
          : ((value + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };
    const rgb = (value: string) =>
      value.match(/[\d.]+/g)?.slice(0, 3).map(Number) ?? [0, 0, 0];
    const contrast = (foreground: string, background: string) => {
      const first = luminance(rgb(foreground));
      const second = luminance(rgb(background));
      return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
    };
    const failures: Array<{ selector: string; text: string; ratio: number }> = [];
    for (const element of document.querySelectorAll<HTMLElement>("body *")) {
      const hasText = Array.from(element.childNodes).some(
        (node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim(),
      );
      if (!hasText || element.getClientRects().length === 0) continue;
      let opacity = 1;
      let background = "rgb(246, 248, 247)";
      for (let current: HTMLElement | null = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        opacity *= Number(style.opacity);
        if (style.backgroundColor !== "rgba(0, 0, 0, 0)") {
          background = style.backgroundColor;
          break;
        }
      }
      if (opacity < 0.98) continue;
      const style = getComputedStyle(element);
      const size = Number.parseFloat(style.fontSize);
      const bold = Number.parseInt(style.fontWeight, 10) >= 700;
      const minimum = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5;
      const ratio = contrast(style.color, background);
      if (ratio < minimum) {
        failures.push({
          selector: `${element.tagName.toLowerCase()}.${element.className.toString().replaceAll(" ", ".")}`,
          text: element.textContent?.trim().slice(0, 60) ?? "",
          ratio: Math.round(ratio * 100) / 100,
        });
      }
    }
    return failures;
  });
  expect(failures).toEqual([]);
}

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
  await expectReadableContrast(page);
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
    .getByLabel("Etichetă verificată", { exact: true })
    .selectOption("Hardware");
  await page
    .getByLabel("Motiv (opțional)", { exact: true })
    .fill("Confirmed during the synthetic support walkthrough.");
  await page
    .getByRole("button", { name: "Marchează ca revizuit", exact: true })
    .click();
  await expect(page.getByText(/Exemplu revizuit la/)).toBeVisible();
  await page
    .getByRole("button", { name: "Închide detaliile", exact: true })
    .click();
  const approvedExport = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Exportă exemple revizuite", exact: true })
    .click();
  const approvedFile = await approvedExport;
  const approvedPath = testInfo.outputPath("approved-examples.csv");
  await approvedFile.saveAs(approvedPath);
  const approvedCsv = await readFile(approvedPath, "utf8");
  expect(approvedCsv).toContain(title);
  expect(approvedCsv).toContain("Hardware");
  expect(approvedCsv).not.toContain("Synthetic private diagnosis");

  await page.getByRole("button", { name: title, exact: true }).click();
  await page
    .getByLabel("Categoria finală", { exact: true })
    .selectOption("Purchase");
  await page.getByRole("button", { name: "Salvează modificările" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: title, exact: true }).click();
  await expect(page.getByText(/Exemplu revizuit la/)).toHaveCount(0);
  await page
    .getByRole("button", { name: "Închide detaliile", exact: true })
    .click();
  const invalidatedExport = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Exportă exemple revizuite", exact: true })
    .click();
  const invalidatedFile = await invalidatedExport;
  const invalidatedPath = testInfo.outputPath("invalidated-examples.csv");
  await invalidatedFile.saveAs(invalidatedPath);
  expect((await readFile(invalidatedPath, "utf8")).trim().split("\n")).toHaveLength(1);
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
