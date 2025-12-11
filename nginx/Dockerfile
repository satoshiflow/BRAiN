# Nginx Reverse Proxy Server
FROM nginx:1.27-alpine

# Copy custom nginx configuration (Docker version)
COPY nginx.docker.conf /etc/nginx/nginx.conf

# Expose ports
EXPOSE 80 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
