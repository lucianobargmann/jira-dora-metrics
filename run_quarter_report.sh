#!/bin/bash

# Quarterly DORA Metrics Report Generator
# Generates monthly metrics for Q4 2025 (October, November, December)
# Usage: ./run_quarter_report.sh [--year YEAR] [--quarter Q]

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set these environment variables or replace with your values
JIRA_URL="${JIRA_URL:-https://ninjio.atlassian.net}"
EMAIL="${JIRA_EMAIL:-your.email@example.com}"
API_TOKEN="${JIRA_API_TOKEN:-your-api-token}"

# Default values for Q4 2025
YEAR="${1:-2025}"
QUARTER="${2:-4}"

# Check if credentials are set
if [ "$EMAIL" = "your.email@example.com" ] || [ "$API_TOKEN" = "your-api-token" ]; then
    echo "Please set your JIRA credentials:"
    echo "  export JIRA_EMAIL=your.email@example.com"
    echo "  export JIRA_API_TOKEN=your-api-token"
    echo ""
    echo "Or create a .env file with:"
    echo "  JIRA_EMAIL=your.email@example.com"
    echo "  JIRA_API_TOKEN=your-api-token"
    exit 1
fi

# Generate output filename with timestamp
OUTPUT_FILE="Q${QUARTER}_${YEAR}_dora_metrics_$(date +%Y%m%d_%H%M%S).csv"

echo "=============================================="
echo "Quarterly DORA Metrics Report Generator"
echo "=============================================="
echo ""
echo "Configuration:"
echo "  JIRA URL: $JIRA_URL"
echo "  Projects: IA, DATA, SAOP, SAOP2"
echo "  Teams:    SAOP, SAOP2"
echo "  Year:     $YEAR"
echo "  Quarter:  Q$QUARTER"
echo "  Output:   $OUTPUT_FILE"
echo ""
echo "Collecting metrics for Q$QUARTER $YEAR..."
echo ""

python3 quarter_metrics.py \
    --jira-url "$JIRA_URL" \
    --email "$EMAIL" \
    --api-token "$API_TOKEN" \
    --projects IA,DATA,SAOP,SAOP2 \
    --teams SAOP,SAOP2 \
    --year "$YEAR" \
    --quarter "$QUARTER" \
    --output "$OUTPUT_FILE"

echo ""
echo "=============================================="
echo "Report generation complete!"
echo "Output file: $OUTPUT_FILE"
echo "=============================================="
