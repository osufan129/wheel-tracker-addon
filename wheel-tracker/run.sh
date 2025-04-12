#!/usr/bin/with-contenv bashio

# Get config
DATABASEPATH=$(bashio::config 'database_path')
LOG_LEVEL=$(bashio::config 'log_level')

# Ensure database directory exists
mkdir -p "$(dirname "$DATABASEPATH")"

# Set environment variables for the application
export DATABASE_URL="sqlite:///$DATABASEPATH"
export FLASK_ENV="production"
export FLASK_APP="app.py"

# Create a new secret key if it doesn't exist
if [ ! -f /data/secret_key ]; then
  python3 -c "import os; print(os.urandom(24).hex())" > /data/secret_key
fi

export SECRET_KEY=$(cat /data/secret_key)

# Set up ingress
INGRESS_PORT="5000"
INGRESS_ENTRY=$(bashio::addon.ingress_entry)
export INGRESS_URL="${INGRESS_ENTRY}"

# Map log level
case "${LOG_LEVEL}" in
  trace)    FLASK_LOG_LEVEL="DEBUG" ;;
  debug)    FLASK_LOG_LEVEL="DEBUG" ;;
  info)     FLASK_LOG_LEVEL="INFO" ;;
  notice)   FLASK_LOG_LEVEL="INFO" ;;
  warning)  FLASK_LOG_LEVEL="WARNING" ;;
  error)    FLASK_LOG_LEVEL="ERROR" ;;
  fatal)    FLASK_LOG_LEVEL="CRITICAL" ;;
  *)        FLASK_LOG_LEVEL="INFO" ;;
esac
export FLASK_LOG_LEVEL

# Start the Flask application using gunicorn
cd /app
python3 -m gunicorn --bind 0.0.0.0:$INGRESS_PORT \
  --workers 2 --threads 2 \
  --timeout 120 \
  --log-level $FLASK_LOG_LEVEL \
  "app:app" 