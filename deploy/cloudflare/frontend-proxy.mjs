const primaryHostname = "njupt.cs-contest.cn";
const origin = "https://api.cs-contest.cn";
const originPrefix = "/_ecs_frontend";

const redirects = new Map([
  ["/index", "/"],
  ["/index/", "/"],
  ["/index.html", "/"],
  ["/about/", "/about"],
  ["/about.html", "/about"],
]);

const pages = new Map([
  ["/", "/index.html"],
  ["/about", "/about.html"],
]);

const forwardedHeaders = [
  "Accept",
  "If-Modified-Since",
  "If-None-Match",
  "If-Range",
  "Range",
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.hostname !== primaryHostname) {
      return env.ASSETS.fetch(request);
    }

    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }

    const redirectPath = redirects.get(url.pathname);
    if (redirectPath) {
      url.pathname = redirectPath;
      return Response.redirect(url.toString(), 307);
    }

    const upstream = new URL(origin);
    const path = /%(?:2f|5c)/i.test(url.pathname) ? "/404" : url.pathname;
    upstream.pathname = originPrefix + (pages.get(path) ?? path);
    upstream.search = url.search;

    const headers = new Headers();
    for (const name of forwardedHeaders) {
      const value = request.headers.get(name);
      if (value !== null) headers.set(name, value);
    }

    return fetch(upstream, {
      method: request.method,
      headers,
      redirect: "manual",
    });
  },
};
