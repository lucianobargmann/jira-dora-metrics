#!/bin/bash

# Velocity & Ticket Count Report runner
# Usage: ./run_velocity_report.sh

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Credentials with fallback defaults
JIRA_URL="${JIRA_URL:-https://ninjio.atlassian.net}"
EMAIL="${JIRA_EMAIL:-your.email@example.com}"
API_TOKEN="${JIRA_API_TOKEN:-your-api-token}"

# Validate credentials
if [ "$EMAIL" = "your.email@example.com" ] || [ "$API_TOKEN" = "your-api-token" ]; then
    echo "Please set your JIRA credentials:"
    echo "  export JIRA_EMAIL=your.email@example.com"
    echo "  export JIRA_API_TOKEN=your-api-token"
    echo "Or create a .env file with JIRA_EMAIL and JIRA_API_TOKEN."
    exit 1
fi

PROJECTS="IA,DATA,POD1,POD2,POD3,POD4"
START_DATE="$(date -d '26 weeks ago' +%Y-%m-%d)"
END_DATE="$(date +%Y-%m-%d)"
OUTPUT="velocity_report_$(date +%Y%m%d_%H%M%S)"

echo "Generating Velocity & Ticket Count Report..."
echo "Projects: $PROJECTS"
echo "Period: $START_DATE to $END_DATE"
echo ""

# Use venv if available (for openpyxl Excel support)
PYTHON="python3"
if [ -f .venv/bin/python3 ]; then
    PYTHON=".venv/bin/python3"
fi

$PYTHON velocity_report.py \
    --jira-url "$JIRA_URL" \
    --email "$EMAIL" \
    --api-token "$API_TOKEN" \
    --projects "$PROJECTS" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --output "$OUTPUT" \
    --format all

echo ""
echo "Report generation complete!"
