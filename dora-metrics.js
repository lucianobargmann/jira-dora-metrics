#!/usr/bin/env node

/**
 * DORA Metrics Script
 * Fetches Jira issues and calculates cycle time, lead time metrics
 * Then sends a formatted report to Slack
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// Load .env file
function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        const value = valueParts.join('=').replace(/^["']|["']$/g, '');
        if (key && !process.env[key]) {
          process.env[key] = value;
        }
      }
    }
  }
}

loadEnv();

// Configuration
const CONFIG = {
  jira: {
    host: process.env.JIRA_HOST || 'ninjio.atlassian.net',
    email: process.env.JIRA_EMAIL,
    apiToken: process.env.JIRA_API_TOKEN,
  },
  slack: {
    webhookUrl: process.env.SLACK_WEBHOOK_URL,
  },
  projects: ['IA', 'DATA', 'SAOP', 'SAOP2'],
  issueTypes: ['Bug', 'Story', 'Task'],
  activeStatuses: ['IN PROGRESS', 'DEV IN PROGRESS', 'IN REVIEW'],
};

// Helper: Calculate previous work week (Monday to Sunday)
function calculatePreviousWeek() {
  const today = new Date();
  const currentDay = today.getDay();

  // Calculate days to subtract to get to last Sunday
  const daysToLastSunday = currentDay === 0 ? 7 : currentDay;

  // Get last Sunday (end of previous week)
  const lastSunday = new Date(today);
  lastSunday.setDate(today.getDate() - daysToLastSunday);

  // Get last Monday (start of previous week)
  const lastMonday = new Date(lastSunday);
  lastMonday.setDate(lastSunday.getDate() - 6);

  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  return {
    startDate: formatDate(lastMonday),
    endDate: formatDate(lastSunday),
  };
}

// Helper: Calculate time between two dates in hours
function getHoursBetween(start, end) {
  return (new Date(end) - new Date(start)) / (1000 * 60 * 60);
}

// Helper: Calculate lead time from changelog
function calculateLeadTime(changelog) {
  if (!changelog || !changelog.histories) return 0;

  let totalHours = 0;
  let currentStatus = null;
  let statusStartTime = null;

  // Sort histories by created date
  const histories = changelog.histories.sort(
    (a, b) => new Date(a.created) - new Date(b.created)
  );

  for (const history of histories) {
    const statusChange = history.items.find((item) => item.field === 'status');

    if (statusChange) {
      // If we were tracking a status, calculate time spent
      if (currentStatus && CONFIG.activeStatuses.includes(currentStatus.toUpperCase())) {
        totalHours += getHoursBetween(statusStartTime, history.created);
      }

      // Update current status
      currentStatus = statusChange.toString;
      statusStartTime = history.created;
    }
  }

  // If still in active status, count time until now
  if (currentStatus && CONFIG.activeStatuses.includes(currentStatus.toUpperCase())) {
    totalHours += getHoursBetween(statusStartTime, new Date());
  }

  return totalHours;
}

// Helper: Calculate percentile
function percentile(arr, p) {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index % 1;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

// Fetch issues from Jira
async function fetchJiraIssues(startDate, endDate) {
  const jql = `status = Done AND project IN (${CONFIG.projects.join(', ')}) AND resolutiondate >= "${startDate}" AND resolutiondate <= "${endDate}" AND type IN (${CONFIG.issueTypes.join(', ')}) ORDER BY resolutiondate DESC`;

  const params = new URLSearchParams({
    jql,
    maxResults: '100',
    fields: 'key,summary,created,resolutiondate,issuetype,priority,status',
    expand: 'changelog',
  });

  const auth = Buffer.from(
    `${CONFIG.jira.email}:${CONFIG.jira.apiToken}`
  ).toString('base64');

  return new Promise((resolve, reject) => {
    const options = {
      hostname: CONFIG.jira.host,
      path: `/rest/api/3/search/jql?${params.toString()}`,
      method: 'GET',
      headers: {
        Authorization: `Basic ${auth}`,
        Accept: 'application/json',
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(JSON.parse(data));
        } else {
          reject(new Error(`Jira API error: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

// Calculate metrics for issues
function calculateMetrics(issues, weekInfo) {
  const metricsData = issues.map((issue) => {
    const created = issue.fields.created;
    const resolved = issue.fields.resolutiondate;
    const project = issue.key.split('-')[0];
    const cycleTime = getHoursBetween(created, resolved);

    let leadTime = calculateLeadTime(issue.changelog);

    // Penalty: If lead time is 0, they skipped workflow - penalize with full cycle time
    const workflowViolation = leadTime === 0;
    if (workflowViolation) {
      leadTime = cycleTime;
    }

    return {
      key: issue.key,
      project,
      summary: issue.fields.summary,
      issueType: issue.fields.issuetype.name,
      priority: issue.fields.priority.name,
      created,
      resolved,
      cycleTime,
      cycleTimeDays: (cycleTime / 24).toFixed(1),
      leadTime,
      leadTimeDays: (leadTime / 24).toFixed(1),
      efficiency: leadTime > 0 ? ((leadTime / cycleTime) * 100).toFixed(1) : 0,
      workflowViolation,
    };
  });

  // Calculate overall statistics
  const cycleTimes = metricsData.map((m) => m.cycleTime);
  const leadTimes = metricsData.map((m) => m.leadTime);

  const avgCycleTime = cycleTimes.reduce((a, b) => a + b, 0) / cycleTimes.length || 0;
  const avgLeadTime = leadTimes.reduce((a, b) => a + b, 0) / leadTimes.length || 0;

  // Count workflow violations
  const workflowViolations = metricsData.filter((m) => m.workflowViolation);

  // Group by issue type
  const byIssueType = metricsData.reduce((acc, item) => {
    if (!acc[item.issueType]) {
      acc[item.issueType] = { count: 0, totalCycleTime: 0, totalLeadTime: 0 };
    }
    acc[item.issueType].count++;
    acc[item.issueType].totalCycleTime += item.cycleTime;
    acc[item.issueType].totalLeadTime += item.leadTime;
    return acc;
  }, {});

  // Group by project
  const byProject = metricsData.reduce((acc, item) => {
    if (!acc[item.project]) {
      acc[item.project] = {
        count: 0,
        totalCycleTime: 0,
        totalLeadTime: 0,
        cycleTimes: [],
        leadTimes: [],
        workflowViolations: 0,
      };
    }
    acc[item.project].count++;
    acc[item.project].totalCycleTime += item.cycleTime;
    acc[item.project].totalLeadTime += item.leadTime;
    acc[item.project].cycleTimes.push(item.cycleTime);
    acc[item.project].leadTimes.push(item.leadTime);
    if (item.workflowViolation) {
      acc[item.project].workflowViolations++;
    }
    return acc;
  }, {});

  // Get top 5 longest lead times
  const topLeadTimes = [...metricsData]
    .sort((a, b) => b.leadTime - a.leadTime)
    .slice(0, 5);

  return {
    metricsData,
    cycleTimes,
    leadTimes,
    avgCycleTime,
    avgLeadTime,
    workflowViolations,
    byIssueType,
    byProject,
    topLeadTimes,
  };
}

// Format Slack message
function formatSlackMessage(metrics, weekInfo, issueCount) {
  const {
    cycleTimes,
    leadTimes,
    avgCycleTime,
    avgLeadTime,
    workflowViolations,
    byIssueType,
    byProject,
    topLeadTimes,
  } = metrics;

  const violationWarning =
    workflowViolations.length > 0
      ? `\n⚠️ *Workflow Violations: ${workflowViolations.length} issues*\n_Issues moved directly to DONE without proper workflow (lead time = cycle time penalty applied)_\n${workflowViolations
          .slice(0, 5)
          .map(
            (item) =>
              `• <https://ninjio.atlassian.net/browse/${item.key}|${item.key}> (${item.project})`
          )
          .join('\n')}${workflowViolations.length > 5 ? `\n_...and ${workflowViolations.length - 5} more_` : ''}\n`
      : '';

  return `
📊 *Weekly DORA Metrics Report*
_Period: ${weekInfo.startDate} to ${weekInfo.endDate}_

*📈 Overall Metrics*
- Issues Completed: *${issueCount}*
- Avg Cycle Time: *${(avgCycleTime / 24).toFixed(1)} days* (${avgCycleTime.toFixed(1)}h)
- Avg Lead Time: *${(avgLeadTime / 24).toFixed(1)} days* (${avgLeadTime.toFixed(1)}h)
- Active Work Ratio: *${((avgLeadTime / avgCycleTime) * 100 || 0).toFixed(1)}%*

*⏱️ Cycle Time Distribution*
- Median: ${(percentile(cycleTimes, 50) / 24).toFixed(1)} days
- P75: ${(percentile(cycleTimes, 75) / 24).toFixed(1)} days
- P95: ${(percentile(cycleTimes, 95) / 24).toFixed(1)} days

*🔄 Lead Time Distribution*
- Median: ${(percentile(leadTimes, 50) / 24).toFixed(1)} days
- P75: ${(percentile(leadTimes, 75) / 24).toFixed(1)} days
- P95: ${(percentile(leadTimes, 95) / 24).toFixed(1)} days

*🎯 By Project*
${Object.entries(byProject)
  .sort((a, b) => b[1].count - a[1].count)
  .map(([project, stats]) => {
    const avgCycle = (stats.totalCycleTime / stats.count / 24).toFixed(1);
    const avgLead = (stats.totalLeadTime / stats.count / 24).toFixed(1);
    const medianCycle = (percentile(stats.cycleTimes, 50) / 24).toFixed(1);
    const medianLead = (percentile(stats.leadTimes, 50) / 24).toFixed(1);
    const violationNote =
      stats.workflowViolations > 0 ? ` ⚠️ ${stats.workflowViolations} violations` : '';
    return `• *${project}*: ${stats.count} issues${violationNote}
  ├ Avg Cycle: ${avgCycle}d | Median: ${medianCycle}d
  └ Avg Lead: ${avgLead}d | Median: ${medianLead}d`;
  })
  .join('\n')}

*📋 By Issue Type*
${Object.entries(byIssueType)
  .map(([type, stats]) => {
    return `• ${type}: ${stats.count} issues | Avg Cycle: ${(stats.totalCycleTime / stats.count / 24).toFixed(1)}d | Avg Lead: ${(stats.totalLeadTime / stats.count / 24).toFixed(1)}d`;
  })
  .join('\n')}

*🐌 Top 5 Longest Lead Times*
${topLeadTimes
  .map(
    (item, i) =>
      `${i + 1}. <https://ninjio.atlassian.net/browse/${item.key}|${item.key}>: ${item.leadTimeDays}d${item.workflowViolation ? ' ⚠️' : ''} - ${item.summary.substring(0, 50)}${item.summary.length > 50 ? '...' : ''}`
  )
  .join('\n')}
${violationWarning}
`;
}

// Send message to Slack
async function sendToSlack(message) {
  if (!CONFIG.slack.webhookUrl) {
    console.log('No Slack webhook URL configured. Message:');
    console.log(message);
    return;
  }

  const url = new URL(CONFIG.slack.webhookUrl);
  const payload = JSON.stringify({ text: message });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: url.hostname,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
        } else {
          reject(new Error(`Slack API error: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

// Main execution
async function main() {
  try {
    // Validate configuration
    if (!CONFIG.jira.email || !CONFIG.jira.apiToken) {
      console.error('Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables are required');
      process.exit(1);
    }

    // Calculate date range
    const weekInfo = calculatePreviousWeek();
    console.log(`Fetching metrics for: ${weekInfo.startDate} to ${weekInfo.endDate}`);

    // Fetch issues from Jira
    const response = await fetchJiraIssues(weekInfo.startDate, weekInfo.endDate);
    const issues = response.issues || [];
    console.log(`Found ${issues.length} issues`);

    if (issues.length === 0) {
      console.log('No issues found for the specified period');
      return;
    }

    // Calculate metrics
    const metrics = calculateMetrics(issues, weekInfo);

    // Format and send Slack message
    const slackMessage = formatSlackMessage(metrics, weekInfo, issues.length);
    await sendToSlack(slackMessage);

    console.log('Report sent successfully!');

    // Return metrics for programmatic use
    return {
      weekInfo,
      issueCount: issues.length,
      metrics: {
        avgCycleTimeDays: (metrics.avgCycleTime / 24).toFixed(1),
        avgLeadTimeDays: (metrics.avgLeadTime / 24).toFixed(1),
        medianCycleTimeDays: (percentile(metrics.cycleTimes, 50) / 24).toFixed(1),
        medianLeadTimeDays: (percentile(metrics.leadTimes, 50) / 24).toFixed(1),
        workflowViolations: metrics.workflowViolations.length,
        byProject: metrics.byProject,
      },
    };
  } catch (error) {
    console.error('Error running metrics:', error.message);
    process.exit(1);
  }
}

main();
