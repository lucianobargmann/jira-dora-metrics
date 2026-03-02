#!/usr/bin/env python3
"""
Quarterly DORA Metrics Report Generator

Generates monthly metrics for a quarter and outputs CSV in a standardized format.
Designed for Q4 2025 (October, November, December) reporting.
"""

import os
import csv
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from calendar import monthrange
from dora_metrics import JiraDORAMetrics


class QuarterlyMetricsReport:
    """Generate quarterly metrics reports with monthly breakdowns."""

    def __init__(self, jira_url: str, email: str, api_token: str):
        """Initialize with JIRA credentials."""
        self.calculator = JiraDORAMetrics(jira_url, email, api_token)

    def get_month_date_range(self, year: int, month: int) -> tuple:
        """Get the start and end dates for a given month."""
        start_date = f"{year}-{month:02d}-01"
        last_day = monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        return start_date, end_date

    def calculate_velocity(self, projects: List[str], start_date: str, end_date: str) -> int:
        """
        Calculate velocity (story points completed) for the period.

        Looks for the 'Story Points' custom field or 'customfield_10016' (common in JIRA).
        """
        jql = f"""
            project in ({','.join(projects)})
            AND resolutiondate >= '{start_date}'
            AND resolutiondate <= '{end_date}'
            AND status in (Done, Resolved, Closed, Released, Deployed)
        """

        # Common story point field names (customfield_10036 is NINJIO's field)
        fields = ["customfield_10036", "customfield_10016", "customfield_10004",
                  "customfield_10002", "Story Points", "storyPoints"]

        issues = self.calculator.search_issues(jql, fields=fields)

        total_points = 0
        for issue in issues:
            # Try different common story point field names
            for field in fields:
                points = issue["fields"].get(field)
                if points is not None:
                    try:
                        total_points += float(points)
                    except (ValueError, TypeError):
                        pass
                    break

        return int(total_points)

    def calculate_deployment_frequency_per_week(self, projects: List[str],
                                                  start_date: str, end_date: str) -> float:
        """Calculate deployments per week for the period."""
        result = self.calculator.calculate_deployment_frequency(projects, start_date, end_date)
        return result.get("deployments_per_week", 0)

    def calculate_defect_ratio(self, projects: List[str], start_date: str, end_date: str) -> float:
        """
        Calculate defect ratio as percentage.

        Defect Ratio = (Number of bugs / Total issues resolved) * 100
        """
        # Get all resolved issues
        all_jql = f"""
            project in ({','.join(projects)})
            AND resolutiondate >= '{start_date}'
            AND resolutiondate <= '{end_date}'
            AND status in (Done, Resolved, Closed)
        """
        all_issues = self.calculator.search_issues(all_jql, fields=["issuetype"])

        # Count bugs
        bug_count = 0
        for issue in all_issues:
            issue_type = issue["fields"].get("issuetype", {})
            type_name = issue_type.get("name", "").lower() if issue_type else ""
            if type_name in ["bug", "defect", "incident"]:
                bug_count += 1

        total_issues = len(all_issues)
        if total_issues == 0:
            return 0.0

        return round((bug_count / total_issues) * 100, 0)

    def count_reported_defects(self, projects: List[str], start_date: str, end_date: str) -> int:
        """Count bugs/defects created during the period."""
        jql = f"""
            project in ({','.join(projects)})
            AND created >= '{start_date}'
            AND created <= '{end_date}'
            AND issuetype in (Bug, Defect, Incident)
        """
        issues = self.calculator.search_issues(jql, fields=["key"])
        return len(issues)

    def collect_monthly_metrics(self, projects: List[str], year: int, month: int,
                                 teams: Optional[List[str]] = None) -> Dict:
        """Collect all metrics for a single month."""
        start_date, end_date = self.get_month_date_range(year, month)
        month_name = datetime(year, month, 1).strftime("%B")

        print(f"  Collecting metrics for {month_name} {year} ({start_date} to {end_date})...")

        # Calculate each metric
        print(f"    - Velocity...")
        velocity = self.calculate_velocity(projects, start_date, end_date)

        print(f"    - Cycle Time...")
        cycle_time_result = self.calculator.calculate_cycle_time(projects, start_date, end_date)
        cycle_time = cycle_time_result.get("mean_cycle_time_days", 0)

        print(f"    - Deployment Frequency...")
        deployment_freq = self.calculate_deployment_frequency_per_week(projects, start_date, end_date)

        print(f"    - Lead Time...")
        lead_time_result = self.calculator.calculate_lead_time(projects, start_date, end_date)
        lead_time = lead_time_result.get("mean_lead_time_days", 0)

        print(f"    - Defect Ratio...")
        defect_ratio = self.calculate_defect_ratio(projects, start_date, end_date)

        print(f"    - Change Failure Rate...")
        cfr_result = self.calculator.calculate_change_failure_rate(projects, start_date, end_date)
        change_failure_rate = cfr_result.get("change_failure_rate_percentage", 0)

        print(f"    - Reported Defects...")
        reported_defects = self.count_reported_defects(projects, start_date, end_date)

        return {
            "month": month_name,
            "year": year,
            "velocity": velocity,
            "cycle_time": round(cycle_time, 2),
            "deployment_freq": round(deployment_freq, 1),
            "lead_time": round(lead_time, 2),
            "defect_ratio": f"{int(defect_ratio)}%",
            "change_failure_rate": f"{int(change_failure_rate)}%",
            "reported_defects": reported_defects,
            "uptime": "TBD"  # Uptime requires external monitoring data
        }

    def collect_quarter_metrics(self, projects: List[str], year: int, quarter: int,
                                  teams: Optional[List[str]] = None) -> List[Dict]:
        """Collect metrics for an entire quarter (3 months)."""
        # Map quarter to months
        quarter_months = {
            1: [1, 2, 3],    # Q1: Jan, Feb, Mar
            2: [4, 5, 6],    # Q2: Apr, May, Jun
            3: [7, 8, 9],    # Q3: Jul, Aug, Sep
            4: [10, 11, 12]  # Q4: Oct, Nov, Dec
        }

        months = quarter_months.get(quarter, [10, 11, 12])

        print(f"\nCollecting Q{quarter} {year} metrics for projects: {', '.join(projects)}")
        print("=" * 60)

        monthly_data = []
        for month in months:
            data = self.collect_monthly_metrics(projects, year, month, teams)
            monthly_data.append(data)

        return monthly_data

    def generate_csv(self, monthly_data: List[Dict], output_path: str):
        """Generate CSV output in the standard DORA metrics format."""
        if not monthly_data:
            print("No data to export.")
            return

        # Get month names for column headers
        months = [d["month"] for d in monthly_data]

        # Define metrics rows matching the expected format
        metrics = [
            ("Velocity (pts)", "Productivity", [str(d["velocity"]) for d in monthly_data]),
            ("Cycle Time (days)", "Delivery", [str(d["cycle_time"]) for d in monthly_data]),
            ("Deployment Freq. (#/wk)", "Delivery", [str(d["deployment_freq"]) for d in monthly_data]),
            ("Lead Time (days)", "Delivery", [str(d["lead_time"]) for d in monthly_data]),
            ("Defect Ratio (%)", "Quality", [d["defect_ratio"] for d in monthly_data]),
            ("Change Failure Rate (%)", "Quality", [d["change_failure_rate"] for d in monthly_data]),
            ("Reported Defects (#)", "Quality", [str(d["reported_defects"]) for d in monthly_data]),
            ("Uptime (%)", "Stability", [d["uptime"] for d in monthly_data]),
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header row
            header = ["Measure", "Category"] + months
            writer.writerow(header)

            # Write metric rows
            for measure, category, values in metrics:
                row = [measure, category] + values
                writer.writerow(row)

        print(f"\nCSV report saved to: {output_path}")

    def print_summary(self, monthly_data: List[Dict]):
        """Print a formatted summary of the quarterly metrics."""
        if not monthly_data:
            print("No data to display.")
            return

        print("\n" + "=" * 80)
        print("QUARTERLY DORA METRICS SUMMARY")
        print("=" * 80)

        # Header
        months = [d["month"] for d in monthly_data]
        header = f"{'Measure':<30} {'Category':<15}" + "".join(f"{m:>12}" for m in months)
        print(header)
        print("-" * 80)

        # Data rows
        rows = [
            ("Velocity (pts)", "Productivity", [d["velocity"] for d in monthly_data]),
            ("Cycle Time (days)", "Delivery", [d["cycle_time"] for d in monthly_data]),
            ("Deployment Freq. (#/wk)", "Delivery", [d["deployment_freq"] for d in monthly_data]),
            ("Lead Time (days)", "Delivery", [d["lead_time"] for d in monthly_data]),
            ("Defect Ratio (%)", "Quality", [d["defect_ratio"] for d in monthly_data]),
            ("Change Failure Rate (%)", "Quality", [d["change_failure_rate"] for d in monthly_data]),
            ("Reported Defects (#)", "Quality", [d["reported_defects"] for d in monthly_data]),
            ("Uptime (%)", "Stability", [d["uptime"] for d in monthly_data]),
        ]

        for measure, category, values in rows:
            value_str = "".join(f"{str(v):>12}" for v in values)
            print(f"{measure:<30} {category:<15}{value_str}")

        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Generate quarterly DORA metrics report")
    parser.add_argument("--jira-url", required=True,
                        help="JIRA instance URL (e.g., https://yourcompany.atlassian.net)")
    parser.add_argument("--email", required=True, help="Atlassian account email")
    parser.add_argument("--api-token", required=True, help="Atlassian API token")
    parser.add_argument("--projects", default="IA,DATA,SAOP,SAOP2",
                        help="Comma-separated project keys (default: IA,DATA,SAOP,SAOP2)")
    parser.add_argument("--year", type=int, default=2025,
                        help="Year for the report (default: 2025)")
    parser.add_argument("--quarter", type=int, default=4, choices=[1, 2, 3, 4],
                        help="Quarter number 1-4 (default: 4 for Q4)")
    parser.add_argument("--teams",
                        help="Comma-separated team names (e.g., SAOP,SAOP2)")
    parser.add_argument("--output", default="quarter_metrics.csv",
                        help="Output CSV file path (default: quarter_metrics.csv)")

    args = parser.parse_args()

    # Parse inputs
    projects = [p.strip() for p in args.projects.split(",")]
    teams = [t.strip() for t in args.teams.split(",")] if args.teams else None

    # Initialize report generator
    report = QuarterlyMetricsReport(args.jira_url, args.email, args.api_token)

    # Collect quarterly metrics
    monthly_data = report.collect_quarter_metrics(projects, args.year, args.quarter, teams)

    # Print summary
    report.print_summary(monthly_data)

    # Generate CSV
    report.generate_csv(monthly_data, args.output)


if __name__ == "__main__":
    main()
