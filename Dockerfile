FROM n8nio/n8n:latest

# Railway uses PORT env variable
ENV N8N_PORT=${PORT}
ENV N8N_PROTOCOL=http
ENV N8N_HOST=0.0.0.0

# Basic auth
ENV N8N_BASIC_AUTH_ACTIVE=true
ENV N8N_BASIC_AUTH_USER=admin
ENV N8N_BASIC_AUTH_PASSWORD=yourpassword

# SQLite storage inside container
ENV N8N_DATABASE_TYPE=sqlite
ENV N8N_DATABASE_SQLITE_PATH=/data/database.sqlite

# Folder for data store
ENV N8N_USER_FOLDER=/data

# Create data folder
RUN mkdir /data
