#!/usr/bin/env python3
"""
Test JIRA connection and display available information.
This helps verify credentials and show what data is accessible.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "release-checker"))

try:
    from config_helper import load_credentials
    from dora_metrics import JiraDORAMetrics
    from datetime import datetime, timedelta
except ImportError as e:
    print(f"Import error: {e}")
    print("\nMake sure you've installed requirements:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

def test_connection():
    """Test connection to JIRA and display available information."""
    print("=" * 80)
    print("JIRA Connection Test")
    print("=" * 80)

    # Load credentials
    print("\n1. Loading credentials...")
    try:
        jira_url, email, api_token = load_credentials()
        print(f"   ✓ JIRA URL: {jira_url}")
        print(f"   ✓ Email: {email}")
        print(f"   ✓ API Token: {api_token[:4]}...{api_token[-4:]}")
    except Exception as e:
        print(f"   ✗ Error loading credentials: {e}")
        return False

    # Initialize calculator
    print("\n2. Initializing JIRA client...")
    try:
        calculator = JiraDORAMetrics(jira_url, email, api_token)
        print("   ✓ Client initialized")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test basic query
    print("\n3. Testing JIRA query...")
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        projects = ["POD1", "POD2", "POD3", "POD4", "IA", "DATA"]
        jql = f"project in ({','.join(projects)}) AND updated >= '{start_date}'"

        print(f"   Query: {jql}")
        issues = calculator.search_issues(jql)
        print(f"   ✓ Found {len(issues)} issues updated in the last 7 days")

        if issues:
            print(f"\n   Sample issue: {issues[0]['key']}")
            print(f"   Summary: {issues[0]['fields'].get('summary', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error querying JIRA: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Get team members
    print("\n4. Getting team members...")
    try:
        for project in ["POD1", "POD2", "POD3", "POD4"]:
            try:
                members = calculator.get_team_members([project], start_date, end_date, team=project)
                print(f"   ✓ {project}: {len(members)} members")
                if members:
                    print(f"     Members: {', '.join(members[:5])}")
                    if len(members) > 5:
                        print(f"     ... and {len(members) - 5} more")
            except Exception as e:
                print(f"   ⚠ {project}: {e}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 80)
    print("Connection test complete!")
    print("=" * 80)
    print("\nYou can now run the full report with:")
    print("  python3 run_with_env.py --teams POD1,POD2,POD3,POD4")
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
