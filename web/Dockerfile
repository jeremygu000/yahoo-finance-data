FROM node:22-slim AS deps

RUN corepack enable

WORKDIR /app

COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-slim AS builder

RUN corepack enable

WORKDIR /app

COPY --from=deps /app/node_modules node_modules/
COPY web/src/ src/
COPY web/public/ public/
COPY web/next.config.ts web/tsconfig.json web/postcss.config.mjs ./
COPY web/.prettierrc.json web/.oxlintrc.json web/eslint.config.mjs ./

ARG NEXT_PUBLIC_API_URL=http://localhost:8100
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN pnpm build

FROM node:22-slim AS runtime

RUN corepack enable && \
    groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static .next/static/
COPY --from=builder /app/public public/

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

USER app

EXPOSE 3000

CMD ["node", "server.js"]
