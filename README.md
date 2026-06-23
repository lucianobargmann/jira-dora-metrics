# JIRA Metrics Calculator

Extract and analyze team performance metrics from JIRA.

## Features

- **Weekly Summaries**: Get weekly breakdowns of cycle time and lead time
- **Team Drill-down**: Analyze performance by team (POD1, POD2, POD3, POD4, etc.)
- **Individual Performance**: Drill down to team member level
- **Default Date Range**: Automatically uses last 12 weeks if not specified
- **DORA Metrics**: Classic DORA metrics (Deployment Frequency, Lead Time, MTTR, Change Failure Rate)

## Installation

```bash
pip install requests
```

## Usage

### Team Performance Report (Default Mode)

Get team performance metrics with weekly summaries:

```bash
python dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN
```

This will:
- Use the last 12 weeks by default
- Show weekly summaries of cycle time and lead time
- Include all projects: IA, DATA, POD1, POD2, POD3, POD4

### Drill Down to Specific Teams

```bash
python dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN \
  --teams POD1,POD2,POD3,POD4
```

This will show:
1. Overall weekly summary
2. Team-level breakdown for POD1, POD2, POD3 and POD4
3. Individual team member performance within each team

### Custom Date Range

```bash
python dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --teams POD1,POD2,POD3,POD4
```

### Save Report to File

```bash
python dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN \
  --teams POD1,POD2,POD3,POD4 \
  --output report.json
```

### DORA Metrics Mode

For traditional DORA metrics:

```bash
python dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN \
  --mode dora \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

## Getting Your Credentials

### Cloud ID
1. Go to https://admin.atlassian.com/
2. Select your organization
3. Find your Cloud ID in the URL or organization settings

### API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name and copy the token

## Report Output

### Team Performance Report

The report includes:

1. **Overall Weekly Summary**
   - Issues completed per week
   - Mean and median cycle time
   - Mean and median lead time

2. **Overall Summary**
   - Total issues across the period
   - Aggregated cycle time and lead time metrics

3. **Team Breakdown** (if --teams specified)
   - Team-level metrics
   - Weekly breakdown for each team
   - Individual team member performance

4. **Individual Performance** (if --teams not specified)
   - Per-contributor metrics across all projects

## Metrics Explained

### Cycle Time
Time from ticket creation to resolution. Measures how long work takes to complete.

### Lead Time
Similar to cycle time in this implementation. Measures time from ticket creation to resolution.

### Weekly Summary
Breaks down metrics by week, showing trends over time.

## Examples

### Quick Start (Last 12 weeks, all teams)

```bash
python dora_metrics.py \
  --cloud-id abc123 \
  --email user@example.com \
  --api-token token123
```

### Specific Team Analysis

```bash
python dora_metrics.py \
  --cloud-id abc123 \
  --email user@example.com \
  --api-token token123 \
  --teams POD1
```

### Quarterly Report with Export

```bash
python dora_metrics.py \
  --cloud-id abc123 \
  --email user@example.com \
  --api-token token123 \
  --start-date 2024-10-01 \
  --end-date 2024-12-31 \
  --teams POD1,POD2,POD3,POD4 \
  --output q4_2024_report.json
```

## Notes

- The script uses JIRA's resolution date to group tickets by week
- Only completed tickets (Done, Resolved, Closed, Released, Deployed) are included
- Cycle time and lead time are calculated from ticket creation to resolution
- For more accurate cycle time, consider enhancing the script to parse changelog for "In Progress" dates
