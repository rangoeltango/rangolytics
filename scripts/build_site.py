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

    # Add playoff indicators
    df['Playoff'] = df['Rank'].apply(lambda x: '🏆' if x == 1 else '⭐' if x <= 8 else '')
    
    # Get metrics for cards
    league_leader = df.loc[df['Rank'] == 1, 'Team Name'].iloc[0]
    
    # Last MoTM Champion
    last_motm_champ = "Gabi-Gabi-Gabagool"
    
    # Current MoTM Leader (MoTM 7 - highest points, then highest score for ties)
    current_motm = "TBD"
    if 'MoTM 7 Points' in df.columns and 'MoTM 7 Score' in df.columns:
        # Sort by MoTM 7 Points (descending), then by MoTM 7 Score (descending) for tiebreaker
        motm_sorted = df.sort_values(['MoTM 7 Points', 'MoTM 7 Score'], ascending=[False, False])
        current_motm = motm_sorted.iloc[0]['Team Name']
    
    display_cols = ["Rank", "Playoff", "Team Name", "Total Score", "Total Points", "W", "D", "L", "Total FFPts"]
    display_cols = [c for c in display_cols if c in df.columns]
    table_html = df[display_cols].sort_values("Rank").to_html(index=False, escape=False)
    
    # Create MoTM standings data
    motm_cols = ["Team Name", "MoTM 7 Points", "MoTM 7 Score", "MoTM 7 Score Behind", "MoTM 7 Behind", "Wk 21 Result", "Wk 22 Result", "Wk 23 Opponent Team", "Wk 24 Opponent Team"]
    available_motm_cols = [col for col in motm_cols if col in df.columns]
    
    # If MoTM 7 Score Behind doesn't exist but MoTM 7 Score does, calculate it
    if "MoTM 7 Score Behind" not in df.columns and "MoTM 7 Score" in df.columns:
        max_score = df["MoTM 7 Score"].max()
        df["MoTM 7 Score Behind"] = max_score - df["MoTM 7 Score"]
        # Update available columns list
        available_motm_cols = [col for col in motm_cols if col in df.columns]
    
    if len(available_motm_cols) > 2:  # At least Team Name and one other column
        # Sort by MoTM 7 Points (high to low), then by MoTM 7 Score (high to low) for tiebreaking
        sort_cols = []
        sort_ascending = []
        
        if "MoTM 7 Points" in df.columns:
            sort_cols.append("MoTM 7 Points")
            sort_ascending.append(False)  # High to low
            
        if "MoTM 7 Score" in df.columns:
            sort_cols.append("MoTM 7 Score")
            sort_ascending.append(False)  # High to low
            
        if sort_cols:
            motm_df = df[available_motm_cols].sort_values(sort_cols, ascending=sort_ascending)
        else:
            motm_df = df[available_motm_cols].sort_values(available_motm_cols[1], ascending=False)
        
        # Determine highest and second highest MoTM 7 Points values for flagging
        if "MoTM 7 Points" in motm_df.columns:
            unique_points = sorted(motm_df["MoTM 7 Points"].unique(), reverse=True)
            highest_points = unique_points[0] if len(unique_points) > 0 else None
            second_highest_points = unique_points[1] if len(unique_points) > 1 else None
        else:
            highest_points = None
            second_highest_points = None
        
        # Create detailed table for MoTM standings with color coding
        motm_table_html = "<table border='1' class='dataframe'><thead><tr style='text-align: right;'>"
        for col in available_motm_cols:
            motm_table_html += f"<th>{col}</th>"
        motm_table_html += "</tr></thead><tbody>"
        
        for _, row in motm_df.iterrows():
            motm_table_html += "<tr>"
            for col in available_motm_cols:
                val = row[col]
                if col == "MoTM 7 Points":
                    # Add flags based on point values
                    if val == highest_points:
                        motm_table_html += f'<td>🟢 {val}</td>'
                    elif val == second_highest_points:
                        motm_table_html += f'<td>🟡 {val}</td>'
                    else:
                        motm_table_html += f'<td>{val}</td>'
                elif "Result" in col:
                    # Color code results
                    if val == "W":
                        motm_table_html += f'<td style="color: green; font-weight: bold;">{val}</td>'
                    elif val == "D":
                        motm_table_html += f'<td style="color: orange; font-weight: bold;">{val}</td>'
                    elif val == "L":
                        motm_table_html += f'<td style="color: red; font-weight: bold;">{val}</td>'
                    else:
                        motm_table_html += f'<td>{val}</td>'
                else:
                    motm_table_html += f'<td>{val}</td>'
            motm_table_html += "</tr>"
        motm_table_html += "</tbody></table>"
    else:
        motm_table_html = "<p>MoTM data not available</p>"
    
    # Create bar chart for Total Points by Team
    chart_df = df.sort_values("Total Points", ascending=False)
    fig = px.bar(
        chart_df, 
        x="Team Name", 
        y="Total Points",
        title="Total Points by Team",
        labels={"Total Points": "Total Points", "Team Name": "Team Name"},
        text="Total Points",
        color_discrete_sequence=["#3A083F"]
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_tickangle=-45,
        height=600,
        margin=dict(b=100, t=80),
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
                text=gw_score_col
            )
            # Apply custom colors to preserve sort order
            gw_fig.update_traces(marker_color=colors, textposition='outside')
            gw_fig.update_layout(
                xaxis_tickangle=-45,
                height=600,
                margin=dict(b=100, t=80),
                font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif"),
                showlegend=False
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
  <title>Farmer's League Football V</title>
  <style>
    body {{ 
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; 
      max-width: 900px; 
      margin: 40px auto; 
      padding: 0 16px;
      background: linear-gradient(135deg, #2d1b69 0%, #3A083F 50%, #1f0a2e 100%);
      min-height: 100vh;
    }}
    h1 {{
      color: #ffffff;
      text-align: center;
      font-weight: 700;
      font-size: 2.5rem;
      margin-bottom: 2rem;
      text-shadow: 0 2px 4px rgba(0,0,0,0.1);
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 1rem;
    }}
    .logo {{
      height: 60px;
      width: auto;
    }}
    .card {{ 
      border: 1px solid #d8b4fe; 
      border-radius: 16px; 
      padding: 20px; 
      margin: 20px 0; 
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(10px);
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07), 0 1px 3px rgba(0, 0, 0, 0.06);
    }}
    .card h2 {{
      color: #3A083F;
      margin-top: 0;
      margin-bottom: 1rem;
      font-weight: bold;
    }}
    table {{ 
      border-collapse: separate; 
      width: 100%; 
      background: white;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      max-height: 400px;
      overflow-y: auto;
      display: block;
    }}
    table thead, table tbody {{
      display: table;
      width: 100%;
      table-layout: fixed;
    }}
    table thead {{
      position: sticky;
      top: 0;
      background: linear-gradient(135deg, #3A083F, #2d0631);
      z-index: 10;
    }}
    th, td {{ 
      border-bottom: 1px solid #e5e7eb; 
      text-align: center; 
      padding: 8px 12px;
      font-size: 0.95rem;
      width: 8%;
    }}
    th:nth-child(3), td:nth-child(3) {{
      width: 25%;
      text-align: left;
    }}
    th:first-child, td:first-child {{
      text-align: center;
      width: 6%;
    }}
    th:nth-child(2), td:nth-child(2) {{
      text-align: center;
      width: 6%;
    }}
    th {{ 
      background: linear-gradient(135deg, #3A083F, #2d0631);
      color: white;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-size: 0.85rem;
    }}
    td {{
      background: white;
    }}
    tr:nth-child(even) td {{
      background: #f9fafb;
    }}
    tr:hover td {{
      background: #faf7ff;
    }}
    .kpis {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .kpi {{ border: 1px solid #d8b4fe; border-radius: 14px; padding: 12px; background: rgba(255, 255, 255, 0.8); }}
    .kpi h3 {{
      font-size: 1.5rem;
      font-weight: bold;
      color: #3A083F;
      margin: 0 0 0.5rem 0;
      text-align: center;
    }}
    .kpi p {{
      font-size: 1rem;
      font-weight: normal;
      color: #000;
      margin: 0;
      text-align: center;
    }}
    .muted {{ color: #6b7280; text-align: center; margin-top: 2rem; }}
    .large-title {{
      font-size: 1.5rem;
      font-weight: bold;
      color: #3A083F;
      margin-top: 0;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
  <h1>
    <img src="logo.PNG" alt="League Logo" class="logo">
    Farmer's Football League 2025-2026
  </h1>

  <div class="kpis">
    <div class="kpi">
      <h3>League Leader</h3>
      <p>{league_leader}</p>
    </div>
    <div class="kpi">
      <h3>Last MoTM Champ</h3>
      <p>{last_motm_champ}</p>
    </div>
    <div class="kpi">
      <h3>Current MoTM Leader</h3>
      <p>{current_motm}</p>
    </div>
  </div>

  <div class="card">
    <h2 class="large-title">Current MoTM Standings</h2>
    {motm_table_html}
  </div>

  <div class="card">
    <h2 class="large-title">League Standings</h2>
    {table_html}
  </div>

  <div class="card">
    <h2 class="large-title">Total Points by Team</h2>
    {chart_html}
  </div>

  <div class="card">
    <h2 class="large-title">Latest Gameweek Results</h2>
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
