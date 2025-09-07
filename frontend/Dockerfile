# Stage 1: Build the React application
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:1.25-alpine
# Copy the built assets
COPY --from=builder /app/dist /usr/share/nginx/html
# Copy the Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy the new dynamic entrypoint script
COPY entrypoint.sh /
# Make the script executable
RUN chmod +x /entrypoint.sh

# Set the new script as the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
# The default Nginx command will be passed as the argument ("$@")
CMD ["nginx", "-g", "daemon off;"]