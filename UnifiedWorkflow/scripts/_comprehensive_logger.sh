#!/bin/bash
# scripts/_comprehensive_logger.sh
# Wrapper script that runs both diagnostic logging and real-time error monitoring

# Get the directory of the script itself
SCRIPT_DIR="/app/scripts"

echo "--- Comprehensive Logger Started at $(date) ---"

# Make sure all scripts are executable
chmod +x "$SCRIPT_DIR/_diagnostic_logger.sh"
chmod +x "$SCRIPT_DIR/_realtime_error_monitor.sh"
chmod +x "$SCRIPT_DIR/_app_log_collector.sh"
chmod +x "$SCRIPT_DIR/_log_rotator.sh"

chmod +x "$SCRIPT_DIR/_noisy_log_collector.sh"

chmod +x "$SCRIPT_DIR/_container_inspector.sh"

# Start the diagnostic logger for container death events in background
echo "Starting diagnostic logger for container failure events..."
"$SCRIPT_DIR/_diagnostic_logger.sh" &
DIAGNOSTIC_PID=$!

# Start the real-time error monitor in background
echo "Starting real-time error monitor for running containers..."
"$SCRIPT_DIR/_realtime_error_monitor.sh" &
REALTIME_PID=$!

# Start the application log collector in background
echo "Starting application log collector for debug files..."
"$SCRIPT_DIR/_app_log_collector.sh" &
APP_LOG_PID=$!

# Start the log rotator in background
echo "Starting log rotator for automatic log management..."
"$SCRIPT_DIR/_log_rotator.sh" &
ROTATOR_PID=$!

# Start the noisy log collector in background
echo "Starting noisy log collector..."
"$SCRIPT_DIR/_noisy_log_collector.sh" &
NOISY_LOG_PID=$!

# Start the container inspector in background
echo "Starting container inspector..."
"$SCRIPT_DIR/_container_inspector.sh" &
INSPECTOR_PID=$!

# Function to handle cleanup on exit
cleanup() {
    echo "Shutting down comprehensive logger..."
    kill $DIAGNOSTIC_PID 2>/dev/null
    kill $REALTIME_PID 2>/dev/null
    kill $APP_LOG_PID 2>/dev/null
    kill $ROTATOR_PID 2>/dev/null
    kill $NOISY_LOG_PID 2>/dev/null
    kill $INSPECTOR_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "All loggers are running:"
echo "  - Diagnostic logger PID: $DIAGNOSTIC_PID"
echo "  - Real-time monitor PID: $REALTIME_PID" 
echo "  - App log collector PID: $APP_LOG_PID"
echo "  - Container inspector PID: $INSPECTOR_PID"

# Wait for any process to exit
wait $DIAGNOSTIC_PID $REALTIME_PID $APP_LOG_PID $ROTATOR_PID $NOISY_LOG_PID $INSPECTOR_PID