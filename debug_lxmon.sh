#!/bin/bash

# lxmon System Debug Script
# Comprehensive testing of all system components

LOG_FILE="/opt/DEV/lxmon_debug_$(date +%Y%m%d_%H%M%S).log"
echo "🚀 Starting lxmon System Debug - $(date)" | tee -a "$LOG_FILE"
echo "==============================================" | tee -a "$LOG_FILE"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to test HTTP endpoint
test_endpoint() {
    local url="$1"
    local expected_code="${2:-200}"
    local description="$3"

    log "Testing: $description"
    log "URL: $url"

    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$url" 2>>"$LOG_FILE")
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_code" ]; then
        log "✅ SUCCESS - HTTP $http_code"
        if [ ${#body} -lt 500 ]; then
            log "Response: $body"
        else
            log "Response: $(echo "$body" | head -c 200)... (truncated)"
        fi
    else
        log "❌ FAILED - HTTP $http_code (expected $expected_code)"
        log "Response: $body"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test API authentication
test_auth() {
    log "Testing Authentication System"

    # Test login
    login_response=$(curl -s -X POST "http://192.168.211.128:8000/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=demo&password=demo123" 2>>"$LOG_FILE")

    if echo "$login_response" | grep -q "access_token"; then
        log "✅ Login successful"
        token=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        log "Token obtained: ${token:0:20}..."

        # Test protected endpoint
        auth_response=$(curl -s -H "Authorization: Bearer $token" \
            "http://192.168.211.128:8000/api/auth/me" 2>>"$LOG_FILE")

        if echo "$auth_response" | grep -q "username"; then
            log "✅ Protected endpoint accessible"
        else
            log "❌ Protected endpoint failed"
            log "Response: $auth_response"
        fi
    else
        log "❌ Login failed"
        log "Response: $login_response"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to check container health
check_containers() {
    log "Checking Container Health"

    containers=("lxmon-server" "lxmon-dashboard" "postgres" "redis" "lxmon-agent")
    for container in "${containers[@]}"; do
        status=$(docker-compose ps "$container" --format "table {{.Status}}" | tail -n 1)
        log "$container: $status"
    done
    echo "" | tee -a "$LOG_FILE"
}

# Function to test CORS
test_cors() {
    log "Testing CORS Configuration"

    cors_response=$(curl -s -X OPTIONS "http://192.168.211.128:8000/api/auth/login" \
        -H "Origin: http://192.168.211.128:3000" \
        -H "Access-Control-Request-Method: POST" \
        -v 2>&1 | grep -i "access-control-allow-origin" | head -1)

    if [ -n "$cors_response" ]; then
        log "✅ CORS headers present: $cors_response"
    else
        log "❌ CORS headers missing"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test Tailwind CSS
test_tailwind() {
    log "Testing Tailwind CSS"

    css_content=$(curl -s "http://192.168.211.128:3000/assets/index-B6JVXMrT.css" 2>>"$LOG_FILE")

    if echo "$css_content" | grep -q "tailwindcss"; then
        log "✅ Tailwind CSS loaded successfully"
        log "CSS size: $(echo "$css_content" | wc -c) bytes"
    else
        log "❌ Tailwind CSS not found"
    fi

    # Test if CSS classes are working
    login_page=$(curl -s "http://192.168.211.128:3000/login" 2>>"$LOG_FILE")
    if echo "$login_page" | grep -q "class="; then
        log "✅ CSS classes found in HTML"
    else
        log "❌ No CSS classes found in HTML"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test database connectivity
test_database() {
    log "Testing Database Connectivity"

    # Test health endpoint which includes DB check
    health_response=$(curl -s "http://192.168.211.128:8000/health" 2>>"$LOG_FILE")

    if echo "$health_response" | grep -q '"status": "healthy"'; then
        log "✅ Database connection healthy"

        # Extract database stats
        db_servers=$(echo "$health_response" | grep -o '"servers_registered": [0-9]*' | cut -d: -f2 | tr -d ' ')
        db_metrics=$(echo "$health_response" | grep -o '"total_metrics": [0-9]*' | cut -d: -f2 | tr -d ' ')

        log "Database stats: $db_servers servers, $db_metrics metrics"
    else
        log "❌ Database connection unhealthy"
        log "Health response: $health_response"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test Redis connectivity
test_redis() {
    log "Testing Redis Connectivity"

    health_response=$(curl -s "http://192.168.211.128:8000/health" 2>>"$LOG_FILE")

    if echo "$health_response" | grep -q '"redis":.*"status": "healthy"'; then
        log "✅ Redis connection healthy"

        # Extract Redis stats
        redis_clients=$(echo "$health_response" | grep -o '"connected_clients": [0-9]*' | cut -d: -f2 | tr -d ' ')
        redis_memory=$(echo "$health_response" | grep -o '"used_memory": "[^"]*"' | cut -d'"' -f4)

        log "Redis stats: $redis_clients clients, $redis_memory memory"
    else
        log "❌ Redis connection unhealthy"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test system monitoring
test_monitoring() {
    log "Testing System Monitoring"

    system_info=$(curl -s "http://192.168.211.128:8000/api/system/info" 2>>"$LOG_FILE")

    if echo "$system_info" | grep -q "cpu"; then
        log "✅ System monitoring working"

        # Extract system stats
        cpu_usage=$(echo "$system_info" | grep -o '"usage_percent": [0-9.]*' | head -1 | cut -d: -f2 | tr -d ' ')
        memory_usage=$(echo "$system_info" | grep -o '"usage_percent": [0-9.]*' | tail -1 | cut -d: -f2 | tr -d ' ')

        log "System stats: CPU ${cpu_usage}%, Memory ${memory_usage}%"
    else
        log "❌ System monitoring failed"
        log "Response: $system_info"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to test dashboard accessibility
test_dashboard() {
    log "Testing Dashboard Accessibility"

    # Test main dashboard page
    dashboard_response=$(curl -s -I "http://192.168.211.128:3000/" 2>>"$LOG_FILE" | head -1)
    if echo "$dashboard_response" | grep -q "200"; then
        log "✅ Dashboard main page accessible"
    else
        log "❌ Dashboard main page not accessible: $dashboard_response"
    fi

    # Test login page
    login_response=$(curl -s -I "http://192.168.211.128:3000/login" 2>>"$LOG_FILE" | head -1)
    if echo "$login_response" | grep -q "200"; then
        log "✅ Dashboard login page accessible"
    else
        log "❌ Dashboard login page not accessible: $login_response"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Main execution
log "🔍 Starting comprehensive system tests..."

# Basic connectivity tests
log "📡 Testing basic connectivity..."
test_endpoint "http://192.168.211.128:8000/health" "200" "Server Health Check"
test_endpoint "http://192.168.211.128:3000/health" "200" "Dashboard Health Check"
test_endpoint "http://192.168.211.128:8000/docs" "200" "API Documentation"

# Container health
check_containers

# Core functionality tests
test_database
test_redis
test_monitoring
test_auth
test_cors
test_tailwind
test_dashboard

# Final summary
log "🎯 System Debug Complete!"
log "Log file saved to: $LOG_FILE"
log "=============================================="

echo "Debug log created: $LOG_FILE"
echo "Run 'cat $LOG_FILE' to view detailed results"
