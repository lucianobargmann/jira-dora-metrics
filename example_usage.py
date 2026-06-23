#!/usr/bin/env python3
"""
Example usage of the JIRA Metrics Calculator

This script demonstrates how to use the JiraDORAMetrics class programmatically.
"""

import os
from datetime import datetime, timedelta
from dora_metrics import JiraDORAMetrics

# Get credentials from environment variables (recommended)
CLOUD_ID = os.getenv("JIRA_CLOUD_ID", "your-cloud-id")
EMAIL = os.getenv("JIRA_EMAIL", "your.email@example.com")
API_TOKEN = os.getenv("JIRA_API_TOKEN", "your-api-token")

# Initialize the calculator
calculator = JiraDORAMetrics(CLOUD_ID, EMAIL, API_TOKEN)

# Calculate date range (last 12 weeks)
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(weeks=12)).strftime("%Y-%m-%d")

print(f"Analyzing metrics from {start_date} to {end_date}\n")

# Example 1: Overall metrics across all projects
print("=" * 80)
print("Example 1: Overall Metrics")
print("=" * 80)
projects = ["IA", "DATA", "POD1", "POD2", "POD3", "POD4"]
weekly_summary = calculator.get_weekly_summary(projects, start_date, end_date)

print(f"\nTotal issues resolved: {weekly_summary['total_issues']}")
print(f"Number of weeks: {len(weekly_summary['weeks'])}\n")

for week, data in list(weekly_summary['weeks'].items())[:3]:  # Show first 3 weeks
    print(f"{week}:")
    print(f"  Issues: {data['issue_count']}")
    print(f"  Avg Cycle Time: {data['cycle_time']['mean_days']} days")
    print(f"  Avg Lead Time: {data['lead_time']['mean_days']} days")

# Example 2: Team-specific metrics (POD1)
print("\n" + "=" * 80)
print("Example 2: POD1 Team Metrics")
print("=" * 80)
saop_cycle = calculator.calculate_cycle_time(["POD1"], start_date, end_date, team="POD1")
saop_lead = calculator.calculate_lead_time(["POD1"], start_date, end_date, team="POD1")

print(f"\nPOD1 Team Performance:")
print(f"  Issues completed: {saop_cycle['sample_size']}")
print(f"  Mean cycle time: {saop_cycle['mean_cycle_time_days']} days")
print(f"  Median cycle time: {saop_cycle['median_cycle_time_days']} days")
print(f"  Mean lead time: {saop_lead['mean_lead_time_days']} days")

# Example 3: Get team members and their individual metrics
print("\n" + "=" * 80)
print("Example 3: Individual Team Member Metrics (POD1)")
print("=" * 80)
team_members = calculator.get_team_members(["POD1"], start_date, end_date, team="POD1")

print(f"\nTeam members in POD1: {', '.join(team_members)}\n")

for member in team_members[:3]:  # Show first 3 members
    member_cycle = calculator.calculate_cycle_time(
        ["POD1"], start_date, end_date, team="POD1", assignee=member
    )
    print(f"{member}:")
    print(f"  Issues: {member_cycle['sample_size']}")
    print(f"  Avg cycle time: {member_cycle['mean_cycle_time_days']} days")

# Example 4: Full team performance report
print("\n" + "=" * 80)
print("Example 4: Full Team Performance Report")
print("=" * 80)
report = calculator.generate_team_performance_report(
    projects=["POD1", "POD2", "POD3", "POD4"],
    start_date=start_date,
    end_date=end_date,
    teams=["POD1", "POD2", "POD3", "POD4"]
)

# Print the formatted report
calculator.print_team_performance_report(report)

# Optionally save to JSON
import json
with open("team_performance_report.json", "w") as f:
    json.dump(report, f, indent=2)
print("\nReport saved to team_performance_report.json")
