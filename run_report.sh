#!/bin/bash

# Quick start script for generating team performance reports
# Usage: ./run_report.sh [--detailed]

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set these environment variables or replace with your values
JIRA_URL="${JIRA_URL:-https://ninjio.atlassian.net}"
EMAIL="${JIRA_EMAIL:-your.email@example.com}"
API_TOKEN="${JIRA_API_TOKEN:-your-api-token}"

# Parse arguments
DETAILED=""
for arg in "$@"; do
    case $arg in
        --detailed)
            DETAILED="--detailed"
            ;;
    esac
done

# Check if credentials are set
if [ "$EMAIL" = "your.email@example.com" ] || [ "$API_TOKEN" = "your-api-token" ]; then
    echo "Please set your JIRA credentials:"
    echo "  export JIRA_EMAIL=your.email@example.com"
    echo "  export JIRA_API_TOKEN=your-api-token"
    exit 1
fi

echo "Generating team performance report..."
echo "Projects: IA, DATA, SAOP, SAOP2"
echo "Period: Last 1 weeks"
echo ""

python3 dora_metrics.py \
    --jira-url "$JIRA_URL" \
    --email "$EMAIL" \
    --api-token "$API_TOKEN" \
    --projects IA,DATA,SAOP,SAOP2 \
    --teams SAOP,SAOP2 \
    --start-date "$(date -d '2 week ago' +%Y-%m-%d)" \
    --output "team_report_$(date +%Y%m%d%h).json" \
    $DETAILED

echo ""
echo "Report generation complete!"
