# Portable optional frontend packaging. No Replit runtime, server auth or secrets.
FROM node:22-alpine AS frontend
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 BASE_PATH=/
RUN corepack enable && corepack prepare pnpm@10.26.1 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc tsconfig.base.json ./
COPY artifacts/ndsp-console/package.json ./artifacts/ndsp-console/package.json
COPY lib/api-client-react/package.json ./lib/api-client-react/package.json
RUN pnpm install --frozen-lockfile
COPY lib/api-client-react ./lib/api-client-react
COPY artifacts/ndsp-console ./artifacts/ndsp-console
RUN pnpm --filter @workspace/ndsp-console run build

FROM nginx:1.27-alpine
COPY infra/console/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend /app/artifacts/ndsp-console/out /usr/share/nginx/html
EXPOSE 8080