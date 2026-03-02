#!/usr/bin/env python3
"""
Helper to load JIRA credentials from parent directory's .env file
and extract cloud_id from JIRA URL.
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

def extract_cloud_id_from_url(jira_url: str) -> str:
    """
    Extract cloud ID from JIRA URL.

    For URLs like https://yourcompany.atlassian.net, we need to fetch the cloud ID
    from the API. For now, we'll extract the subdomain as an approximation.
    """
    # Check if it's an Atlassian cloud URL
    match = re.match(r'https://([^.]+)\.atlassian\.net', jira_url)
    if match:
        # For Atlassian Cloud, we need to make an API call to get the cloud ID
        # For now, return a placeholder that explains what's needed
        return None
    return None

def load_credentials():
    """Load JIRA credentials from parent directory's .env file."""
    # Try to load from parent directory first
    parent_env = Path(__file__).parent.parent / "release-checker" / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
        print(f"Loaded credentials from: {parent_env}")
    else:
        # Try current directory
        load_dotenv()
        print("Loaded credentials from current directory or environment")

    jira_url = os.getenv("JIRA_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_url, jira_email, jira_api_token]):
        print("\nError: Missing JIRA credentials!")
        print("Please ensure you have a .env file with:")
        print("  JIRA_URL=https://yourcompany.atlassian.net")
        print("  JIRA_EMAIL=your.email@example.com")
        print("  JIRA_API_TOKEN=your-api-token")
        print(f"\nChecked location: {parent_env}")
        sys.exit(1)

    print(f"JIRA URL: {jira_url}")
    print(f"Email: {jira_email}")

    # Remove trailing slash from URL
    jira_url = jira_url.rstrip('/')

    return jira_url, jira_email, jira_api_token

if __name__ == "__main__":
    jira_url, email, api_token = load_credentials()
    print(f"\nJIRA URL: {jira_url}")
    print(f"Email: {email}")
    print(f"API Token: {api_token[:4]}...{api_token[-4:]}")
