#!/bin/sh

# Set defaults if not provided
if [ -z "$BACKEND_URL" ]; then
  BACKEND_URL="http://localhost:8000"
elif ! echo "$BACKEND_URL" | grep -q "^http"; then
  BACKEND_URL="https://$BACKEND_URL"
fi

if [ -z "$AGENT_API_KEY" ]; then
  AGENT_API_KEY="my-secret-key"
fi

echo "Replacing placeholders in index.html..."
echo "BACKEND_URL: $BACKEND_URL"
echo "AGENT_API_KEY: [HIDDEN]"

sed -i "s|__BACKEND_URL__|$BACKEND_URL|g" /usr/share/nginx/html/index.html
sed -i "s|__AGENT_API_KEY__|$AGENT_API_KEY|g" /usr/share/nginx/html/index.html

# Execute Nginx daemon
exec nginx -g "daemon off;"
