import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      access_token: "token",
      token_type: "bearer",
      user: { id: "admin", username: "Admin", email: "admin@robolinks.vn", role: "admin", created_at: new Date().toISOString() }
    })
  }));
});

test("login to chat and receive citation", async ({ page }) => {
  await page.route("**/api/chat/stream", async (route) => route.fulfill({
    contentType: "text/event-stream",
    body: "data: Motor Siemens\n\ndata: {\"citations\":[{\"type\":\"document\",\"file\":\"BOM.xlsx\"}]}\n\ndata: [DONE]\n\n"
  }));
  await page.goto("/sign-in");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("textbox", { name: "Message" }).fill("Heineken dùng motor gì?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Motor Siemens")).toBeVisible();
  await expect(page.getByText("BOM.xlsx")).toBeVisible();
});

test("wiki browse opens entity relations", async ({ page }) => {
  await page.route("**/api/wiki/entities", async (route) => route.fulfill({ contentType: "application/json", body: "[]" }));
  await page.route("**/api/wiki/search?q=Alpha", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([{ name: "Alpha", type: "PROJECT", description: "Test project" }])
  }));
  await page.route("**/api/wiki/entity/Alpha", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      name: "Alpha",
      type: "PROJECT",
      description: "Test project",
      relations: [{ src: "Alpha", rel_type: "USES", tgt: "PLC", description: "Control" }],
      sources: [],
      graph_nodes: [{ id: "Alpha", label: "Alpha", type: "PROJECT" }, { id: "PLC", label: "PLC", type: "EQUIPMENT" }],
      graph_edges: [{ source: "Alpha", target: "PLC", label: "USES" }]
    })
  }));
  await page.goto("/sign-in");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Wiki" }).click();
  await page.getByPlaceholder("Search entity name").fill("Alpha");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("link", { name: /Alpha/ }).click();
  await expect(page.getByText("USES").first()).toBeVisible();
});

test("admin approve flow updates queue", async ({ page }) => {
  await page.route("**/api/admin/nas/queue", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "file-1", nas_path: "/projects/A.pdf", folder_type: "manual", status: "pending_review", created_at: new Date().toISOString() }]) });
    } else {
      await route.fallback();
    }
  });
  await page.route("**/api/admin/nas/queue/file-1/action", async (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ id: "file-1", nas_path: "/projects/A.pdf", folder_type: "manual", status: "indexed", created_at: new Date().toISOString() }) }));
  await page.goto("/sign-in");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Admin" }).click();
  await expect(page.getByText("/projects/A.pdf")).toBeVisible();
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("/projects/A.pdf")).toHaveCount(0);
});

test("admin scan now updates folder summary", async ({ page }) => {
  await page.route("**/api/admin/nas/folders", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          { id: "folder-1", path: "/local-nas/projects/Demo/docs", folder_type: "manual", is_active: true, last_scanned: null, created_at: new Date().toISOString() }
        ])
      });
    } else {
      await route.fallback();
    }
  });
  await page.route("**/api/admin/nas/folders/folder-1/scan", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      folder: { id: "folder-1", path: "/local-nas/projects/Demo/docs", folder_type: "manual", is_active: true, last_scanned: new Date().toISOString(), created_at: new Date().toISOString() },
      scanned_count: 1,
      new_count: 1,
      updated_count: 0,
      deleted_count: 0,
      queued_count: 1,
      ingested_count: 0,
      error_count: 0,
      last_scanned: new Date().toISOString(),
      errors: []
    })
  }));
  await page.goto("/sign-in");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("link", { name: "Folders" }).click();
  await page.getByRole("button", { name: "Scan now" }).click();
  await expect(page.getByText("Scanned 1 file(s): 1 new, 0 updated, 0 deleted, 1 queued/reviewed, 0 ingested, 0 error(s).")).toBeVisible();
});
