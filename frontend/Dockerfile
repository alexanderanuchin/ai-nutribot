FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
# Предустановим кэш слоём (ускорит повторные сборки)
RUN npm ci || npm i
COPY . .
EXPOSE 5173
# В рантайме node_modules — том, поэтому дублируем установку перед запуском dev-сервера
CMD ["sh","-lc","npm ci || npm i; npm run dev -- --host 0.0.0.0"]
