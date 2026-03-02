/**
 * JIRA Metrics Import for Google Sheets
 *
 * Usage:
 * 1. Open Google Sheets
 * 2. Go to Extensions > Apps Script
 * 3. Paste this code
 * 4. Save and run importMetricsFromCell()
 */

/**
 * Import metrics from RawJSON sheet
 * Cell A1 should contain either:
 *   - A Google Drive file ID (e.g., 1AbCdEfGhIjKlMnOpQrStUvWxYz)
 *   - A Google Drive sharing URL (e.g., https://drive.google.com/file/d/FILE_ID/view)
 *   - Raw JSON content pasted directly
 */
function importMetricsFromCell() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let rawSheet = ss.getSheetByName('RawJSON');
  if (!rawSheet) {
    SpreadsheetApp.getUi().alert('Create a sheet named "RawJSON" and put the file ID or JSON in cell A1');
    return;
  }
  const input = rawSheet.getRange('A1').getValue().trim();
  if (!input) {
    SpreadsheetApp.getUi().alert('Please enter a Google Drive file ID or JSON content in cell A1');
    return;
  }

  let jsonText;

  // Check if it's a Google Drive URL and extract file ID
  let fileId = null;
  const driveUrlMatch = input.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (driveUrlMatch) {
    fileId = driveUrlMatch[1];
  } else if (/^[a-zA-Z0-9_-]{20,}$/.test(input)) {
    // Looks like a file ID (alphanumeric, 20+ chars)
    fileId = input;
  }

  if (fileId) {
    try {
      const file = DriveApp.getFileById(fileId);
      jsonText = file.getBlob().getDataAsString();
    } catch (e) {
      SpreadsheetApp.getUi().alert('Could not access file: ' + e.message + '\n\nMake sure the file exists and you have access to it.');
      return;
    }
  } else {
    // Assume it's raw JSON content
    jsonText = input;
  }

  try {
    const json = JSON.parse(jsonText);
    processMetrics(json);
  } catch (e) {
    SpreadsheetApp.getUi().alert('Failed to parse JSON: ' + e.message);
  }
}

/**
 * Main function to process metrics and create sheets
 */
function processMetrics(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Create Team Rankings sheet
  createTeamRankings(ss, data);

  // Create Individual Rankings sheet (overall)
  createIndividualRankings(ss, data);

  // Create Weekly Trends sheet (overall + per-team weekly sheets)
  createWeeklyTrends(ss, data);

  // Create Weekly Individual Rankings (stack ranked per week)
  createWeeklyIndividualRankings(ss, data);

  SpreadsheetApp.getUi().alert('Import complete! Check the new sheets.');
}

/**
 * Create team-level rankings
 */
function createTeamRankings(ss, data) {
  let sheet = ss.getSheetByName('Team Rankings');
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet('Team Rankings');
  }

  const headers = [
    'Rank', 'Team', 'Issues Completed',
    'Mean Cycle Time (Days)', 'Median Cycle Time (Days)',
    'Mean Lead Time (Days)', 'Median Lead Time (Days)',
    'P95 Cycle Time (Days)'
  ];

  const teams = [];
  const byTeam = data.by_team || {};

  for (const [teamName, teamData] of Object.entries(byTeam)) {
    const cycleTime = teamData.cycle_time || {};
    const leadTime = teamData.lead_time || {};

    teams.push({
      name: teamName,
      issueCount: cycleTime.sample_size || 0,
      meanCycle: cycleTime.mean_cycle_time_days || 0,
      medianCycle: cycleTime.median_cycle_time_days || 0,
      meanLead: leadTime.mean_lead_time_days || 0,
      medianLead: leadTime.median_lead_time_days || 0,
      p95Cycle: cycleTime.p95_cycle_time_days || 0
    });
  }

  // Sort by median cycle time (lower is better)
  teams.sort((a, b) => a.medianCycle - b.medianCycle);

  const rows = [headers];
  teams.forEach((team, idx) => {
    rows.push([
      idx + 1,
      team.name,
      team.issueCount,
      Math.round(team.meanCycle * 100) / 100,
      Math.round(team.medianCycle * 100) / 100,
      Math.round(team.meanLead * 100) / 100,
      Math.round(team.medianLead * 100) / 100,
      Math.round(team.p95Cycle * 100) / 100
    ]);
  });

  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  formatSheet(sheet, headers.length);

  // Add metadata
  const metaRow = rows.length + 2;
  sheet.getRange(metaRow, 1).setValue('Report Period:');
  sheet.getRange(metaRow, 2).setValue(`${data.metadata.start_date} to ${data.metadata.end_date}`);
  sheet.getRange(metaRow + 1, 1).setValue('Generated:');
  sheet.getRange(metaRow + 1, 2).setValue(data.metadata.generated_at);
}

/**
 * Create individual contributor rankings across all teams
 */
function createIndividualRankings(ss, data) {
  let sheet = ss.getSheetByName('Individual Rankings');
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet('Individual Rankings');
  }

  const headers = [
    'Rank', 'Name', 'Team', 'Issues Completed',
    'Mean Cycle Time (Days)', 'Median Cycle Time (Days)',
    'P95 Cycle Time (Days)', 'Score'
  ];

  const individuals = [];
  const byTeam = data.by_team || {};

  for (const [teamName, teamData] of Object.entries(byTeam)) {
    const members = teamData.members || {};

    for (const [memberName, memberData] of Object.entries(members)) {
      if (memberName === 'Unassigned') continue;

      const cycleTime = memberData.cycle_time || {};
      const issueCount = cycleTime.sample_size || 0;

      if (issueCount === 0) continue;

      const meanCycle = cycleTime.mean_cycle_time_days || 0;
      const medianCycle = cycleTime.median_cycle_time_days || 0;
      const p95Cycle = cycleTime.p95_cycle_time_days || 0;

      // Score: weighted combination (lower is better)
      // Prioritizes: throughput (issues), then median cycle time
      const score = (medianCycle * 0.4) + (meanCycle * 0.3) - (issueCount * 0.5);

      individuals.push({
        name: memberName,
        team: teamName,
        issueCount: issueCount,
        meanCycle: meanCycle,
        medianCycle: medianCycle,
        p95Cycle: p95Cycle,
        score: score
      });
    }
  }

  // Sort by score (lower is better - fast + high throughput)
  individuals.sort((a, b) => a.score - b.score);

  const rows = [headers];
  individuals.forEach((person, idx) => {
    rows.push([
      idx + 1,
      person.name,
      person.team,
      person.issueCount,
      Math.round(person.meanCycle * 100) / 100,
      Math.round(person.medianCycle * 100) / 100,
      Math.round(person.p95Cycle * 100) / 100,
      Math.round(person.score * 100) / 100
    ]);
  });

  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  formatSheet(sheet, headers.length);

  // Add scoring explanation
  const metaRow = rows.length + 2;
  sheet.getRange(metaRow, 1).setValue('Score Formula:');
  sheet.getRange(metaRow, 2).setValue('(Median Cycle × 0.4) + (Mean Cycle × 0.3) - (Issue Count × 0.5)');
  sheet.getRange(metaRow + 1, 1).setValue('Lower score = better performance (fast delivery + high throughput)');
}

/**
 * Create weekly trends overview (overall)
 */
function createWeeklyTrends(ss, data) {
  let sheet = ss.getSheetByName('Weekly Trends');
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet('Weekly Trends');
  }

  const headers = [
    'Week', 'Issues Completed',
    'Mean Cycle Time (Days)', 'Median Cycle Time (Days)',
    'Mean Lead Time (Days)', 'Median Lead Time (Days)'
  ];

  const weeks = [];
  const weeklySummary = data.overall?.weekly_summary?.weeks || {};

  for (const [weekRange, weekData] of Object.entries(weeklySummary)) {
    const cycleTime = weekData.cycle_time || {};
    const leadTime = weekData.lead_time || {};

    weeks.push({
      week: weekRange,
      issueCount: weekData.issue_count || 0,
      meanCycle: cycleTime.mean_days || 0,
      medianCycle: cycleTime.median_days || 0,
      meanLead: leadTime.mean_days || 0,
      medianLead: leadTime.median_days || 0
    });
  }

  // Sort by week (chronological)
  weeks.sort((a, b) => a.week.localeCompare(b.week));

  const rows = [headers];
  weeks.forEach(week => {
    rows.push([
      week.week,
      week.issueCount,
      Math.round(week.meanCycle * 100) / 100,
      Math.round(week.medianCycle * 100) / 100,
      Math.round(week.meanLead * 100) / 100,
      Math.round(week.medianLead * 100) / 100
    ]);
  });

  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  formatSheet(sheet, headers.length);

  // Create team weekly sheets
  createTeamWeeklySheets(ss, data);
}

/**
 * Create weekly breakdown sheets per team
 */
function createTeamWeeklySheets(ss, data) {
  const byTeam = data.by_team || {};

  for (const [teamName, teamData] of Object.entries(byTeam)) {
    const sheetName = `${teamName} Weekly`;
    let sheet = ss.getSheetByName(sheetName);
    if (sheet) {
      sheet.clear();
    } else {
      sheet = ss.insertSheet(sheetName);
    }

    const headers = [
      'Week', 'Team Issues',
      'Mean Cycle (Days)', 'Median Cycle (Days)'
    ];

    // Get all unique weeks from team and members
    const allWeeks = new Set();
    const teamWeekly = teamData.weekly_summary?.weeks || {};
    Object.keys(teamWeekly).forEach(w => allWeeks.add(w));

    const members = teamData.members || {};
    for (const memberData of Object.values(members)) {
      const memberWeeks = memberData.weekly_summary?.weeks || {};
      Object.keys(memberWeeks).forEach(w => allWeeks.add(w));
    }

    // Add member columns to headers
    const memberNames = Object.keys(members).filter(n => n !== 'Unassigned');
    memberNames.forEach(name => {
      headers.push(`${name} Issues`);
      headers.push(`${name} Cycle (Days)`);
    });

    const sortedWeeks = Array.from(allWeeks).sort();
    const rows = [headers];

    sortedWeeks.forEach(week => {
      const teamWeekData = teamWeekly[week] || {};
      const teamCycle = teamWeekData.cycle_time || {};

      const row = [
        week,
        teamWeekData.issue_count || 0,
        Math.round((teamCycle.mean_days || 0) * 100) / 100,
        Math.round((teamCycle.median_days || 0) * 100) / 100
      ];

      // Add member data for this week
      memberNames.forEach(name => {
        const memberWeekData = members[name]?.weekly_summary?.weeks?.[week] || {};
        const memberCycle = memberWeekData.cycle_time || {};
        row.push(memberWeekData.issue_count || 0);
        row.push(Math.round((memberCycle.mean_days || 0) * 100) / 100);
      });

      rows.push(row);
    });

    sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
    formatSheet(sheet, headers.length);
  }
}

/**
 * Create individual weekly rankings - stack ranked per week
 */
function createWeeklyIndividualRankings(ss, data) {
  let sheet = ss.getSheetByName('Weekly Individual Rankings');
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet('Weekly Individual Rankings');
  }

  const headers = [
    'Week', 'Rank', 'Name', 'Team', 'Issues Completed',
    'Mean Cycle Time (Days)', 'Median Cycle Time (Days)'
  ];

  const rows = [headers];
  const byTeam = data.by_team || {};

  // Collect all weeks
  const allWeeks = new Set();
  for (const teamData of Object.values(byTeam)) {
    const members = teamData.members || {};
    for (const memberData of Object.values(members)) {
      const weeks = memberData.weekly_summary?.weeks || {};
      Object.keys(weeks).forEach(w => allWeeks.add(w));
    }
  }

  const sortedWeeks = Array.from(allWeeks).sort();

  // For each week, rank individuals
  sortedWeeks.forEach(week => {
    const weeklyPerformers = [];

    for (const [teamName, teamData] of Object.entries(byTeam)) {
      const members = teamData.members || {};

      for (const [memberName, memberData] of Object.entries(members)) {
        if (memberName === 'Unassigned') continue;

        const weekData = memberData.weekly_summary?.weeks?.[week];
        if (!weekData || weekData.issue_count === 0) continue;

        const cycleTime = weekData.cycle_time || {};
        weeklyPerformers.push({
          name: memberName,
          team: teamName,
          issueCount: weekData.issue_count || 0,
          meanCycle: cycleTime.mean_days || 0,
          medianCycle: cycleTime.median_days || 0
        });
      }
    }

    // Sort by issues completed (desc), then by median cycle time (asc)
    weeklyPerformers.sort((a, b) => {
      if (b.issueCount !== a.issueCount) return b.issueCount - a.issueCount;
      return a.medianCycle - b.medianCycle;
    });

    weeklyPerformers.forEach((person, idx) => {
      rows.push([
        week,
        idx + 1,
        person.name,
        person.team,
        person.issueCount,
        Math.round(person.meanCycle * 100) / 100,
        Math.round(person.medianCycle * 100) / 100
      ]);
    });
  });

  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  formatSheet(sheet, headers.length);
}

/**
 * Apply formatting to a sheet
 */
function formatSheet(sheet, numCols) {
  // Format header row
  const headerRange = sheet.getRange(1, 1, 1, numCols);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285f4');
  headerRange.setFontColor('white');

  // Auto-resize columns
  for (let i = 1; i <= numCols; i++) {
    sheet.autoResizeColumn(i);
  }

  // Freeze header row
  sheet.setFrozenRows(1);

  // Add alternating row colors
  const dataRange = sheet.getDataRange();
  const numRows = dataRange.getNumRows();
  for (let i = 2; i <= numRows; i++) {
    if (i % 2 === 0) {
      sheet.getRange(i, 1, 1, numCols).setBackground('#f8f9fa');
    }
  }
}

/**
 * Add custom menu to Google Sheets
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('JIRA Metrics')
    .addItem('Import from RawJSON sheet', 'importMetricsFromCell')
    .addToUi();
}
