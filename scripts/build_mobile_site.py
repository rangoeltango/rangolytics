import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "site"
OUT_FILE = OUT_DIR / "farmers-mobile.html"

def load_lineup_data():
    """Load and process lineup data"""
    try:
        lineup_df = pd.read_excel(ROOT / "data" / "lineup_data.xlsx")
        return lineup_df
    except FileNotFoundError:
        return None

def get_current_lineup_gameweek(lineup_df):
    """Get the current gameweek that has lineup data"""
    if lineup_df is None:
        return None
    
    # Find GW score columns in lineup data
    gw_cols = [col for col in lineup_df.columns if col.startswith('GW ') and col.endswith(' Score')]
    
    if not gw_cols:
        return None
    
    # Extract gameweek numbers and return the highest one
    gw_numbers = []
    for col in gw_cols:
        try:
            gw_num = int(col.split(' ')[1])
            gw_numbers.append(gw_num)
        except (IndexError, ValueError):
            continue
    
    return max(gw_numbers) if gw_numbers else None

def get_team_lineup_for_gw(lineup_df, team_name, gw):
    """Get lineup for specific team and gameweek"""
    if lineup_df is None:
        return []
    
    team_data = lineup_df[lineup_df['Team Name'] == team_name]
    if team_data.empty:
        return []
    
    lineup = []
    for _, row in team_data.iterrows():
        # Our new format has simplified columns
        score_col = f'GW {gw} Score'
        
        if 'Player' in row and pd.notna(row['Player']) and row['Player'] != '':
            player_info = {
                'name': row['Player'],
                'position': row['Position Type'],  # Use Position Type for grouping
                'position_number': row['Position'],  # Keep numeric position for ordering
                'score': row[score_col] if score_col in row and pd.notna(row[score_col]) else 0,
                'status': '',  # Not available in new format
                'is_captain': row['Is Captain'] if pd.notna(row['Is Captain']) else False,
                'is_vice': row['Is Vice Captain'] if pd.notna(row['Is Vice Captain']) else False,
                'is_effective_captain': False  # Can derive from multiplier if needed
            }
            lineup.append(player_info)
    
    return lineup

def generate_lineup_html(lineup, team_name, opponent_lineup=None):
    """Generate HTML for team lineup"""
    if not lineup:
        return f"<p>No lineup data available for {team_name}</p>"
    
    # Process captain scoring
    processed_lineup = []
    captain_player = None
    vice_captain_player = None
    
    for player in lineup:
        player_copy = player.copy()
        if player['is_captain']:
            captain_player = player_copy
        elif player['is_vice']:
            vice_captain_player = player_copy
        processed_lineup.append(player_copy)
    
    # Apply captain scoring logic
    if captain_player and captain_player['score'] > 0:
        # Captain played, double their score
        captain_player['score'] *= 2
        captain_player['captain_scored'] = True
    elif vice_captain_player and vice_captain_player['score'] > 0:
        # Captain didn't play, double vice-captain's score
        vice_captain_player['score'] *= 2
        vice_captain_player['captain_scored'] = True
    
    # Get opponent player names for comparison
    opponent_players = set()
    if opponent_lineup:
        opponent_players = {p['name'] for p in opponent_lineup}
    
    html = f"<div class='lineup-container'>"
    
    # Separate starters and bench players
    starters = [p for p in processed_lineup if p['position_number'] <= 11]
    bench = [p for p in processed_lineup if p['position_number'] > 11]
    
    # Sort by score (highest to lowest)
    starters.sort(key=lambda x: x['score'], reverse=True)
    bench.sort(key=lambda x: x['score'], reverse=True)
    
    # Find highest scorer in the team
    all_players = starters + bench
    highest_score = max((p['score'] for p in all_players), default=0)
    
    # Show starters
    if starters:
        html += "<div class='lineup-group'><h5 style='color: #28a745; margin-bottom: 10px;'>STARTERS</h5>"
        for player in starters:
            captain_badge = ""
            if player['is_effective_captain']:
                captain_badge = " <span class='captain-badge effective'>C</span>"
            elif player['is_captain']:
                captain_badge = " <span class='captain-badge'>C</span>"
            elif player['is_vice']:
                captain_badge = " <span class='captain-badge vice'>VC</span>"
            
            # Add captain multiplier indicator
            if player.get('captain_scored', False):
                captain_badge += " <span class='multiplier-badge'>×2</span>"
            
            # Add star for highest scorer
            star = " ⭐" if player['score'] == highest_score and highest_score > 0 else ""
            
            # Check if player is on both teams
            common_indicator = " <span class='common-player'>🤝</span>" if player['name'] in opponent_players else ""
            
            score_display = int(player['score']) if player['score'] != 0 and pd.notna(player['score']) else 0
            html += f"""<div class='player-row starter'>
                <span class='player-info'>{player['name']} - {player['position']} - {score_display} pts{star}{captain_badge}{common_indicator}</span>
            </div>"""
        html += "</div>"
    
    # Show bench
    if bench:
        html += "<div class='lineup-group'><h5 style='color: #6c757d; margin-bottom: 10px; margin-top: 15px;'>BENCH</h5>"
        for player in bench:
            captain_badge = ""
            if player['is_vice']:
                captain_badge = " <span class='captain-badge vice'>VC</span>"
            
            # Add captain multiplier indicator
            if player.get('captain_scored', False):
                captain_badge += " <span class='multiplier-badge'>×2</span>"
            
            # Add star for highest scorer
            star = " ⭐" if player['score'] == highest_score and highest_score > 0 else ""
            
            # Check if player is on both teams
            common_indicator = " <span class='common-player'>🤝</span>" if player['name'] in opponent_players else ""
            
            score_display = int(player['score']) if player['score'] != 0 and pd.notna(player['score']) else 0
            html += f"""<div class='player-row bench'>
                <span class='player-info'>{player['name']} - {player['position']} - {score_display} pts{star}{captain_badge}{common_indicator}</span>
            </div>"""
        html += "</div>"
    
    html += "</div>"
    return html

def main():
    df = pd.read_excel(ROOT / "data" / "league_results.xlsx", sheet_name="Sheet1")
    lineup_df = load_lineup_data()

    # Add playoff indicators
    df['Playoff'] = df['Rank'].apply(lambda x: '🏆' if x == 1 else '⭐' if x <= 8 else '')
    
    # Get metrics for cards
    league_leader = df.loc[df['Rank'] == 1, 'Team Name'].iloc[0]
    
    # Last MoTM Champion
    last_motm_champ = "Momoney"
    
    # Current MoTM Leader (MoTM 8 - highest points, then highest score for ties)
    current_motm = "TBD"
    if 'MoTM 8 Points' in df.columns and 'MoTM 8 Score' in df.columns:
        # Sort by MoTM 8 Points (descending), then by MoTM 8 Score (descending) for tiebreaker
        motm_sorted = df.sort_values(['MoTM 8 Points', 'MoTM 8 Score'], ascending=[False, False])
        current_motm = motm_sorted.iloc[0]['Team Name']
    
    # Find most recent week with data first (moved up from later in code)
    score_cols = [col for col in df.columns if col.startswith('Wk ') and col.endswith(' Score')]
    most_recent_week = 0
    for col in score_cols:
        week_num = int(col.split()[1])
        if not df[col].isna().all() and df[col].sum() > 0:  # Has actual scores
            most_recent_week = max(most_recent_week, week_num)
    
    display_cols = ["Rank", "Playoff", "Team Name", "Total Score", "Total Points", "W", "D", "L", "Total FFPts"]
    display_cols = [c for c in display_cols if c in df.columns]
    
    # Create MoTM standings data with fixed columns for MoTM 8
    motm_cols = ["Team Name", "MoTM 8 Points", "MoTM 8 Score", "MoTM 8 Score Behind", "MoTM 8 Behind", 
                 "Wk 25 Result", "Wk 26 Opponent Team", "Wk 27 Opponent Team", "Wk 28 Opponent Team"]
    available_motm_cols = [col for col in motm_cols if col in df.columns]
    
    # If MoTM 8 Score Behind doesn't exist but MoTM 8 Score does, calculate it
    if "MoTM 8 Score Behind" not in df.columns and "MoTM 8 Score" in df.columns:
        max_score = df["MoTM 8 Score"].max()
        df["MoTM 8 Score Behind"] = max_score - df["MoTM 8 Score"]
        # Update available columns list
        available_motm_cols = [col for col in motm_cols if col in df.columns]
    
    if len(available_motm_cols) > 2:  # At least Team Name and one other column
        # Sort by MoTM 8 Points (high to low), then by MoTM 8 Score (high to low) for tiebreaking
        sort_cols = []
        sort_ascending = []
        
        if "MoTM 8 Points" in df.columns:
            sort_cols.append("MoTM 8 Points")
            sort_ascending.append(False)  # High to low
            
        if "MoTM 8 Score" in df.columns:
            sort_cols.append("MoTM 8 Score")
            sort_ascending.append(False)  # High to low
            
        if sort_cols:
            motm_df = df[available_motm_cols].sort_values(sort_cols, ascending=sort_ascending)
        else:
            motm_df = df[available_motm_cols].sort_values(available_motm_cols[1], ascending=False)
        
        # Determine highest and second highest MoTM 8 Points values for flagging
        if "MoTM 8 Points" in motm_df.columns:
            unique_points = sorted(motm_df["MoTM 8 Points"].unique(), reverse=True)
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
                elif col == "MoTM 8 Points":
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

    # Create GW Matchups section
    if most_recent_week > 0:
        opponent_team_col = f'Wk {most_recent_week} Opponent Team'
        opponent_score_col = f'Wk {most_recent_week} Opponent Score'
        team_score_col = f'Wk {most_recent_week} Score'
        team_result_col = f'Wk {most_recent_week} Result'
        
        if all(col in df.columns for col in [opponent_team_col, opponent_score_col, team_score_col]):
            # Create matchups data
            matchups_html = ""            
            processed_teams = set()
            matchup_data = []
            
            for _, team_row in df.iterrows():
                team_name = team_row['Team Name']
                if team_name in processed_teams:
                    continue
                
                opponent_name = team_row[opponent_team_col]
                team_score = team_row[team_score_col] if pd.notna(team_row[team_score_col]) else 0
                opponent_score = team_row[opponent_score_col] if pd.notna(team_row[opponent_score_col]) else 0
                team_result = team_row[team_result_col] if team_result_col in df.columns else 'TBD'
                
                # Get team record (W-D-L)
                team_w = team_row['W'] if 'W' in df.columns else 0
                team_d = team_row['D'] if 'D' in df.columns else 0
                team_l = team_row['L'] if 'L' in df.columns else 0
                team_record = f"{int(team_w)}-{int(team_d)}-{int(team_l)}"
                
                # Find opponent row for their result and record
                opponent_row = df[df['Team Name'] == opponent_name]
                opponent_result = 'TBD'
                opponent_record = "0-0-0"
                if not opponent_row.empty:
                    if team_result_col in df.columns:
                        opponent_result = opponent_row.iloc[0][team_result_col]
                    # Get opponent record
                    opp_w = opponent_row.iloc[0]['W'] if 'W' in df.columns else 0
                    opp_d = opponent_row.iloc[0]['D'] if 'D' in df.columns else 0
                    opp_l = opponent_row.iloc[0]['L'] if 'L' in df.columns else 0
                    opponent_record = f"{int(opp_w)}-{int(opp_d)}-{int(opp_l)}"
                
                # Calculate score difference
                score_diff = abs(team_score - opponent_score)
                
                # Store matchup data for sorting
                matchup_data.append({
                    'team_name': team_name,
                    'team_score': team_score,
                    'team_result': team_result,
                    'team_record': team_record,
                    'opponent_name': opponent_name,
                    'opponent_score': opponent_score,
                    'opponent_result': opponent_result,
                    'opponent_record': opponent_record,
                    'score_diff': score_diff
                })
                
                # Mark both teams as processed
                processed_teams.add(team_name)
                processed_teams.add(opponent_name)
            
            # Sort matchups by score difference (smallest margin first)
            matchup_data.sort(key=lambda x: x['score_diff'])
            
            # Generate HTML for sorted matchups
            for i, matchup in enumerate(matchup_data):
                # Determine styling based on results
                team_class = 'border-success bg-success' if matchup['team_result'] == 'W' else 'border-danger bg-danger' if matchup['team_result'] == 'L' else 'border-warning bg-warning' if matchup['team_result'] == 'D' else 'border-secondary bg-secondary'
                opponent_class = 'border-success bg-success' if matchup['opponent_result'] == 'W' else 'border-danger bg-danger' if matchup['opponent_result'] == 'L' else 'border-warning bg-warning' if matchup['opponent_result'] == 'D' else 'border-secondary bg-secondary'
                
                # Handle singular/plural for points
                point_text = "pt" if matchup['score_diff'] == 1 else "pts"
                
                # Generate lineup data for both teams
                # Get current gameweek from lineup data
                current_lineup_gw = get_current_lineup_gameweek(lineup_df)
                if current_lineup_gw:
                    team_lineup = get_team_lineup_for_gw(lineup_df, matchup['team_name'], current_lineup_gw)
                    opponent_lineup = get_team_lineup_for_gw(lineup_df, matchup['opponent_name'], current_lineup_gw)
                else:
                    team_lineup = []
                    opponent_lineup = []
                
                team_lineup_html = generate_lineup_html(team_lineup, matchup['team_name'], opponent_lineup)
                opponent_lineup_html = generate_lineup_html(opponent_lineup, matchup['opponent_name'], team_lineup)
                
                matchups_html += f"""
                <div class="col-12 mb-3">
                    <div class="card border-0 shadow-sm">
                        <div class="card-body p-3">
                            <div class="row align-items-center">
                                <div class="col-4">
                                    <div class="card {team_class} bg-opacity-10 border-opacity-50">
                                        <div class="card-body p-2 text-center">
                                            <div class="d-flex justify-content-between align-items-center mb-1">
                                                <div class="fw-bold" style="font-size: 0.75rem;">{matchup['team_name']}</div>
                                                <button class="btn btn-sm p-0" onclick="toggleLineup('mobile-lineup-{i}')" style="font-size: 0.7rem;">📋</button>
                                            </div>
                                            <div class="text-muted mb-1" style="font-size: 0.65rem;">{matchup['team_record']}</div>
                                            <div class="h4 mb-1">{matchup['team_score']:.0f}</div>
                                            <div class="badge bg-dark">{matchup['team_result']}</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="fw-bold text-primary mb-1">VS</div>
                                    <small class="text-muted">Decided by {matchup['score_diff']:.0f} {point_text}</small>
                                </div>
                                <div class="col-4">
                                    <div class="card {opponent_class} bg-opacity-10 border-opacity-50">
                                        <div class="card-body p-2 text-center">
                                            <div class="d-flex justify-content-between align-items-center mb-1">
                                                <div class="fw-bold" style="font-size: 0.75rem;">{matchup['opponent_name']}</div>
                                                <button class="btn btn-sm p-0" onclick="toggleLineup('mobile-lineup-{i}')" style="font-size: 0.7rem;">📋</button>
                                            </div>
                                            <div class="text-muted mb-1" style="font-size: 0.65rem;">{matchup['opponent_record']}</div>
                                            <div class="h4 mb-1">{matchup['opponent_score']:.0f}</div>
                                            <div class="badge bg-dark">{matchup['opponent_result']}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="lineup-section" id="mobile-lineup-{i}" style="display: none; margin-top: 15px;">
                                <div class="row">
                                    <div class="col-6">
                                        <h6>{matchup['team_name']} - GW {current_lineup_gw} Lineup <button onclick='toggleSharedPlayers(this)' class='compact-toggle-btn' title='Hide/Show Shared Players'>🤝</button></h6>
                                        {team_lineup_html}
                                    </div>
                                    <div class="col-6">
                                        <h6>{matchup['opponent_name']} - GW {current_lineup_gw} Lineup <button onclick='toggleSharedPlayers(this)' class='compact-toggle-btn' title='Hide/Show Shared Players'>🤝</button></h6>
                                        {opponent_lineup_html}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """
                
        else:
            matchups_html = '<div class="alert alert-info">Matchup data not available for this gameweek</div>'
    else:
        matchups_html = '<div class="alert alert-info">No gameweek data available</div>'

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
    <script>
        function toggleLineup(lineupId) {{
            var lineup = document.getElementById(lineupId);
            if (lineup.style.display === "none" || lineup.style.display === "") {{
                lineup.style.display = "block";
            }} else {{
                lineup.style.display = "none";
            }}
        }}
        
        function toggleSharedPlayers(button) {{
            var lineupContainer = button.closest('.lineup-section');
            if (!lineupContainer) lineupContainer = button.closest('.col-6');
            var sharedPlayers = lineupContainer.querySelectorAll('.common-player');
            var isHidden = button.style.opacity === '0.5';
            
            sharedPlayers.forEach(function(player) {{
                var playerRow = player.closest('.player-row');
                if (playerRow) {{
                    if (isHidden) {{
                        playerRow.style.display = 'block';
                        button.style.opacity = '1';
                        button.title = 'Hide Shared Players';
                    }} else {{
                        playerRow.style.display = 'none';
                        button.style.opacity = '0.5';
                        button.title = 'Show Shared Players';
                    }}
                }}
            }});
        }}
    </script>
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
        
        .lineup-section {{
            background-color: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
        }}
        
        .lineup-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }}
        
        .position-group {{
            background: rgba(255, 255, 255, 0.15);
            padding: 8px;
            border-radius: 6px;
        }}
        
        .position-group h5 {{
            margin: 0 0 6px 0;
            color: white;
            font-size: 12px;
            font-weight: 600;
            text-align: center;
        }}
        
        .player-row {{
            display: flex;
            justify-content: flex-start;
            align-items: center;
            padding: 6px 10px;
            margin-bottom: 3px;
            border-radius: 4px;
            font-size: 12px;
        }}
        
        .player-row.starter {{
            background-color: rgba(255, 255, 255, 0.9);
            border-left: 3px solid #28a745;
            color: #333;
        }}
        
        .player-row.bench {{
            background-color: rgba(128, 128, 128, 0.6);
            border-left: 3px solid #6c757d;
            color: #fff;
        }}
        
        .player-info {{
            font-weight: 500;
            width: 100%;
        }}
        }}
        
        .captain-badge {{
            background-color: #007bff;
            color: white;
            font-size: 8px;
            padding: 1px 3px;
            border-radius: 2px;
            font-weight: bold;
            margin-left: 3px;
        }}
        
        .captain-badge.effective {{
            background-color: #28a745;
        }}
        
        .captain-badge.vice {{
            background-color: #6c757d;
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
        
        .shared-players-toggle {{
            text-align: center;
            margin: 10px 0 15px 0;
        }}
        
        .compact-toggle-btn {{
            background: none;
            border: none;
            font-size: 1rem;
            cursor: pointer;
            padding: 2px 4px;
            margin-left: 8px;
            border-radius: 4px;
            transition: opacity 0.3s ease;
            vertical-align: middle;
        }}
        
        .compact-toggle-btn:hover {{
            background: rgba(255,255,255,0.1);
        }}
        
        .compact-toggle-btn:active {{
            transform: scale(0.95);
        }}
        
        .common-player {{
            color: #28a745;
            font-weight: bold;
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
                <a href="farmers-desktop.html" class="btn btn-outline-light btn-sm">🖥️ View Desktop Version</a>
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

        <!-- GW Matchups -->
        <div class="container-fluid my-4">
            <div class="card border-0 shadow-sm">
                <div class="card-body">
                    <h3 class="text-center mb-3" style="color: #3A083F;">GW {most_recent_week} Matchups</h3>
                    <div class="row g-3">
                        {matchups_html}
                    </div>
                </div>
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