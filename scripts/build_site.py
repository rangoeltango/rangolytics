from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sample.csv"
OUT_DIR = ROOT / "site"
OUT_FILE = OUT_DIR / "index.html"

def main():
    df = pd.read_excel(ROOT / "data" / "league_results.xlsx", sheet_name="Sheet1")

    display_cols = ["Rank", "Team Name", "Total Score", "Total Points", "W", "D", "L", "Total FFPts"]
    display_cols = [c for c in display_cols if c in df.columns]
    table_html = df[display_cols].sort_values("Rank").to_html(index=False)
    
    # Create bar chart for Total Points by Team
    chart_df = df.sort_values("Total Points", ascending=False)
    fig = px.bar(
        chart_df, 
        x="Team Name", 
        y="Total Points",
        title="Total Points by Team",
        labels={"Total Points": "Total Points", "Team Name": "Team Name"},
        text="Total Points"
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        margin=dict(b=100),
        font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif")
    )
    chart_html = pio.to_html(fig, include_plotlyjs='cdn', div_id="points-chart")
    
    # Find most recent week with data
    score_cols = [col for col in df.columns if col.startswith('Wk ') and col.endswith(' Score')]
    most_recent_week = 0
    for col in score_cols:
        week_num = int(col.split()[1])
        if not df[col].isna().all() and df[col].sum() > 0:  # Has actual scores
            most_recent_week = max(most_recent_week, week_num)
    
    # Create gameweek results chart
    if most_recent_week > 0:
        gw_score_col = f'Wk {most_recent_week} Score'
        gw_result_col = f'Wk {most_recent_week} Result'
        
        if gw_score_col in df.columns and gw_result_col in df.columns:
            gw_df = df[[gw_score_col, gw_result_col, 'Team Name']].copy()
            gw_df = gw_df.sort_values(gw_score_col, ascending=False)
            
            # Color mapping for results
            color_map = {'W': 'green', 'L': 'red', 'D': 'gold'}
            colors = [color_map.get(result, 'blue') for result in gw_df[gw_result_col]]
            
            gw_fig = px.bar(
                gw_df,
                x='Team Name',
                y=gw_score_col,
                title=f'Gameweek {most_recent_week} Results',
                labels={gw_score_col: 'Score', 'Team Name': 'Team Name'},
                text=gw_score_col,
                color=gw_result_col,
                color_discrete_map=color_map
            )
            gw_fig.update_traces(textposition='outside')
            gw_fig.update_layout(
                xaxis_tickangle=-45,
                height=500,
                margin=dict(b=100),
                font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif"),
                showlegend=True
            )
            gw_chart_html = pio.to_html(gw_fig, include_plotlyjs='cdn', div_id="gameweek-chart")
        else:
            gw_chart_html = "<p>No gameweek data available</p>"
    else:
        gw_chart_html = "<p>No gameweek data available</p>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>My Data MVP</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; margin: 16px 0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #eee; text-align: left; padding: 10px; }}
    th {{ background: #fafafa; }}
    .kpis {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .kpi {{ border: 1px solid #e5e7eb; border-radius: 14px; padding: 12px; }}
    .muted {{ color: #6b7280; }}
  </style>
</head>
<body>
  <h1>Farmer's Football League 2025-2026</h1>

  <div class="card">
    <h2>League Standings</h2>
    {table_html}
  </div>

  <div class="card">
    <h2>Total Points by Team</h2>
    {chart_html}
  </div>

  <div class="card">
    <h2>Latest Gameweek Results</h2>
    {gw_chart_html}
  </div>

  <div class="muted">
    Generated at: {pd.Timestamp.utcnow()} UTC
  </div>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")

if __name__ == "__main__":
    main()
