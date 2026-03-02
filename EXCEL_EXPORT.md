# Excel Export Guide

The metrics script can now export reports to Excel format with multiple sheets optimized for pivot tables, charts, and analysis.

## Installation

Make sure you have the required packages:

```bash
pip install pandas openpyxl
```

## Usage

### Export to Excel

```bash
# Export directly to Excel
python3 run_with_env.py --teams SAOP,SAOP2 --output report.xlsx

# Or use the --excel flag to auto-generate filename
python3 run_with_env.py --teams SAOP,SAOP2 --excel
```

### Custom date range with Excel export

```bash
python3 run_with_env.py \
  --teams SAOP,SAOP2 \
  --start-date 2024-09-01 \
  --end-date 2024-11-17 \
  --output team_metrics_q4.xlsx
```

## Excel File Structure

The exported Excel file contains 5 sheets:

### 1. Weekly Summary
- **Purpose**: Time series analysis and trend charts
- **Columns**:
  - Week (date range)
  - Issues Completed
  - Cycle Time Mean/Median (days)
  - Lead Time Mean/Median (days)
- **Use for**: Line charts showing trends over time

### 2. Overall Summary
- **Purpose**: High-level KPIs
- **Columns**:
  - Metric name
  - Value
- **Contains**: Total issues, mean/median/P95 for cycle and lead times

### 3. Team Comparison
- **Purpose**: Compare teams side-by-side
- **Columns**:
  - Team
  - Issues Completed
  - Cycle Time Mean/Median
  - Lead Time Mean/Median
- **Use for**: Bar charts comparing teams

### 4. Individual Performance
- **Purpose**: Team member analysis
- **Columns**:
  - Team
  - Team Member
  - Issues Completed
  - Cycle Time Mean/Median
  - Lead Time Mean/Median
- **Use for**: Individual performance tracking, pivot tables

### 5. Raw Issue Data
- **Purpose**: Detailed pivot table analysis
- **Columns**:
  - Issue Key
  - Project (extracted from issue key)
  - Summary
  - Assignee
  - Resolved Date
  - Cycle Time (days/hours)
  - Lead Time (days/hours)
  - Year-Week (for grouping)
  - Month (for grouping)
- **Use for**: Create custom pivot tables and drill-down analysis

## Creating Charts and Pivot Tables

### Example 1: Weekly Trend Chart

1. Go to "Weekly Summary" sheet
2. Select data (Week column + Cycle Time Mean)
3. Insert → Line Chart
4. Customize title and labels

### Example 2: Team Comparison Bar Chart

1. Go to "Team Comparison" sheet
2. Select Team column + Cycle Time Mean column
3. Insert → Bar Chart
4. Add data labels for exact values

### Example 3: Pivot Table by Team Member

1. Go to "Raw Issue Data" sheet
2. Insert → Pivot Table
3. Drag "Assignee" to Rows
4. Drag "Cycle Time (days)" to Values (set to Average)
5. Drag "Year-Week" to Filters (to filter by time period)

### Example 4: Distribution Histogram

1. Go to "Raw Issue Data" sheet
2. Select "Cycle Time (days)" column
3. Insert → Histogram
4. Adjust bin width as needed

### Example 5: Monthly Performance Pivot

1. Go to "Raw Issue Data" sheet
2. Create pivot table with:
   - Rows: Month
   - Columns: Project or Assignee
   - Values: Count of Issues, Average Cycle Time

### Example 6: Project Comparison

1. Go to "Raw Issue Data" sheet
2. Create pivot table with:
   - Rows: Project
   - Values: Count of Issues, Average Cycle Time, Median Cycle Time
3. Or create a bar chart showing cycle time by project

## Tips

- **Freeze Panes**: Top row is already frozen for easy scrolling
- **Auto-filtering**: Click header row to enable filtering
- **Conditional Formatting**: Apply to highlight high/low performers
- **Sparklines**: Add mini-charts in cells for quick trends
- **Named Ranges**: Define ranges for easier chart creation

## Advanced Analysis Ideas

### 1. Cycle Time Distribution
Create a histogram of cycle times to identify outliers and understand the distribution.

### 2. Team Member Ranking
Use conditional formatting or a bar chart to rank team members by average cycle time.

### 3. Week-over-Week Change
Add a calculated column to show % change from previous week.

### 4. Velocity Tracking
Plot issues completed per week to track team velocity.

### 5. SLA Compliance
Add conditional formatting to highlight issues exceeding target cycle time.

## Formatting Features

The exported Excel includes:
- ✓ Professional header styling (blue background, white text)
- ✓ Auto-sized columns
- ✓ Frozen header row
- ✓ Date formatting
- ✓ Sorted data (by date/name)

## Troubleshooting

**Import Error**: Make sure pandas and openpyxl are installed
```bash
pip install pandas openpyxl
```

**Large Files**: For many issues (>10,000), export may take a few minutes

**Date Issues**: Dates are in ISO format (YYYY-MM-DD) for easy sorting
