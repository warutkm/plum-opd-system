FROM node:18-alpine

WORKDIR /app

COPY package.json ./

# Install dependencies using peer deps override to handle React 19 RC smoothly
RUN npm install --legacy-peer-deps

COPY . .

# Build the Next.js application
RUN npm run build

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["npm", "run", "start"]
