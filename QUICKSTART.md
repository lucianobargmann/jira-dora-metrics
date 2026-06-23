# Quick Start - 3 Steps

## Step 1: Set up credentials

Create a `.env` file in `/home/luke/code/release-checker/`:

```bash
cd /home/luke/code/release-checker
nano .env
```

Add your JIRA credentials:
```
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your-api-token-here
```

Get your API token from: https://id.atlassian.com/manage-profile/security/api-tokens

## Step 2: Install dependencies

```bash
cd /home/luke/code/metrics
pip install -r requirements.txt
```

## Step 3: Run your report

### Test connection first:
```bash
python3 test_connection.py
```

### Generate team performance report:
```bash
# Last 12 weeks, POD1, POD2, POD3 and POD4 teams
python3 run_with_env.py --teams POD1,POD2,POD3,POD4

# Custom date range
python3 run_with_env.py --teams POD1,POD2,POD3,POD4 --start-date 2024-09-01 --end-date 2024-11-17

# Save to JSON file
python3 run_with_env.py --teams POD1,POD2,POD3,POD4 --output my_report.json
```

That's it! The report will show:
- Weekly summaries of cycle time and lead time
- Overall metrics for the period
- Breakdown by team (POD1, POD2, POD3, POD4)
- Individual team member performance

---

For more details, see SETUP.md or README.md
