# Quick Setup Guide

## Option 1: Create a .env file (Recommended)

Create a `.env` file in the `release-checker` directory with your JIRA credentials:

```bash
cd /home/luke/code/release-checker
cat > .env << 'EOF'
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your-jira-api-token
BITBUCKET_URL=https://api.bitbucket.org/2.0
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_USERNAME=your-username
BITBUCKET_APP_PASSWORD=your-app-password
PROJECT_KEY=SAOP
REPOSITORY_SLUG=your-repo
DEFAULT_BRANCH=main
EOF
```

Then edit the file with your actual credentials:
```bash
nano .env  # or vim .env, or use your preferred editor
```

Once configured, you can run the metrics report with:
```bash
cd /home/luke/code/metrics
python3 run_with_env.py --teams SAOP,SAOP2
```

## Option 2: Use environment variables directly

Set environment variables in your shell:

```bash
export JIRA_URL=https://yourcompany.atlassian.net
export JIRA_EMAIL=your.email@example.com
export JIRA_API_TOKEN=your-jira-api-token
```

Then run with the same command:
```bash
python3 run_with_env.py --teams SAOP,SAOP2
```

## Option 3: Use command line arguments (Original method)

If you know your cloud ID directly:

```bash
python3 dora_metrics.py \
  --cloud-id YOUR_CLOUD_ID \
  --email your.email@example.com \
  --api-token YOUR_API_TOKEN \
  --teams SAOP,SAOP2
```

## Getting Your JIRA Credentials

### JIRA URL
Your JIRA URL is typically: `https://yourcompany.atlassian.net`

### JIRA Email
The email address you use to log into JIRA.

### JIRA API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "Metrics Script")
4. Copy the token (you won't be able to see it again!)

## Running Your First Report

After setting up credentials, try:

```bash
# Default: Last 12 weeks, all projects
python3 run_with_env.py

# Specific teams
python3 run_with_env.py --teams SAOP,SAOP2

# Custom date range
python3 run_with_env.py --teams SAOP,SAOP2 --start-date 2024-01-01 --end-date 2024-03-31

# Save to file
python3 run_with_env.py --teams SAOP,SAOP2 --output report.json
```

## Troubleshooting

### Cloud ID issues
If you get cloud ID errors, the script will try to auto-detect it from your JIRA URL. If that fails:

1. Go to https://admin.atlassian.com/
2. Select your organization
3. Note the cloud ID from the URL or settings

### Permission issues
Make sure your API token has permission to:
- Read issues in your projects
- Access user information
- View project details
