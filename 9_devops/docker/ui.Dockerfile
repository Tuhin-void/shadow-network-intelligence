# Shadow Network Intelligence — Dashboard UI
#
# Two-stage build: Node build → Nginx static serve.
# The orchestrator URL is baked at build time via VITE_API_BASE_URL.
# Override with `--build-arg VITE_API_BASE_URL=http://your-api`.
FROM node:22-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_PREFIX=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_PREFIX=${VITE_API_PREFIX}

COPY 8_dashboard_ui/package.json 8_dashboard_ui/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY 8_dashboard_ui/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback — every non-asset request returns index.html so the
# React Router routes resolve client-side.
RUN printf '%s\n' \
    'server {' \
    '  listen 80;' \
    '  root /usr/share/nginx/html;' \
    '  index index.html;' \
    '  location / { try_files $uri $uri/ /index.html; }' \
    '}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/ > /dev/null || exit 1
