from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sample.csv"
OUT_DIR = ROOT / "site"
OUT_FILE = OUT_DIR / "farmers-desktop.html"

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
        html += "<div class='lineup-group'><h4 style='color: #6c757d; margin-bottom: 12px; margin-top: 20px;'>BENCH</h4>"
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
    
    display_cols = ["Rank", "Playoff", "Team Name", "Total Score", "Total Points", "W", "D", "L", "Total FFPts"]
    display_cols = [c for c in display_cols if c in df.columns]
    table_html = df[display_cols].sort_values("Rank").to_html(index=False, escape=False, classes="league-table", border=0)
    # Remove the default 'dataframe' class that pandas adds
    table_html = table_html.replace('class="dataframe league-table"', 'class="league-table"')
    
    # Find most recent week with data first (moved up from later in code)
    score_cols = [col for col in df.columns if col.startswith('Wk ') and col.endswith(' Score')]
    most_recent_week = 0
    for col in score_cols:
        week_num = int(col.split()[1])
        if not df[col].isna().all() and df[col].sum() > 0:  # Has actual scores
            most_recent_week = max(most_recent_week, week_num)
    
    # Create MoTM standings data with fixed columns for MoTM 8
    motm_cols = ["Team Name", "MoTM 8 Points", "MoTM 8 Score", "MoTM 8 Score Behind", "MoTM 8 Behind"]
    
    # Add specific weeks: Wk 25 result, then Wk 26-28 opponents
    motm_cols.extend(["Wk 25 Result", "Wk 26 Opponent Team", "Wk 27 Opponent Team", "Wk 28 Opponent Team"])
    
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
        motm_table_html = "<table border='1' class='dataframe'><thead><tr style='text-align: right;'>"
        for col in available_motm_cols:
            motm_table_html += f"<th>{col}</th>"
        motm_table_html += "</tr></thead><tbody>"
        
        for _, row in motm_df.iterrows():
            motm_table_html += "<tr>"
            for col in available_motm_cols:
                val = row[col]
                if col == "MoTM 8 Points":
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
            
            # Generate HTML table manually for proper styling
            form_table_html = "<table border='1' class='form-table'><thead><tr style='text-align: right;'>"
            for col in form_available_cols:
                form_table_html += f"<th>{col}</th>"
            form_table_html += "</tr></thead><tbody>"
            
            for _, row in form_df.iterrows():
                form_table_html += "<tr>"
                for col in form_available_cols:
                    val = row[col]
                    if col in available_result_cols and "Result" in col:
                        # Color code results
                        if val == "W":
                            form_table_html += f'<td style="color: green; font-weight: bold;">{val}</td>'
                        elif val == "D":
                            form_table_html += f'<td style="color: #DAA520; font-weight: bold;">{val}</td>'
                        elif val == "L":
                            form_table_html += f'<td style="color: red; font-weight: bold;">{val}</td>'
                        else:
                            form_table_html += f'<td>{val}</td>'
                    else:
                        form_table_html += f'<td>{val}</td>'
                form_table_html += "</tr>"
            form_table_html += "</tbody></table>"
        else:
            form_table_html = "<p>5 Week Form data not available</p>"
    else:
        form_table_html = "<p>Not enough weeks of data for 5 Week Form table</p>"

    # Create GW Matchups section
    if most_recent_week > 0:
        opponent_team_col = f'Wk {most_recent_week} Opponent Team'
        opponent_score_col = f'Wk {most_recent_week} Opponent Score'
        team_score_col = f'Wk {most_recent_week} Score'
        team_result_col = f'Wk {most_recent_week} Result'
        
        if all(col in df.columns for col in [opponent_team_col, opponent_score_col, team_score_col]):
            # Create matchups data
            matchups_html = "<div class='matchups-container'>"            
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
                team_record = f"({int(team_w)}-{int(team_d)}-{int(team_l)})"
                
                # Find opponent row for their result and record
                opponent_row = df[df['Team Name'] == opponent_name]
                opponent_result = 'TBD'
                opponent_record = "(0-0-0)"
                if not opponent_row.empty:
                    if team_result_col in df.columns:
                        opponent_result = opponent_row.iloc[0][team_result_col]
                    # Get opponent record
                    opp_w = opponent_row.iloc[0]['W'] if 'W' in df.columns else 0
                    opp_d = opponent_row.iloc[0]['D'] if 'D' in df.columns else 0
                    opp_l = opponent_row.iloc[0]['L'] if 'L' in df.columns else 0
                    opponent_record = f"({int(opp_w)}-{int(opp_d)}-{int(opp_l)})"
                
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
                team_class = 'win' if matchup['team_result'] == 'W' else 'loss' if matchup['team_result'] == 'L' else 'draw' if matchup['team_result'] == 'D' else 'pending'
                opponent_class = 'win' if matchup['opponent_result'] == 'W' else 'loss' if matchup['opponent_result'] == 'L' else 'draw' if matchup['opponent_result'] == 'D' else 'pending'
                
                # Handle singular/plural for points
                point_text = "pt" if matchup['score_diff'] == 1 else "pts"
                
                # Generate lineup data for both teams
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
                <div class="matchup-card">
                    <div class="team-card {team_class}">
                        <div class="team-name">
                            {matchup['team_name']} {matchup['team_record']}
                            <button class="expand-btn" onclick="toggleLineup('lineup-{i}')" title="View Lineups">📋</button>
                        </div>
                        <div class="team-score">{matchup['team_score']:.0f}</div>
                        <div class="team-result">{matchup['team_result']}</div>
                    </div>
                    <div class="vs-section">
                        <div class="vs-text">VS</div>
                        <div class="score-diff">Decided by {matchup['score_diff']:.0f} {point_text}</div>
                    </div>
                    <div class="team-card {opponent_class}">
                        <div class="team-name">
                            {matchup['opponent_name']} {matchup['opponent_record']}
                            <button class="expand-btn" onclick="toggleLineup('lineup-{i}')" title="View Lineups">📋</button>
                        </div>
                        <div class="team-score">{matchup['opponent_score']:.0f}</div>
                        <div class="team-result">{matchup['opponent_result']}</div>
                    </div>
                    <div class="lineup-section" id="lineup-{i}" style="display: none;">
                        <div style="display: flex; gap: 20px;">
                            <div style="flex: 1;">
                                <h4>{matchup['team_name']} - GW {current_lineup_gw} Lineup <button onclick='toggleSharedPlayers(this)' class='compact-toggle-btn' title='Hide/Show Shared Players'>🤝</button></h4>
                                {team_lineup_html}
                            </div>
                            <div style="flex: 1;">
                                <h4>{matchup['opponent_name']} - GW {current_lineup_gw} Lineup <button onclick='toggleSharedPlayers(this)' class='compact-toggle-btn' title='Hide/Show Shared Players'>🤝</button></h4>
                                {opponent_lineup_html}
                            </div>
                        </div>
                    </div>
                </div>
                """
            
            matchups_html += "</div>"
        else:
            matchups_html = "<p>Matchup data not available for this gameweek</p>"
    else:
        matchups_html = "<p>No gameweek data available</p>"

    # Build Top Scorers of the Week from lineup data
    top_scorers_html = "<p>No lineup data available</p>"
    if lineup_df is not None:
        current_lineup_gw = get_current_lineup_gameweek(lineup_df)
        if current_lineup_gw:
            score_col = f'GW {current_lineup_gw} Score'
            if score_col in lineup_df.columns:
                scorers_df = lineup_df[lineup_df[score_col].notna()].copy()
                # Determine role and captain from Multiplier (0=bench, 1=starter, 2=captain)
                scorers_df['Role'] = scorers_df['Multiplier'].map({0: 'Bench', 1: 'Starter', 2: 'Starter'})
                scorers_df['Captain'] = scorers_df['Multiplier'].apply(lambda x: 'Captain' if x == 2 else '')
                # Apply captain multiplier to score
                scorers_df['Effective Score'] = scorers_df[score_col] * scorers_df['Multiplier'].apply(lambda x: 2 if x == 2 else 1)
                # Group by Player + Position + Captain + Role
                player_stats = scorers_df.groupby(['Player', 'Position Type', 'Captain', 'Role']).agg(
                    Score=('Effective Score', 'first'),
                    TeamList=('Team Name', lambda x: ', '.join(sorted(x.unique())))
                ).reset_index()
                player_stats = player_stats.sort_values('Score', ascending=False).head(20)
                # Build table
                top_scorers_html = "<table class='motm-schedule-table' border='0'><thead><tr>"
                top_scorers_html += "<th>Rank</th><th>Player</th><th>Position</th><th>Score</th><th>Teams</th><th>Role</th><th>Captain</th>"
                top_scorers_html += "</tr></thead><tbody>"
                for rank, (_, row) in enumerate(player_stats.iterrows(), 1):
                    captain_display = '⭐ C' if row['Captain'] == 'Captain' else ''
                    top_scorers_html += f"<tr><td>{rank}</td><td>{row['Player']}</td><td>{row['Position Type']}</td><td>{int(row['Score'])}</td><td>{row['TeamList']}</td><td>{row['Role']}</td><td>{captain_display}</td></tr>"
                top_scorers_html += "</tbody></table>"

    # Load Manager of the Month Schedule
    try:
        motm_schedule_df = pd.read_excel(ROOT / "data" / "motm_schedule.xlsx")
        # Convert MoTM column to clean text (remove .0 decimals, keep NaN as empty)
        if 'MoTM' in motm_schedule_df.columns:
            motm_schedule_df['MoTM'] = motm_schedule_df['MoTM'].apply(
                lambda x: str(int(x)) if pd.notna(x) and isinstance(x, float) and x == int(x) else ('None' if pd.isna(x) else str(x))
            )

        # Determine current MoTM row based on most_recent_week
        def is_current_motm_row(row):
            try:
                first_gw = int(row['First Gameweek'].replace('GW ', ''))
                last_gw = int(row['Last Gameweek'].replace('GW ', ''))
                return first_gw <= most_recent_week <= last_gw
            except (ValueError, AttributeError):
                return False

        # Build table HTML manually to support row highlighting
        motm_schedule_table_html = "<table class='motm-schedule-table' border='0'><thead><tr>"
        for col in motm_schedule_df.columns:
            motm_schedule_table_html += f"<th>{col}</th>"
        motm_schedule_table_html += "</tr></thead><tbody>"
        for _, row in motm_schedule_df.iterrows():
            if is_current_motm_row(row):
                motm_schedule_table_html += "<tr class='current-motm'>"
            else:
                motm_schedule_table_html += "<tr>"
            for col in motm_schedule_df.columns:
                motm_schedule_table_html += f"<td>{row[col]}</td>"
            motm_schedule_table_html += "</tr>"
        motm_schedule_table_html += "</tbody></table>"
    except FileNotFoundError:
        motm_schedule_table_html = "<p>MoTM Schedule data not available</p>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Farmer's League Football V</title>
  <script>
    // Device detection and auto-redirect
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {{
      window.location.href = 'farmers-mobile.html';
    }}
    
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
      if (!lineupContainer) lineupContainer = button.parentElement.parentElement;
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
    body {{ 
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; 
      max-width: 1400px; 
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
    th {{
      color: white;
      font-weight: bold;
    }}
    th, td {{ 
      border-bottom: 1px solid #e5e7eb; 
      text-align: center; 
      padding: 8px 12px;
      font-size: 0.95rem;
      width: 8%;
    }}
    /* League table styling - Team Name is 3rd column */
    .league-table th:nth-child(3), .league-table td:nth-child(3) {{
      width: 16%;
      text-align: left;
    }}
    .league-table th:first-child, .league-table td:first-child {{
      text-align: center;
      width: 6%;
    }}
    .league-table th:nth-child(2), .league-table td:nth-child(2) {{
      text-align: center;
    }}
    
    /* MoTM table styling - Team Name is 1st column */
    .dataframe th:first-child, .dataframe td:first-child {{
      width: 16%;
      text-align: left;
    }}
    .dataframe th:nth-child(3), .dataframe td:nth-child(3) {{
      width: 8%;
      text-align: center;
    }}
    
    /* MoTM Schedule table styling */
    .motm-schedule-table th, .motm-schedule-table td {{
      text-align: center;
    }}
    tr.current-motm td {{
      background: #d4edda !important;
      font-weight: bold;
    }}
    
    /* Form table styling - Team Name is 3rd column */
    .form-table th:nth-child(3), .form-table td:nth-child(3) {{
      width: 16%;
      text-align: left;
    }}
    .form-table th:first-child, .form-table td:first-child {{
      text-align: center;
      width: 6%;
    }}
    .form-table th:nth-child(2), .form-table td:nth-child(2) {{
      text-align: center;
      width: 8%;
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
    /* Matchups styling */
    .matchups-container {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 15px;
      margin-top: 20px;
    }}
    .matchup-card {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      background: rgba(255, 255, 255, 0.8);
      border-radius: 12px;
      padding: 15px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      gap: 15px;
    }}
    .team-card {{
      text-align: center;
      padding: 10px;
      border-radius: 8px;
      border: 2px solid transparent;
    }}
    .team-card.win {{
      border-color: #22c55e;
      background: rgba(34, 197, 94, 0.1);
    }}
    .team-card.loss {{
      border-color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
    }}
    .team-card.draw {{
      border-color: #f59e0b;
      background: rgba(245, 158, 11, 0.1);
    }}
    .team-card.pending {{
      border-color: #6b7280;
      background: rgba(107, 114, 128, 0.1);
    }}
    
    .expand-btn {{
      background: none;
      border: none;
      font-size: 14px;
      cursor: pointer;
      margin-left: 5px;
      opacity: 0.7;
      transition: opacity 0.2s;
    }}
    
    .expand-btn:hover {{
      opacity: 1;
    }}
    
    .lineup-section {{
      grid-column: 1 / -1;
      background-color: #f8f9fa;
      padding: 15px;
      border-radius: 8px;
      margin-top: 10px;
      border: 1px solid #e9ecef;
    }}
    
    .lineup-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
    }}
    
    .position-group {{
      background: white;
      padding: 10px;
      border-radius: 6px;
      border: 1px solid #dee2e6;
    }}
    
    .position-group h5 {{
      margin: 0 0 8px 0;
      color: #495057;
      font-size: 14px;
      font-weight: 600;
      text-align: center;
    }}
    
    .player-row {{
      display: flex;
      justify-content: flex-start;
      align-items: center;
      padding: 8px 12px;
      margin-bottom: 4px;
      border-radius: 4px;
      font-size: 14px;
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
    
    .captain-badge {{
      background-color: #007bff;
      color: white;
      font-size: 10px;
      padding: 2px 4px;
      border-radius: 3px;
      font-weight: bold;
      margin-left: 4px;
    }}
    
    .captain-badge.effective {{
      background-color: #28a745;
    }}
    
    .captain-badge.vice {{
      background-color: #6c757d;
    }}
    
    .multiplier-badge {{
      background-color: #dc3545;
      color: white;
      font-size: 9px;
      padding: 1px 4px;
      border-radius: 2px;
      font-weight: bold;
      margin-left: 3px;
    }}
    
    .common-player {{
      font-size: 14px;
      margin-left: 4px;
      color: #007bff;
      font-weight: bold;
    }}
    .team-name {{
      font-weight: bold;
      font-size: 0.9rem;
      margin-bottom: 5px;
      color: #3A083F;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .team-score {{
      font-size: 1.5rem;
      font-weight: bold;
      margin-bottom: 5px;
    }}
    .team-result {{
      font-size: 0.8rem;
      font-weight: bold;
    }}
    .vs-section {{
      text-align: center;
    }}
    .vs-text {{
      font-weight: bold;
      font-size: 1.2rem;
      color: #3A083F;
      margin-bottom: 5px;
    }}
    .score-diff {{
      font-size: 0.8rem;
      color: #6b7280;
      font-style: italic;
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
      font-size: 14px;
      margin-left: 4px;
      color: #28a745;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <h1>
    <img src="logo.PNG" alt="League Logo" class="logo">
    Farmer's Football League 2025-2026
  </h1>
  
  <div style="text-align: center; margin-bottom: 2rem;">
    <a href="index.html" style="color: white; text-decoration: none; background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; margin-right: 10px;">🏠 Home</a>
    <a href="farmers-mobile.html" style="color: white; text-decoration: none; background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 6px; font-size: 0.9rem;">Mobile Version</a>
  </div>

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

  <div class="card">
    <h2 class="large-title">5 Week Form Table</h2>
    {form_table_html}
  </div>

  <div class="card">
    <h2 class="large-title">GW {most_recent_week} Matchups</h2>
    {matchups_html}
  </div>

  <div class="card">
    <h2 class="large-title">Top Scorers of the Week (GW {get_current_lineup_gameweek(lineup_df) or most_recent_week})</h2>
    {top_scorers_html}
  </div>

  <div class="card">
    <h2 class="large-title">Manager of the Month Schedule</h2>
    {motm_schedule_table_html}
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
