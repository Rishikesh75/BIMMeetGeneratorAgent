# syntax=docker/dockerfile:1
# Multi-stage: builder → api (Node) and web (nginx static + /api proxy)

FROM node:24-bookworm-slim AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY .npmrc ./
COPY scripts ./scripts
COPY artifacts ./artifacts
COPY lib ./lib

RUN pnpm install --frozen-lockfile

RUN pnpm --filter @workspace/api-server run build
RUN pnpm --filter @workspace/gmeet-bim run build

# --- API: workspace + compiled bundle (push schema then serve)
FROM node:24-bookworm-slim AS api
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9 --activate

COPY --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml /app/tsconfig.base.json ./
COPY --from=builder /app/.npmrc ./.npmrc
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/artifacts ./artifacts
COPY --from=builder /app/lib ./lib
COPY --from=builder /app/scripts ./scripts

COPY docker/api-entrypoint.sh /api-entrypoint.sh
RUN chmod +x /api-entrypoint.sh

ENV NODE_ENV=production
EXPOSE 8080

ENTRYPOINT ["/api-entrypoint.sh"]

# --- Web: nginx serves Vite build; browser calls same-origin /api → proxied to api service
FROM nginx:1.27-alpine AS web
COPY --from=builder /app/artifacts/gmeet-bim/dist/public /usr/share/nginx/html
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
