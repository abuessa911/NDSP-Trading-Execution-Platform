import http from "node:http";
import { allowedRequest, readClosedCandles, MarketUnavailable } from "./hunter-readonly-market.mjs";
import { readFile, stat } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../out");
const port = Number(process.env.PORT);
const marketPreviewEnabled = process.env.HUNTER_READONLY_MARKET_PREVIEW === "true";
const bindHost = marketPreviewEnabled ? "127.0.0.1" : "0.0.0.0";
const marketCache = new Map();
const marketRateTimes = [];
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("A valid PORT is required.");
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2" };

http.createServer(async (request, response) => {
  response.setHeader("Referrer-Policy", "no-referrer");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Cache-Control", "no-store");
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" }).end();
    return;
  }
  try {
    const requestUrl = new URL(request.url, "http://static.invalid");
    const pathname = decodeURIComponent(requestUrl.pathname);
    if (pathname === "/preview/market/closed-candles") {
      response.setHeader("Content-Type", "application/json; charset=utf-8");
      if (!marketPreviewEnabled || !/^(?:127\.0\.0\.1|localhost):1934[12]$/.test(request.headers.host || "")) {
        response.writeHead(404).end('{"status":"UNAVAILABLE"}');
        return;
      }
      const query = requestUrl.searchParams;
      if (Array.from(query.keys()).some(k => !["market", "symbol", "interval"].includes(k)) ||
          ["market", "symbol", "interval"].some(k => query.getAll(k).length !== 1)) {
        response.writeHead(400).end('{"status":"INVALID_PARAMETERS"}');
        return;
      }
      let selection;
      try {
        selection = allowedRequest({
          market: query.get("market"),
          symbol: query.get("symbol"),
          interval: query.get("interval"),
        });
      } catch {
        response.writeHead(422).end('{"status":"INVALID_SELECTION"}');
        return;
      }
      const now = Date.now();
      const key = [selection.market, selection.symbol, selection.interval].join(":");
      const cached = marketCache.get(key);
      if (cached && now - cached.time <= 25_000) {
        response.writeHead(200).end(JSON.stringify(cached.body));
        return;
      }
      while (marketRateTimes.length && now - marketRateTimes[0] > 60_000) marketRateTimes.shift();
      if (marketRateTimes.length >= 24) {
        response.writeHead(429).end('{"status":"RATE_LIMITED"}');
        return;
      }
      marketRateTimes.push(now);
      try {
        const market = await readClosedCandles(selection);
        marketCache.set(key, { time: now, body: market });
        response.writeHead(200).end(JSON.stringify(market));
      } catch (error) {
        const reason = error instanceof MarketUnavailable ? error.code : "MARKET_PREVIEW_UNAVAILABLE";
        response.writeHead(503).end(JSON.stringify({ status: "UNAVAILABLE", reason_code: reason }));
      }
      return;
    }
    let target = resolve(root, `.${pathname}`);
    if (target !== root && !target.startsWith(root + sep)) throw new Error("Invalid path");
    if ((await stat(target)).isDirectory()) target = resolve(target, "index.html");
    const body = await readFile(target);
    response.writeHead(200, { "Content-Type": mime[extname(target)] ?? "application/octet-stream" });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch {
    response.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
    const body = await readFile(resolve(root, "404.html")).catch(() => Buffer.from("Not found"));
    response.end(request.method === "HEAD" ? undefined : body);
  }
}).listen(port, bindHost);