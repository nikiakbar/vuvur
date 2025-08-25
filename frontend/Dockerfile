# Stage 1: Build the React application
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:1.25-alpine
# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Expose port 80
EXPOSE 80