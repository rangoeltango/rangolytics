import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "site"
OUT_FILE = OUT_DIR / "football-mobile.html"

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
        motm_table_rows = ""
        for _, row in motm_df.iterrows():
            cells = ""
            for i, (col, val) in enumerate(row.items()):
                if i == 0:  # Team Name
                    cells += f'<td class="fw-semibold">{val}</td>'
                elif col == "MoTM 7 Points":
                    # Add flags based on point values
                    if val == highest_points:
                        cells += f'<td class="text-center">🟢 {val}</td>'
                    elif val == second_highest_points:
                        cells += f'<td class="text-center">🟡 {val}</td>'
                    else:
                        cells += f'<td class="text-center">{val}</td>'
                elif "Result" in col:
                    # Color code results
                    if val == "W":
                        cells += f'<td class="text-center" style="color: green; font-weight: bold;">{val}</td>'
                    elif val == "D":
                        cells += f'<td class="text-center" style="color: orange; font-weight: bold;">{val}</td>'
                    elif val == "L":
                        cells += f'<td class="text-center" style="color: red; font-weight: bold;">{val}</td>'
                    else:
                        cells += f'<td class="text-center">{val}</td>'
                else:
                    cells += f'<td class="text-center">{val}</td>'
            motm_table_rows += f'<tr>{cells}</tr>\n'
        
        motm_table_headers = ""
        for i, col in enumerate(available_motm_cols):
            if i == 0:  # Team Name
                motm_table_headers += f'<th scope="col" style="width: 25%;">{col}</th>'
            else:
                motm_table_headers += f'<th scope="col" class="text-center">{col}</th>'
    else:
        motm_table_rows = ""
        motm_table_headers = ""
    
    # Create responsive table with Bootstrap classes
    table_df = df[display_cols].sort_values("Rank")
    table_rows = ""
    for _, row in table_df.iterrows():
        cells = ""
        for i, (col, val) in enumerate(row.items()):
            if i == 0:  # Rank column
                cells += f'<td class="text-center fw-bold">{val}</td>'
            elif i == 1:  # Playoff column
                cells += f'<td class="text-center">{val}</td>'
            elif i == 2:  # Team Name column
                cells += f'<td class="fw-semibold">{val}</td>'
            else:
                cells += f'<td class="text-center">{val}</td>'
        table_rows += f'<tr>{cells}</tr>\n'
    
    # Create horizontal bar chart for Total Points by Team
    chart_df = df.sort_values("Total Points", ascending=True)  # Ascending for horizontal
    fig = px.bar(
        chart_df, 
        y="Team Name", 
        x="Total Points",
        orientation='h',
        labels={"Total Points": "Total Points", "Team Name": "Team Name"},
        text="Total Points",
        color_discrete_sequence=["#3A083F"]
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        height=700,
        margin=dict(l=160, r=15, t=15, b=15),  # Reduced left margin
        font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif"),
        yaxis=dict(tickfont=dict(size=11), showticklabels=True, title=None),
        xaxis=dict(range=[0, chart_df['Total Points'].max() * 1.15]),  # Add 15% padding
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
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
            gw_df = gw_df.sort_values(gw_score_col, ascending=True)  # Ascending for horizontal bars
            
            # Color mapping for results
            color_map = {'W': 'green', 'L': 'red', 'D': 'gold'}
            colors = [color_map.get(result, 'blue') for result in gw_df[gw_result_col]]
            
            gw_fig = px.bar(
                gw_df,
                y='Team Name',
                x=gw_score_col,
                orientation='h',
                labels={gw_score_col: 'Score', 'Team Name': 'Team Name'},
                text=gw_score_col
            )
            # Apply custom colors to preserve sort order
            gw_fig.update_traces(marker_color=colors, textposition='outside')
            gw_fig.update_layout(
                height=700,
                margin=dict(l=160, r=15, t=15, b=15),
                font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif"),
                showlegend=False,
                yaxis=dict(tickfont=dict(size=11), showticklabels=True, title=None),
                xaxis=dict(range=[0, gw_df[gw_score_col].max() * 1.15]),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            gw_chart_html = pio.to_html(gw_fig, include_plotlyjs='cdn', div_id="gameweek-chart")
        else:
            gw_chart_html = "<p>No gameweek data available</p>"
    else:
        gw_chart_html = "<p>No gameweek data available</p>"

    # Create 5 Week Form Table
    if most_recent_week >= 5:
        # Calculate 5-week range
        start_week = most_recent_week - 4
        end_week = most_recent_week
        
        # Calculate 5-week scores
        five_week_cols = [f'Wk {w} Score' for w in range(start_week, end_week + 1)]
        available_five_week_cols = [col for col in five_week_cols if col in df.columns]
        
        if available_five_week_cols:
            # Calculate 5-week totals
            df['5 Week Score'] = df[available_five_week_cols].sum(axis=1)
            
            # Calculate 5-week rank
            df['5 Week Rank'] = df['5 Week Score'].rank(method='dense', ascending=False).astype(int)
            
            # Calculate behind 5-week high
            five_week_high = df['5 Week Score'].max()
            df['Behind 5 Week High'] = five_week_high - df['5 Week Score']
            
            # Prepare result columns for the 5 weeks
            result_cols = [f'Wk {w} Result' for w in range(start_week, end_week + 1)]
            available_result_cols = [col for col in result_cols if col in df.columns]
            
            # Create table columns
            form_cols = ['Rank', '5 Week Rank', 'Team Name', '5 Week Score', 'Behind 5 Week High'] + available_result_cols
            form_available_cols = [col for col in form_cols if col in df.columns]
            
            # Sort by 5 Week Score descending
            form_df = df[form_available_cols].sort_values('5 Week Score', ascending=False)
            
            # Create mobile-friendly table headers
            form_table_headers = ""
            for i, col in enumerate(form_available_cols):
                if col == "Team Name":
                    form_table_headers += f'<th scope="col" style="width: 25%;">{col}</th>'
                elif col in ["Rank", "5 Week Rank"]:
                    form_table_headers += f'<th scope="col" class="text-center" style="width: 8%;">{col}</th>'
                else:
                    form_table_headers += f'<th scope="col" class="text-center">{col}</th>'
            
            # Create mobile-friendly table rows
            form_table_rows = ""
            for _, row in form_df.iterrows():
                cells = ""
                for col in form_available_cols:
                    val = row[col]
                    if col in available_result_cols and "Result" in col:
                        # Color code results
                        if val == "W":
                            cells += f'<td class="text-center" style="color: green; font-weight: bold;">{val}</td>'
                        elif val == "D":
                            cells += f'<td class="text-center" style="color: #DAA520; font-weight: bold;">{val}</td>'
                        elif val == "L":
                            cells += f'<td class="text-center" style="color: red; font-weight: bold;">{val}</td>'
                        else:
                            cells += f'<td class="text-center">{val}</td>'
                    elif col == "Team Name":
                        cells += f'<td>{val}</td>'
                    else:
                        cells += f'<td class="text-center">{val}</td>'
                form_table_rows += f'<tr>{cells}</tr>\n'
            
        else:
            form_table_headers = "<th>No Data</th>"
            form_table_rows = "<tr><td>5 Week Form data not available</td></tr>"
    else:
        form_table_headers = "<th>No Data</th>"
        form_table_rows = "<tr><td>Not enough weeks of data for 5 Week Form table</td></tr>"

    # Create column headers for table
    table_headers = ""
    for i, col in enumerate(display_cols):
        if i == 0:  # Rank
            table_headers += f'<th scope="col" class="text-center" style="width: 8%;">{col}</th>'
        elif i == 1:  # Playoff
            table_headers += f'<th scope="col" class="text-center" style="width: 8%;">{col}</th>'
        elif i == 2:  # Team Name
            table_headers += f'<th scope="col" style="width: 30%;">{col}</th>'
        else:
            table_headers += f'<th scope="col" class="text-center">{col}</th>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farmer's Football League 2025-2026 - Mobile</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {{
            --primary-purple: #3A083F;
            --secondary-purple: #2d0631;
            --light-purple: #d8b4fe;
        }}
        
        body {{
            background: linear-gradient(135deg, var(--primary-purple), var(--secondary-purple));
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: white;
        }}
        
        .hero-section {{
            text-align: center;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }}
        
        .league-title {{
            font-size: 2rem;
            font-weight: bold;
            margin: 1rem 0;
            color: white;
        }}
        
        .logo {{
            height: 80px;
            width: auto;
            margin-bottom: 1rem;
        }}
        
        .metric-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            border: 2px solid var(--light-purple);
        }}
        
        .metric-title {{
            color: var(--primary-purple);
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value {{
            color: #333;
            font-size: 1rem;
        }}
        
        .content-card {{
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            border: 2px solid var(--light-purple);
        }}
        
        .section-title {{
            color: var(--primary-purple);
            font-weight: bold;
            font-size: 1.4rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }}
        
        .table {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            font-size: 0.9rem;
        }}
        
        .table thead th {{
            background: linear-gradient(135deg, var(--primary-purple), var(--secondary-purple));
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: none;
            font-size: 0.8rem;
            padding: 0.75rem 0.5rem;
        }}
        
        .table tbody td {{
            color: #333;
            border-color: #e5e7eb;
            vertical-align: middle;
            padding: 0.75rem 0.5rem;
        }}
        
        .table-container {{
            max-height: 500px;
            overflow-y: auto;
            border-radius: 12px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 0.5rem;
            margin: 1rem 0;
            overflow: hidden;
        }}
        
        .timestamp {{
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
            margin-top: 2rem;
        }}
        
        /* Mobile optimizations */
        @media (max-width: 768px) {{
            .league-title {{
                font-size: 1.5rem;
            }}
            
            .logo {{
                height: 60px;
            }}
            
            .table {{
                font-size: 0.8rem;
            }}
            
            .table thead th,
            .table tbody td {{
                padding: 0.5rem 0.3rem;
            }}
            
            .content-card {{
                padding: 1rem;
                margin-bottom: 1.5rem;
            }}
            
            .metric-card {{
                padding: 1rem;
            }}
        }}
        
        /* Extra small screens */
        @media (max-width: 576px) {{
            .table {{
                font-size: 0.75rem;
            }}
            
            .table thead th,
            .table tbody td {{
                padding: 0.4rem 0.2rem;
            }}
            
            .league-title {{
                font-size: 1.3rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Hero Section -->
        <div class="hero-section">
            <img src="logo.PNG" alt="League Logo" class="logo">
            <h1 class="league-title">Farmer's Football League 2025-2026</h1>
            <div class="text-center mt-3">
                <a href="index.html" class="btn btn-outline-light btn-sm me-2">🏠 Home</a>
                <a href="football-desktop.html" class="btn btn-outline-light btn-sm">🖥️ View Desktop Version</a>
            </div>
        </div>

        <!-- Metric Cards -->
        <div class="row mb-4">
            <div class="col-md-4 col-12">
                <div class="metric-card">
                    <div class="metric-title">League Leader</div>
                    <div class="metric-value">{league_leader}</div>
                </div>
            </div>
            <div class="col-md-4 col-12">
                <div class="metric-card">
                    <div class="metric-title">Last MoTM Champ</div>
                    <div class="metric-value">{last_motm_champ}</div>
                </div>
            </div>
            <div class="col-md-4 col-12">
                <div class="metric-card">
                    <div class="metric-title">Current MoTM Leader</div>
                    <div class="metric-value">{current_motm}</div>
                </div>
            </div>
        </div>

        <!-- MoTM Standings -->
        <div class="content-card">
            <h2 class="section-title">Current MoTM Standings</h2>
            <div class="table-container">
                <table class="table table-hover">
                    <thead class="sticky-top">
                        <tr>
                            {motm_table_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {motm_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- League Standings -->
        <div class="content-card">
            <h2 class="section-title">League Standings</h2>
            <div class="table-container">
                <table class="table table-hover">
                    <thead class="sticky-top">
                        <tr>
                            {table_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Charts -->
        <div class="content-card">
            <h2 class="section-title">Total Points by Team</h2>
            <div class="chart-container">
                {chart_html}
            </div>
        </div>

        <div class="content-card">
            <h2 class="section-title">Latest Gameweek (GW{most_recent_week}) Results</h2>
            <div class="chart-container">
                {gw_chart_html}
            </div>
        </div>

        <div class="content-card">
            <h2 class="section-title">5 Week Form Table</h2>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead class="table-dark">
                        <tr>
                            {form_table_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {form_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="timestamp">
            Generated at: {pd.Timestamp.now('UTC')} UTC
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")

if __name__ == "__main__":
    main()