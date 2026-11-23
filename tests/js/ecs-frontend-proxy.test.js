const assert = require("node:assert/strict");
const test = require("node:test");

test("primary site loads public pages from the ECS origin", async (t) => {
  const { default: worker } = await import("../../deploy/cloudflare/frontend-proxy.mjs");
  const fetch = t.mock.method(globalThis, "fetch", () => new Response("ECS"));

  const page = new Request("https://njupt.cs-contest.cn/?audit=1", {
    headers: { "If-None-Match": '"existing"', Cookie: "session=example" },
  });
  const response = await worker.fetch(page, {});
  assert.equal(await response.text(), "ECS");

  const [origin, options] = fetch.mock.calls[0].arguments;
  assert.equal(origin.href, "https://api.cs-contest.cn/_ecs_frontend/index.html?audit=1");
  assert.equal(options.headers.get("If-None-Match"), '"existing"');
  assert.equal(options.headers.has("Cookie"), false);

  await worker.fetch(new Request("https://njupt.cs-contest.cn/about", { method: "HEAD" }), {});
  assert.equal(fetch.mock.calls[1].arguments[0].pathname, "/_ecs_frontend/about.html");
  assert.equal(fetch.mock.calls[1].arguments[1].method, "HEAD");
});

test("primary site preserves canonical URLs and only accepts reads", async (t) => {
  const { default: worker } = await import("../../deploy/cloudflare/frontend-proxy.mjs");
  const fetch = t.mock.method(globalThis, "fetch", () => new Response("ECS"));

  const redirect = await worker.fetch(new Request("https://njupt.cs-contest.cn/about.html?v=1"), {});
  assert.equal(redirect.status, 307);
  assert.equal(redirect.headers.get("Location"), "https://njupt.cs-contest.cn/about?v=1");

  const rejected = await worker.fetch(new Request("https://njupt.cs-contest.cn/", { method: "POST" }), {});
  assert.equal(rejected.status, 405);
  assert.equal(rejected.headers.get("Allow"), "GET, HEAD");
  assert.equal(fetch.mock.callCount(), 0);
});

test("other hostnames keep their static assets", async (t) => {
  const { default: worker } = await import("../../deploy/cloudflare/frontend-proxy.mjs");
  const fetch = t.mock.method(globalThis, "fetch", () => new Response("ECS"));
  const assets = { fetch: t.mock.fn(() => new Response("static asset")) };

  const request = new Request("https://www.cs-contest.cn/");
  const response = await worker.fetch(request, { ASSETS: assets });
  assert.equal(await response.text(), "static asset");
  assert.equal(assets.fetch.mock.calls[0].arguments[0], request);
  assert.equal(fetch.mock.callCount(), 0);
});
