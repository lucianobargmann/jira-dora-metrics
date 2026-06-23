#!/usr/bin/env python3
"""
Run the team performance report using credentials from parent directory's .env file.
This is a convenience wrapper that loads credentials and runs the report.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import from release-checker if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "release-checker"))

from config_helper import load_credentials
from dora_metrics import JiraDORAMetrics
from excel_exporter import export_report_to_excel
import json
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Generate JIRA team performance report using .env credentials"
    )
    parser.add_argument(
        "--projects",
        default="IA,DATA,POD1,POD2,POD3,POD4",
        help="Comma-separated project keys (default: IA,DATA,POD1,POD2,POD3,POD4)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date in YYYY-MM-DD format (default: 12 weeks ago)"
    )
    parser.add_argument(
        "--end-date",
        help="End date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "--teams",
        help="Comma-separated team names for drill-down (e.g., POD1,POD2,POD3,POD4)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (optional). Use .json for JSON or .xlsx for Excel"
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Export to Excel format (in addition to console output)"
    )
    parser.add_argument(
        "--mode",
        default="team-performance",
        choices=["team-performance", "dora"],
        help="Report mode: team-performance (default) or dora"
    )

    args = parser.parse_args()

    # Load credentials from .env file
    print("Loading credentials from .env file...")
    try:
        jira_url, email, api_token = load_credentials()
    except Exception as e:
        print(f"Error loading credentials: {e}")
        sys.exit(1)

    # Parse projects
    projects = [p.strip() for p in args.projects.split(",")]

    # Parse teams if provided
    teams = [t.strip() for t in args.teams.split(",")] if args.teams else None

    # Calculate default dates (last 12 weeks)
    if not args.end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    else:
        end_date = args.end_date

    if not args.start_date:
        start_dt = datetime.now() - timedelta(weeks=12)
        start_date = start_dt.strftime("%Y-%m-%d")
    else:
        start_date = args.start_date

    print(f"\nGenerating report for period: {start_date} to {end_date}")
    if teams:
        print(f"Teams: {', '.join(teams)}")
    print()

    # Initialize calculator
    calculator = JiraDORAMetrics(jira_url, email, api_token)

    # Generate and print report based on mode
    try:
        if args.mode == "team-performance":
            report = calculator.generate_team_performance_report(
                projects, start_date, end_date, teams
            )
            calculator.print_team_performance_report(report)
        else:  # dora mode
            report = calculator.generate_report(projects, start_date, end_date)
            calculator.print_report(report)

        # Save to file if requested
        if args.output:
            if args.output.endswith('.xlsx'):
                # Export to Excel
                excel_file = export_report_to_excel(report, args.output)
                print(f"\n✓ Excel report saved to: {excel_file}")
            elif args.output.endswith('.json'):
                # Export to JSON
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\n✓ JSON report saved to: {args.output}")
            else:
                # Auto-detect based on content or default to JSON
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\n✓ Report saved to: {args.output}")

        # Export to Excel if flag is set (even without --output)
        if args.excel and not (args.output and args.output.endswith('.xlsx')):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_file = export_report_to_excel(report, f"jira_metrics_{timestamp}.xlsx")
            print(f"\n✓ Excel report saved to: {excel_file}")

    except Exception as e:
        print(f"\nError generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
