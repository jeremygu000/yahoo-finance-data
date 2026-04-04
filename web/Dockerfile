FROM node:22-slim AS base

RUN corepack enable

WORKDIR /app

COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY web/src/ src/
COPY web/public/ public/
COPY web/next.config.ts web/tsconfig.json web/postcss.config.mjs ./
COPY web/.prettierrc.json web/.oxlintrc.json web/eslint.config.mjs ./

ENV NEXT_PUBLIC_API_URL=http://localhost:8100
RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]
