#!/bin/bash

# Quick start script for generating team performance reports
# Usage: ./run_report.sh [--detailed] [--week-of YYYY-MM-DD]
#   --week-of  Date inside the week to report on for LAST WEEK AVERAGE.
#              Defaults to the previous completed week (last Saturday).

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
WEEK_OF=""
while [ $# -gt 0 ]; do
    case $1 in
        --detailed)
            DETAILED="--detailed"
            ;;
        --week-of)
            WEEK_OF="$2"
            shift
            ;;
        --week-of=*)
            WEEK_OF="${1#*=}"
            ;;
    esac
    shift
done

# Build optional --week-of flag for the python call
WEEK_OF_ARG=""
if [ -n "$WEEK_OF" ]; then
    WEEK_OF_ARG="--week-of $WEEK_OF"
fi

# Check if credentials are set
if [ "$EMAIL" = "your.email@example.com" ] || [ "$API_TOKEN" = "your-api-token" ]; then
    echo "Please set your JIRA credentials:"
    echo "  export JIRA_EMAIL=your.email@example.com"
    echo "  export JIRA_API_TOKEN=your-api-token"
    exit 1
fi

echo "Generating team performance report..."
echo "Projects: IA, DATA, POD1, POD2, POD3, POD4"
echo "Period: Last 1 weeks"
echo ""

python3 dora_metrics.py \
    --jira-url "$JIRA_URL" \
    --email "$EMAIL" \
    --api-token "$API_TOKEN" \
    --projects IA,DATA,POD1,POD2,POD3,POD4 \
    --teams POD1,POD2,POD3,POD4 \
    --start-date "$(date -d '2 week ago' +%Y-%m-%d)" \
    --output "team_report_$(date +%Y%m%d%h).json" \
    $WEEK_OF_ARG \
    $DETAILED

echo ""
echo "Report generation complete!"
