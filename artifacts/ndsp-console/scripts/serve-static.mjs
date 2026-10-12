import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../out");
const port = Number(process.env.PORT);
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
    const pathname = decodeURIComponent(new URL(request.url, "http://static.invalid").pathname);
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
}).listen(port, "0.0.0.0");