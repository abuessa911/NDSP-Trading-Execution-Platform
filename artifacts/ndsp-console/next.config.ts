import type { NextConfig } from "next";

const rawBase = process.env.BASE_PATH ?? "/";
if (!rawBase.startsWith("/") || rawBase.includes("..") || rawBase.includes("?")) {
  throw new Error("BASE_PATH must be an absolute application path.");
}

const config: NextConfig = {
  // API/session ownership stays in FastAPI. Static Next output is portable and
  // keeps browser requests on the same origin without a second auth server.
  // Dev must retain normal unknown-route handling. Next's export-mode dev
  // dispatcher throws before notFound() for unlisted dynamic parameters.
  output: process.env.NODE_ENV === "production" ? "export" : undefined,
  // In export mode Next treats a non-default distDir as the export directory,
  // not a separate intermediate directory. Keep production's default (.next)
  // so its export stays in out/, and isolate the live preview instead.
  distDir: process.env.NODE_ENV === "production" ? ".next" : ".next-dev",
  agentRules: false,
  trailingSlash: true,
  basePath: rawBase === "/" ? "" : rawBase.replace(/\/$/, ""),
  poweredByHeader: false,
  allowedDevOrigins: ["**.replit.dev", "**.replit.app", "localhost", "127.0.0.1"],
  transpilePackages: ["@workspace/api-client-react"],
  experimental: { cpus: 2 },
};

export default config;