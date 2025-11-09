FROM node:22-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm i

FROM node:22-alpine AS runtime

ENV NODE_ENV=development
WORKDIR /app

RUN addgroup -S app && adduser -S app -G app
RUN apk add --no-cache curl

COPY --chown=app:app --from=deps /app/node_modules ./node_modules
COPY --chown=app:app . .

USER app

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=10s CMD curl -f http://127.0.0.1:5173/ || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
