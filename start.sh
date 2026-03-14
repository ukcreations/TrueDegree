#!/bin/sh

echo "Starting TrueDegree..."

# Create a simple index.html for health check
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>TrueDegree</title>
</head>
<body>
    <h1>TrueDegree is running! 🎓</h1>
    <p>Frontend: Working</p>
    <p>Backend: Starting...</p>
</body>
</html>
EOF

# Test nginx configuration
nginx -t

# Start nginx
echo "Starting nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Wait for nginx to start
echo "Waiting for nginx to start..."
sleep 5

# Test nginx is running
curl -f http://localhost/ || echo "Nginx not responding"

# Start FastAPI
echo "Starting FastAPI..."
cd /app
python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000)" &
FASTAPI_PID=$!

# Wait for FastAPI to start
echo "Waiting for FastAPI to start..."
sleep 10

# Test FastAPI is running
curl -f http://localhost:8000/docs || echo "FastAPI not responding"

echo "Services started. PIDs: nginx=$NGINX_PID, fastapi=$FASTAPI_PID"

# Keep the container running and monitor services
while true; do
    if ! kill -0 $NGINX_PID 2>/dev/null; then
        echo "Nginx died, restarting..."
        nginx -g "daemon off;" &
        NGINX_PID=$!
    fi
    
    if ! kill -0 $FASTAPI_PID 2>/dev/null; then
        echo "FastAPI died, restarting..."
        cd /app
        python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000)" &
        FASTAPI_PID=$!
    fi
    
    sleep 30
done
