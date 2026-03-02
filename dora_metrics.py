#!/usr/bin/env python3
"""
JIRA DORA Metrics Calculator

This script calculates the four key DORA (DevOps Research and Assessment) metrics:
1. Deployment Frequency
2. Lead Time for Changes
3. Mean Time to Recovery (MTTR)
4. Change Failure Rate

Usage:
    python dora_metrics.py --start-date 2024-01-01 --end-date 2024-12-31
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import json
from collections import defaultdict
import statistics


class JiraDORAMetrics:
    def __init__(self, jira_url: str, email: str, api_token: str):
        """
        Initialize JIRA DORA Metrics calculator.

        Args:
            jira_url: Your JIRA instance URL (e.g., https://yourcompany.atlassian.net)
            email: Your Atlassian account email
            api_token: Your Atlassian API token
        """
        # Remove trailing slash if present
        self.base_url = jira_url.rstrip('/')
        self.auth = (email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def search_issues(self, jql: str, fields: List[str] = None, max_results: int = 100) -> List[Dict]:
        """Search JIRA issues using JQL with the new API endpoint."""
        if fields is None:
            fields = ["summary", "status", "created", "resolutiondate", "priority",
                     "issuetype", "labels", "assignee", "key"]

        all_issues = []
        next_page_token = None

        while True:
            url = f"{self.base_url}/rest/api/3/search/jql"

            payload = {
                "jql": jql,
                "fields": fields,
                "maxResults": max_results
            }

            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
            response.raise_for_status()
            data = response.json()

            issues = data.get("issues", [])
            all_issues.extend(issues)

            # Check if there are more pages
            is_last = data.get("isLast", True)
            if is_last:
                break

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return all_issues
    
    def calculate_deployment_frequency(self, projects: List[str], start_date: str, end_date: str) -> Dict:
        """
        Calculate Deployment Frequency.
        
        Assumptions:
        - Issues with label 'deployment' or 'release' are deployments
        - Or issues of type 'Deployment' if such type exists
        - Or resolved issues in Production environment
        
        Returns deployment frequency per day/week/month.
        """
        jql = f"""
            project in ({','.join(projects)}) 
            AND resolutiondate >= '{start_date}' 
            AND resolutiondate <= '{end_date}'
            AND (labels in (deployment, release, prod, production) 
                 OR issuetype = Deployment
                 OR status in (Released, Deployed))
        """
        
        deployments = self.search_issues(jql)
        
        # Calculate time span
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        weeks = days / 7
        months = days / 30.44
        
        deployment_count = len(deployments)
        
        # Group deployments by date
        deployments_by_date = defaultdict(int)
        for issue in deployments:
            resolution_date = issue["fields"].get("resolutiondate")
            if resolution_date:
                date = datetime.strptime(resolution_date[:10], "%Y-%m-%d").date()
                deployments_by_date[date] += 1
        
        return {
            "total_deployments": deployment_count,
            "days_in_period": days,
            "deployments_per_day": round(deployment_count / days, 2),
            "deployments_per_week": round(deployment_count / weeks, 2),
            "deployments_per_month": round(deployment_count / months, 2),
            "deployment_dates": dict(deployments_by_date),
            "rating": self._rate_deployment_frequency(deployment_count / days)
        }
    
    def get_issue_changelog(self, issue_key: str) -> List[Dict]:
        """Get the changelog for a specific issue."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/changelog"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        data = response.json()
        return data.get("values", [])

    def get_in_progress_date(self, issue_key: str, created_date: str) -> str:
        """
        Get the date when an issue first moved to 'In Progress' status.
        Falls back to created date if no In Progress transition found.

        Args:
            issue_key: The JIRA issue key
            created_date: The issue creation date as fallback

        Returns:
            ISO format datetime string of when work started
        """
        try:
            changelog = self.get_issue_changelog(issue_key)

            # Look for the first transition to an "in progress" type status
            in_progress_statuses = [
                'in progress', 'in development', 'in review', 'in testing',
                'dev in progress', 'development', 'coding', 'working',
                'started', 'active', 'doing'
            ]

            for entry in changelog:
                for item in entry.get("items", []):
                    if item.get("field") == "status":
                        to_status = (item.get("toString") or "").lower()
                        if any(status in to_status for status in in_progress_statuses):
                            return entry.get("created", created_date)

            # If no "in progress" found, return created date
            return created_date
        except Exception:
            # On any error, fall back to created date
            return created_date

    def get_issues_with_changelog(self, projects: List[str], start_date: str, end_date: str,
                                   team: Optional[str] = None, assignee: Optional[str] = None) -> List[Dict]:
        """
        Fetch issues with their In Progress dates for accurate cycle time calculation.

        Returns list of issues with both created_date and in_progress_date.
        """
        jql_parts = [
            f"project in ({','.join(projects)})",
            f"resolutiondate >= '{start_date}'",
            f"resolutiondate <= '{end_date}'",
            "status in (Done, Resolved, Closed, Released, Deployed)"
        ]

        if team:
            jql_parts.append(f"project = {team}")
        if assignee:
            jql_parts.append(f"assignee = '{assignee}'")

        jql = " AND ".join(jql_parts)
        fields = ["summary", "status", "created", "resolutiondate", "assignee", "issuetype", "key"]
        issues = self.search_issues(jql, fields=fields)

        enriched_issues = []
        total = len(issues)

        for idx, issue in enumerate(issues):
            key = issue["key"]
            created = issue["fields"].get("created")
            resolved = issue["fields"].get("resolutiondate")

            if not resolved or not created:
                continue

            # Get the in-progress date from changelog
            in_progress_date = self.get_in_progress_date(key, created)

            assignee_obj = issue["fields"].get("assignee")
            assignee_name = assignee_obj.get("displayName", "Unassigned") if assignee_obj else "Unassigned"

            enriched_issues.append({
                "key": key,
                "summary": issue["fields"].get("summary", ""),
                "assignee": assignee_name,
                "created": created,
                "in_progress_date": in_progress_date,
                "resolved": resolved
            })

            # Progress indicator for large datasets
            if (idx + 1) % 50 == 0:
                print(f"    Fetched changelog for {idx + 1}/{total} issues...")

        return enriched_issues

    def calculate_cycle_time(self, projects: List[str], start_date: str, end_date: str,
                            team: Optional[str] = None, assignee: Optional[str] = None,
                            enriched_issues: Optional[List[Dict]] = None) -> Dict:
        """
        Calculate Cycle Time - time from work starting to completion.

        Cycle time = Time from 'In Progress' to 'Done/Resolved'
        This is different from lead time which starts from ticket creation.

        Args:
            enriched_issues: Optional pre-fetched issues with changelog data to avoid re-fetching
        """
        if enriched_issues is None:
            enriched_issues = self.get_issues_with_changelog(projects, start_date, end_date, team, assignee)

        cycle_times = []
        issues_with_times = []

        for issue in enriched_issues:
            in_progress = issue["in_progress_date"]
            resolved = issue["resolved"]

            in_progress_dt = datetime.strptime(in_progress[:19], "%Y-%m-%dT%H:%M:%S")
            resolved_dt = datetime.strptime(resolved[:19], "%Y-%m-%dT%H:%M:%S")
            cycle_time_hours = (resolved_dt - in_progress_dt).total_seconds() / 3600

            # Ensure non-negative (in case of data issues)
            cycle_time_hours = max(0, cycle_time_hours)
            cycle_times.append(cycle_time_hours)

            issues_with_times.append({
                "key": issue["key"],
                "summary": issue["summary"],
                "assignee": issue["assignee"],
                "cycle_time_hours": round(cycle_time_hours, 2),
                "cycle_time_days": round(cycle_time_hours / 24, 2),
                "in_progress_date": in_progress[:10],
                "resolved_date": resolved[:10]
            })

        if not cycle_times:
            return {
                "mean_cycle_time_hours": 0,
                "mean_cycle_time_days": 0,
                "median_cycle_time_hours": 0,
                "median_cycle_time_days": 0,
                "p85_cycle_time_hours": 0,
                "p85_cycle_time_days": 0,
                "p95_cycle_time_hours": 0,
                "p95_cycle_time_days": 0,
                "sample_size": 0,
                "issues": []
            }

        mean_hours = statistics.mean(cycle_times)
        median_hours = statistics.median(cycle_times)
        sorted_times = sorted(cycle_times)
        p85_hours = sorted_times[int(len(cycle_times) * 0.85)] if len(cycle_times) > 0 else 0
        p95_hours = sorted_times[int(len(cycle_times) * 0.95)] if len(cycle_times) > 0 else 0

        return {
            "mean_cycle_time_hours": round(mean_hours, 2),
            "mean_cycle_time_days": round(mean_hours / 24, 2),
            "median_cycle_time_hours": round(median_hours, 2),
            "median_cycle_time_days": round(median_hours / 24, 2),
            "p85_cycle_time_hours": round(p85_hours, 2),
            "p85_cycle_time_days": round(p85_hours / 24, 2),
            "p95_cycle_time_hours": round(p95_hours, 2),
            "p95_cycle_time_days": round(p95_hours / 24, 2),
            "sample_size": len(cycle_times),
            "issues": issues_with_times
        }

    def calculate_lead_time(self, projects: List[str], start_date: str, end_date: str,
                           team: Optional[str] = None, assignee: Optional[str] = None,
                           enriched_issues: Optional[List[Dict]] = None) -> Dict:
        """
        Calculate Lead Time for Changes.

        Lead time = Time from ticket creation to resolution
        This measures the total time from when work was requested to when it was delivered.

        Args:
            enriched_issues: Optional pre-fetched issues to avoid re-fetching
        """
        if enriched_issues is None:
            enriched_issues = self.get_issues_with_changelog(projects, start_date, end_date, team, assignee)

        lead_times = []
        issues_with_times = []

        for issue in enriched_issues:
            created = issue["created"]
            resolved = issue["resolved"]

            created_dt = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            resolved_dt = datetime.strptime(resolved[:19], "%Y-%m-%dT%H:%M:%S")
            lead_time_hours = (resolved_dt - created_dt).total_seconds() / 3600

            # Ensure non-negative
            lead_time_hours = max(0, lead_time_hours)
            lead_times.append(lead_time_hours)

            issues_with_times.append({
                "key": issue["key"],
                "summary": issue["summary"],
                "assignee": issue["assignee"],
                "lead_time_hours": round(lead_time_hours, 2),
                "lead_time_days": round(lead_time_hours / 24, 2),
                "created_date": created[:10],
                "resolved_date": resolved[:10]
            })

        if not lead_times:
            return {
                "mean_lead_time_hours": 0,
                "mean_lead_time_days": 0,
                "median_lead_time_hours": 0,
                "median_lead_time_days": 0,
                "p85_lead_time_hours": 0,
                "p85_lead_time_days": 0,
                "p95_lead_time_hours": 0,
                "p95_lead_time_days": 0,
                "sample_size": 0,
                "rating": "No data",
                "issues": []
            }

        mean_hours = statistics.mean(lead_times)
        median_hours = statistics.median(lead_times)
        sorted_times = sorted(lead_times)
        p85_hours = sorted_times[int(len(lead_times) * 0.85)] if len(lead_times) > 0 else 0
        p95_hours = sorted_times[int(len(lead_times) * 0.95)] if len(lead_times) > 0 else 0

        return {
            "mean_lead_time_hours": round(mean_hours, 2),
            "mean_lead_time_days": round(mean_hours / 24, 2),
            "median_lead_time_hours": round(median_hours, 2),
            "median_lead_time_days": round(median_hours / 24, 2),
            "p85_lead_time_hours": round(p85_hours, 2),
            "p85_lead_time_days": round(p85_hours / 24, 2),
            "p95_lead_time_hours": round(p95_hours, 2),
            "p95_lead_time_days": round(p95_hours / 24, 2),
            "sample_size": len(lead_times),
            "rating": self._rate_lead_time(mean_hours / 24),
            "issues": issues_with_times
        }
    
    def calculate_mttr(self, projects: List[str], start_date: str, end_date: str) -> Dict:
        """
        Calculate Mean Time to Recovery (MTTR).
        
        MTTR = Time from incident detection to resolution
        Focus on high-priority bugs and production incidents
        """
        jql = f"""
            project in ({','.join(projects)}) 
            AND resolutiondate >= '{start_date}' 
            AND resolutiondate <= '{end_date}'
            AND (priority in (Highest, High, Critical, Blocker) 
                 OR issuetype = Incident 
                 OR issuetype = Bug)
            AND (labels in (production, prod, incident, outage, critical)
                 OR priority in (Highest, Critical, Blocker))
        """
        
        incidents = self.search_issues(jql)
        recovery_times = []
        
        for issue in incidents:
            created = issue["fields"].get("created")
            resolved = issue["fields"].get("resolutiondate")
            
            if created and resolved:
                created_dt = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                resolved_dt = datetime.strptime(resolved[:19], "%Y-%m-%dT%H:%M:%S")
                recovery_hours = (resolved_dt - created_dt).total_seconds() / 3600
                recovery_times.append(recovery_hours)
        
        if not recovery_times:
            return {
                "mean_mttr_hours": 0,
                "mean_mttr_days": 0,
                "median_mttr_hours": 0,
                "median_mttr_days": 0,
                "incident_count": 0,
                "rating": "No incidents"
            }
        
        mean_hours = statistics.mean(recovery_times)
        median_hours = statistics.median(recovery_times)
        
        return {
            "mean_mttr_hours": round(mean_hours, 2),
            "mean_mttr_days": round(mean_hours / 24, 2),
            "median_mttr_hours": round(median_hours, 2),
            "median_mttr_days": round(median_hours / 24, 2),
            "incident_count": len(recovery_times),
            "rating": self._rate_mttr(mean_hours)
        }
    
    def calculate_change_failure_rate(self, projects: List[str], start_date: str, end_date: str) -> Dict:
        """
        Calculate Change Failure Rate.
        
        CFR = (Failed deployments / Total deployments) * 100
        Failed deployment = High/Critical bug or incident shortly after deployment
        """
        # Get all deployments
        deployment_jql = f"""
            project in ({','.join(projects)}) 
            AND resolutiondate >= '{start_date}' 
            AND resolutiondate <= '{end_date}'
            AND (labels in (deployment, release, prod, production) 
                 OR status in (Released, Deployed))
        """
        deployments = self.search_issues(deployment_jql)
        total_deployments = len(deployments)
        
        # Get failures (high-priority bugs/incidents in the same period)
        failure_jql = f"""
            project in ({','.join(projects)}) 
            AND created >= '{start_date}' 
            AND created <= '{end_date}'
            AND (priority in (Highest, High, Critical, Blocker))
            AND (issuetype in (Bug, Incident, Defect))
            AND (labels in (production, prod, hotfix, rollback, incident))
        """
        failures = self.search_issues(failure_jql)
        failure_count = len(failures)
        
        if total_deployments == 0:
            cfr_percentage = 0
        else:
            cfr_percentage = (failure_count / total_deployments) * 100
        
        return {
            "total_deployments": total_deployments,
            "failed_changes": failure_count,
            "change_failure_rate_percentage": round(cfr_percentage, 2),
            "rating": self._rate_change_failure_rate(cfr_percentage)
        }
    
    def _rate_deployment_frequency(self, per_day: float) -> str:
        """Rate deployment frequency according to DORA standards."""
        if per_day >= 1:
            return "Elite (Multiple per day)"
        elif per_day >= 1/7:
            return "High (Once per day to once per week)"
        elif per_day >= 1/30:
            return "Medium (Once per week to once per month)"
        else:
            return "Low (Less than once per month)"
    
    def _rate_lead_time(self, days: float) -> str:
        """Rate lead time according to DORA standards."""
        if days < 1:
            return "Elite (Less than one day)"
        elif days <= 7:
            return "High (One day to one week)"
        elif days <= 30:
            return "Medium (One week to one month)"
        else:
            return "Low (More than one month)"
    
    def _rate_mttr(self, hours: float) -> str:
        """Rate MTTR according to DORA standards."""
        if hours < 1:
            return "Elite (Less than one hour)"
        elif hours <= 24:
            return "High (Less than one day)"
        elif hours <= 168:  # One week
            return "Medium (Less than one week)"
        else:
            return "Low (More than one week)"
    
    def _rate_change_failure_rate(self, percentage: float) -> str:
        """Rate change failure rate according to DORA standards."""
        if percentage <= 15:
            return "Elite (0-15%)"
        elif percentage <= 30:
            return "High (16-30%)"
        elif percentage <= 45:
            return "Medium (31-45%)"
        else:
            return "Low (>45%)"

    def get_team_members(self, projects: List[str], start_date: str, end_date: str,
                        team: Optional[str] = None) -> List[str]:
        """
        Get list of unique team members (assignees) for the given period.
        """
        jql_parts = [
            f"project in ({','.join(projects)})",
            f"resolutiondate >= '{start_date}'",
            f"resolutiondate <= '{end_date}'"
        ]

        if team:
            jql_parts.append(f"project = {team}")

        jql = " AND ".join(jql_parts)
        fields = ["assignee"]
        issues = self.search_issues(jql, fields=fields)

        assignees = set()
        for issue in issues:
            assignee = issue["fields"].get("assignee")
            if assignee:
                assignees.add(assignee.get("displayName", "Unknown"))

        return sorted(list(assignees))

    def get_weekly_summary(self, projects: List[str], start_date: str, end_date: str,
                          team: Optional[str] = None, assignee: Optional[str] = None,
                          enriched_issues: Optional[List[Dict]] = None) -> Dict:
        """
        Generate weekly summary of cycle time and lead time.

        Args:
            enriched_issues: Optional pre-fetched issues with changelog data

        Returns:
            Dictionary with weekly breakdowns of metrics
        """
        # Use pre-fetched issues or fetch them
        if enriched_issues is None:
            enriched_issues = self.get_issues_with_changelog(projects, start_date, end_date, team, assignee)

        # Group issues by week
        weekly_data = defaultdict(lambda: {
            "cycle_times": [],
            "lead_times": [],
            "issues": []
        })

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")

        for issue in enriched_issues:
            resolved = issue["resolved"]
            created = issue["created"]
            in_progress = issue["in_progress_date"]

            resolved_dt = datetime.strptime(resolved[:19], "%Y-%m-%dT%H:%M:%S")
            created_dt = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            in_progress_dt = datetime.strptime(in_progress[:19], "%Y-%m-%dT%H:%M:%S")

            # Calculate week number from start date
            days_diff = (resolved_dt - start_dt).days
            week_num = days_diff // 7
            week_start = start_dt + timedelta(weeks=week_num)
            week_end = week_start + timedelta(days=6)
            week_label = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"

            # Calculate times - now properly differentiated!
            # Cycle Time = In Progress -> Resolved (actual work time)
            cycle_time_hours = max(0, (resolved_dt - in_progress_dt).total_seconds() / 3600)
            # Lead Time = Created -> Resolved (total time from request to delivery)
            lead_time_hours = max(0, (resolved_dt - created_dt).total_seconds() / 3600)

            weekly_data[week_label]["cycle_times"].append(cycle_time_hours)
            weekly_data[week_label]["lead_times"].append(lead_time_hours)
            weekly_data[week_label]["issues"].append({
                "key": issue["key"],
                "summary": issue["summary"],
                "assignee": issue["assignee"],
                "cycle_time_days": round(cycle_time_hours / 24, 2),
                "lead_time_days": round(lead_time_hours / 24, 2),
                "in_progress_date": in_progress[:10],
                "resolved_date": resolved[:10]
            })

        # Calculate weekly statistics
        weekly_summary = {}
        for week, data in sorted(weekly_data.items()):
            cycle_times = data["cycle_times"]
            lead_times = data["lead_times"]

            # Calculate P85 for cycle times
            sorted_cycle = sorted(cycle_times) if cycle_times else []
            p85_cycle = sorted_cycle[int(len(cycle_times) * 0.85)] if cycle_times else 0

            # Calculate P85 for lead times
            sorted_lead = sorted(lead_times) if lead_times else []
            p85_lead = sorted_lead[int(len(lead_times) * 0.85)] if lead_times else 0

            weekly_summary[week] = {
                "cycle_time": {
                    "mean_hours": round(statistics.mean(cycle_times), 2) if cycle_times else 0,
                    "mean_days": round(statistics.mean(cycle_times) / 24, 2) if cycle_times else 0,
                    "median_hours": round(statistics.median(cycle_times), 2) if cycle_times else 0,
                    "median_days": round(statistics.median(cycle_times) / 24, 2) if cycle_times else 0,
                    "p85_hours": round(p85_cycle, 2),
                    "p85_days": round(p85_cycle / 24, 2),
                },
                "lead_time": {
                    "mean_hours": round(statistics.mean(lead_times), 2) if lead_times else 0,
                    "mean_days": round(statistics.mean(lead_times) / 24, 2) if lead_times else 0,
                    "median_hours": round(statistics.median(lead_times), 2) if lead_times else 0,
                    "median_days": round(statistics.median(lead_times) / 24, 2) if lead_times else 0,
                    "p85_hours": round(p85_lead, 2),
                    "p85_days": round(p85_lead / 24, 2),
                },
                "issue_count": len(data["issues"]),
                "issues": data["issues"]
            }

        return {
            "weeks": weekly_summary,
            "total_issues": sum(len(data["issues"]) for data in weekly_data.values())
        }
    
    def generate_report(self, projects: List[str], start_date: str, end_date: str) -> Dict:
        """Generate complete DORA metrics report."""
        print(f"Calculating DORA metrics for projects: {', '.join(projects)}")
        print(f"Period: {start_date} to {end_date}\n")
        
        deployment_freq = self.calculate_deployment_frequency(projects, start_date, end_date)
        lead_time = self.calculate_lead_time(projects, start_date, end_date)
        mttr = self.calculate_mttr(projects, start_date, end_date)
        change_failure = self.calculate_change_failure_rate(projects, start_date, end_date)
        
        report = {
            "metadata": {
                "projects": projects,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.now().isoformat()
            },
            "deployment_frequency": deployment_freq,
            "lead_time_for_changes": lead_time,
            "mean_time_to_recovery": mttr,
            "change_failure_rate": change_failure
        }
        
        return report
    
    def generate_team_performance_report(self, projects: List[str], start_date: str, end_date: str,
                                         teams: Optional[List[str]] = None) -> Dict:
        """
        Generate comprehensive team performance report with weekly summaries and drill-downs.

        Args:
            projects: List of project keys
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            teams: Optional list of specific teams to analyze (e.g., ['SAOP', 'SAOP2'])

        Returns:
            Comprehensive report with overall, team, and individual metrics
        """
        print(f"Generating team performance report...")
        print(f"Period: {start_date} to {end_date}\n")

        report = {
            "metadata": {
                "projects": projects,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.now().isoformat()
            },
            "overall": {},
            "by_team": {},
            "by_team_member": {}
        }

        # Overall metrics - fetch all issues with changelog once
        print("Fetching all issues with changelog data (this may take a while)...")
        all_enriched_issues = self.get_issues_with_changelog(projects, start_date, end_date)
        print(f"  Fetched {len(all_enriched_issues)} issues total.\n")

        print("Calculating overall metrics...")
        report["overall"]["weekly_summary"] = self.get_weekly_summary(projects, start_date, end_date, enriched_issues=all_enriched_issues)
        report["overall"]["cycle_time"] = self.calculate_cycle_time(projects, start_date, end_date, enriched_issues=all_enriched_issues)
        report["overall"]["lead_time"] = self.calculate_lead_time(projects, start_date, end_date, enriched_issues=all_enriched_issues)

        # Team-level metrics
        if teams:
            for team in teams:
                print(f"Calculating metrics for team: {team}...")
                # Filter enriched issues for this team
                team_issues = [i for i in all_enriched_issues if i["key"].startswith(f"{team}-")]

                report["by_team"][team] = {
                    "weekly_summary": self.get_weekly_summary([team], start_date, end_date, team=team, enriched_issues=team_issues),
                    "cycle_time": self.calculate_cycle_time([team], start_date, end_date, team=team, enriched_issues=team_issues),
                    "lead_time": self.calculate_lead_time([team], start_date, end_date, team=team, enriched_issues=team_issues),
                    "team_members": list(set(i["assignee"] for i in team_issues if i["assignee"] != "Unassigned"))
                }
                report["by_team"][team]["team_members"].sort()

                # Per team member in this team
                team_members = report["by_team"][team]["team_members"]
                report["by_team"][team]["members"] = {}

                for member in team_members:
                    print(f"  Calculating metrics for {member}...")
                    # Filter for this member
                    member_issues = [i for i in team_issues if i["assignee"] == member]
                    report["by_team"][team]["members"][member] = {
                        "weekly_summary": self.get_weekly_summary([team], start_date, end_date, team=team, assignee=member, enriched_issues=member_issues),
                        "cycle_time": self.calculate_cycle_time([team], start_date, end_date, team=team, assignee=member, enriched_issues=member_issues),
                        "lead_time": self.calculate_lead_time([team], start_date, end_date, team=team, assignee=member, enriched_issues=member_issues)
                    }
        else:
            # If no specific teams, get all team members across all projects
            print("Calculating per-member metrics...")
            team_members = list(set(i["assignee"] for i in all_enriched_issues if i["assignee"] != "Unassigned"))
            team_members.sort()

            for member in team_members:
                print(f"  Calculating metrics for {member}...")
                member_issues = [i for i in all_enriched_issues if i["assignee"] == member]
                report["by_team_member"][member] = {
                    "weekly_summary": self.get_weekly_summary(projects, start_date, end_date, assignee=member, enriched_issues=member_issues),
                    "cycle_time": self.calculate_cycle_time(projects, start_date, end_date, assignee=member, enriched_issues=member_issues),
                    "lead_time": self.calculate_lead_time(projects, start_date, end_date, assignee=member, enriched_issues=member_issues)
                }

        # Calculate last week average for SAOP and SAOP2
        if teams and "SAOP" in report["by_team"] and "SAOP2" in report["by_team"]:
            saop_weeks = report["by_team"]["SAOP"].get("weekly_summary", {}).get("weeks", {})
            saop2_weeks = report["by_team"]["SAOP2"].get("weekly_summary", {}).get("weeks", {})

            if saop_weeks and saop2_weeks:
                # Get the most recent week (last key in ordered dict)
                last_week = list(saop_weeks.keys())[-1]

                if last_week in saop_weeks and last_week in saop2_weeks:
                    saop_lead = saop_weeks[last_week]["lead_time"]["mean_days"]
                    saop2_lead = saop2_weeks[last_week]["lead_time"]["mean_days"]
                    saop_cycle = saop_weeks[last_week]["cycle_time"]["mean_days"]
                    saop2_cycle = saop2_weeks[last_week]["cycle_time"]["mean_days"]

                    report["last_week_average"] = {
                        "period": last_week,
                        "teams": ["SAOP", "SAOP2"],
                        "lead_time": {
                            "SAOP_days": saop_lead,
                            "SAOP2_days": saop2_lead,
                            "average_days": round((saop_lead + saop2_lead) / 2, 2)
                        },
                        "cycle_time": {
                            "SAOP_days": saop_cycle,
                            "SAOP2_days": saop2_cycle,
                            "average_days": round((saop_cycle + saop2_cycle) / 2, 2)
                        }
                    }

        return report

    def _print_ticket_details(self, cycle_data: Dict, lead_data: Dict):
        """Print individual ticket lead and cycle times."""
        # Build lookup from lead_time issues by key
        lead_by_key = {}
        for issue in lead_data.get("issues", []):
            lead_by_key[issue["key"]] = issue

        cycle_issues = cycle_data.get("issues", [])
        if not cycle_issues:
            print("    No tickets found.")
            return

        # Print header
        print(f"    {'Ticket':<14} {'Assignee':<22} {'Cycle (d)':>10} {'Lead (d)':>10}  Summary")
        print(f"    {'─' * 14} {'─' * 22} {'─' * 10} {'─' * 10}  {'─' * 40}")

        for issue in sorted(cycle_issues, key=lambda x: x["cycle_time_days"], reverse=True):
            key = issue["key"]
            lead_issue = lead_by_key.get(key, {})
            lead_days = lead_issue.get("lead_time_days", "N/A")
            summary = issue["summary"][:50]
            print(f"    {key:<14} {issue['assignee']:<22} {issue['cycle_time_days']:>10} {lead_days:>10}  {summary}")

    def print_team_performance_report(self, report: Dict, detailed: bool = False):
        """Print formatted team performance report."""
        print("\n" + "=" * 100)
        print("TEAM PERFORMANCE REPORT")
        print("=" * 100)
        print(f"\nProjects: {', '.join(report['metadata']['projects'])}")
        print(f"Period: {report['metadata']['start_date']} to {report['metadata']['end_date']}")
        print(f"Generated: {report['metadata']['generated_at']}\n")

        # Overall Weekly Summary
        print("=" * 100)
        print("OVERALL WEEKLY SUMMARY")
        print("=" * 100)
        weekly = report["overall"]["weekly_summary"]["weeks"]
        for week, data in weekly.items():
            print(f"\n{week}")
            print("-" * 100)
            print(f"  Issues Completed: {data['issue_count']}")
            print(f"  Cycle Time - Mean: {data['cycle_time']['mean_days']}d, P50: {data['cycle_time']['median_days']}d, P85: {data['cycle_time']['p85_days']}d")
            print(f"  Lead Time  - Mean: {data['lead_time']['mean_days']}d, P50: {data['lead_time']['median_days']}d, P85: {data['lead_time']['p85_days']}d")

        # Overall Summary
        print("\n" + "=" * 100)
        print("OVERALL SUMMARY")
        print("=" * 100)
        overall_cycle = report["overall"]["cycle_time"]
        overall_lead = report["overall"]["lead_time"]
        print(f"\nTotal Issues: {overall_cycle['sample_size']}")
        print(f"Cycle Time - Mean: {overall_cycle['mean_cycle_time_days']}d, P50: {overall_cycle['median_cycle_time_days']}d, P85: {overall_cycle['p85_cycle_time_days']}d")
        print(f"Lead Time  - Mean: {overall_lead['mean_lead_time_days']}d, P50: {overall_lead['median_lead_time_days']}d, P85: {overall_lead['p85_lead_time_days']}d")

        if detailed:
            print(f"\n  All Tickets:")
            self._print_ticket_details(overall_cycle, overall_lead)

        # Team Drill-down
        if report["by_team"]:
            print("\n" + "=" * 100)
            print("TEAM BREAKDOWN")
            print("=" * 100)

            for team, team_data in report["by_team"].items():
                print(f"\n{'-' * 100}")
                print(f"TEAM: {team}")
                print(f"{'-' * 100}")

                team_cycle = team_data["cycle_time"]
                team_lead = team_data["lead_time"]

                print(f"\nTeam Summary:")
                print(f"  Issues Completed: {team_cycle['sample_size']}")
                print(f"  Cycle Time - Mean: {team_cycle['mean_cycle_time_days']}d, P50: {team_cycle['median_cycle_time_days']}d, P85: {team_cycle['p85_cycle_time_days']}d")
                print(f"  Lead Time  - Mean: {team_lead['mean_lead_time_days']}d, P50: {team_lead['median_lead_time_days']}d, P85: {team_lead['p85_lead_time_days']}d")

                if detailed:
                    print(f"\n  Team Tickets:")
                    self._print_ticket_details(team_cycle, team_lead)

                # Weekly breakdown for team
                print(f"\nWeekly Breakdown:")
                team_weekly = team_data["weekly_summary"]["weeks"]
                for week, data in team_weekly.items():
                    print(f"  {week}: {data['issue_count']} issues | " +
                          f"Cycle: {data['cycle_time']['mean_days']}d | " +
                          f"Lead: {data['lead_time']['mean_days']}d")

                # Team member breakdown
                print(f"\nTeam Member Performance:")
                for member, member_data in team_data["members"].items():
                    member_cycle = member_data["cycle_time"]
                    member_lead = member_data["lead_time"]
                    print(f"  {member}:")
                    print(f"    Issues: {member_cycle['sample_size']}")
                    print(f"    Cycle Time - Mean: {member_cycle['mean_cycle_time_days']}d, P50: {member_cycle['median_cycle_time_days']}d, P85: {member_cycle['p85_cycle_time_days']}d")
                    print(f"    Lead Time  - Mean: {member_lead['mean_lead_time_days']}d, P50: {member_lead['median_lead_time_days']}d, P85: {member_lead['p85_lead_time_days']}d")

                    if detailed:
                        self._print_ticket_details(member_cycle, member_lead)

        # Individual contributors (if no team breakdown)
        elif report["by_team_member"]:
            print("\n" + "=" * 100)
            print("INDIVIDUAL PERFORMANCE")
            print("=" * 100)

            for member, member_data in report["by_team_member"].items():
                member_cycle = member_data["cycle_time"]
                member_lead = member_data["lead_time"]
                print(f"\n{member}:")
                print(f"  Issues: {member_cycle['sample_size']}")
                print(f"  Cycle Time - Mean: {member_cycle['mean_cycle_time_days']}d, P50: {member_cycle['median_cycle_time_days']}d, P85: {member_cycle['p85_cycle_time_days']}d")
                print(f"  Lead Time  - Mean: {member_lead['mean_lead_time_days']}d, P50: {member_lead['median_lead_time_days']}d, P85: {member_lead['p85_lead_time_days']}d")

                if detailed:
                    self._print_ticket_details(member_cycle, member_lead)

        # Last week average for SAOP and SAOP2
        if "last_week_average" in report:
            print("\n" + "=" * 100)
            print("LAST WEEK AVERAGE (SAOP + SAOP2) / 2")
            print("=" * 100)
            lwa = report["last_week_average"]
            print(f"\nPeriod: {lwa['period']}")
            print(f"\nLead Time:")
            print(f"  SAOP:    {lwa['lead_time']['SAOP_days']} days")
            print(f"  SAOP2:   {lwa['lead_time']['SAOP2_days']} days")
            print(f"  Average: {lwa['lead_time']['average_days']} days")
            print(f"\nCycle Time:")
            print(f"  SAOP:    {lwa['cycle_time']['SAOP_days']} days")
            print(f"  SAOP2:   {lwa['cycle_time']['SAOP2_days']} days")
            print(f"  Average: {lwa['cycle_time']['average_days']} days")

        print("\n" + "=" * 100)

    def print_report(self, report: Dict):
        """Print a formatted DORA metrics report."""
        print("=" * 80)
        print("DORA METRICS REPORT")
        print("=" * 80)
        print(f"\nProjects: {', '.join(report['metadata']['projects'])}")
        print(f"Period: {report['metadata']['start_date']} to {report['metadata']['end_date']}")
        print(f"Generated: {report['metadata']['generated_at']}\n")

        print("-" * 80)
        print("1. DEPLOYMENT FREQUENCY")
        print("-" * 80)
        df = report['deployment_frequency']
        print(f"Total Deployments: {df['total_deployments']}")
        print(f"Per Day: {df['deployments_per_day']}")
        print(f"Per Week: {df['deployments_per_week']}")
        print(f"Per Month: {df['deployments_per_month']}")
        print(f"Rating: {df['rating']}\n")

        print("-" * 80)
        print("2. LEAD TIME FOR CHANGES")
        print("-" * 80)
        lt = report['lead_time_for_changes']
        print(f"Mean: {lt['mean_lead_time_days']} days ({lt['mean_lead_time_hours']} hours)")
        print(f"Median: {lt['median_lead_time_days']} days ({lt['median_lead_time_hours']} hours)")
        print(f"95th Percentile: {lt['p95_lead_time_days']} days")
        print(f"Sample Size: {lt['sample_size']} issues")
        print(f"Rating: {lt['rating']}\n")

        print("-" * 80)
        print("3. MEAN TIME TO RECOVERY (MTTR)")
        print("-" * 80)
        mttr = report['mean_time_to_recovery']
        print(f"Mean: {mttr['mean_mttr_days']} days ({mttr['mean_mttr_hours']} hours)")
        print(f"Median: {mttr['median_mttr_days']} days ({mttr['median_mttr_hours']} hours)")
        print(f"Incidents: {mttr['incident_count']}")
        print(f"Rating: {mttr['rating']}\n")

        print("-" * 80)
        print("4. CHANGE FAILURE RATE")
        print("-" * 80)
        cfr = report['change_failure_rate']
        print(f"Total Deployments: {cfr['total_deployments']}")
        print(f"Failed Changes: {cfr['failed_changes']}")
        print(f"Failure Rate: {cfr['change_failure_rate_percentage']}%")
        print(f"Rating: {cfr['rating']}\n")

        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Calculate JIRA metrics for team performance")
    parser.add_argument("--jira-url", required=True, help="JIRA instance URL (e.g., https://yourcompany.atlassian.net)")
    parser.add_argument("--email", required=True, help="Atlassian account email")
    parser.add_argument("--api-token", required=True, help="Atlassian API token")
    parser.add_argument("--projects", default="IA,DATA,SAOP,SAOP2",
                       help="Comma-separated project keys (default: IA,DATA,SAOP,SAOP2)")
    parser.add_argument("--start-date",
                       help="Start date in YYYY-MM-DD format (default: 12 weeks ago)")
    parser.add_argument("--end-date",
                       help="End date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--teams",
                       help="Comma-separated team names for drill-down (e.g., SAOP,SAOP2)")
    parser.add_argument("--mode", default="team-performance",
                       choices=["team-performance", "dora"],
                       help="Report mode: team-performance (default) or dora")
    parser.add_argument("--output", help="Output JSON file path (optional)")
    parser.add_argument("--detailed", action="store_true",
                       help="Show individual ticket lead and cycle times")

    args = parser.parse_args()

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

    # Initialize calculator
    jira_url = args.jira_url.rstrip('/')
    calculator = JiraDORAMetrics(jira_url, args.email, args.api_token)

    # Generate and print report based on mode
    if args.mode == "team-performance":
        report = calculator.generate_team_performance_report(projects, start_date, end_date, teams)
        calculator.print_team_performance_report(report, detailed=args.detailed)
    else:  # dora mode
        report = calculator.generate_report(projects, start_date, end_date)
        calculator.print_report(report)

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()