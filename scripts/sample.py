import requests
import json
import pandas as pd

base_url = "https://fantasy.premierleague.com/api/"

def get_all_league_info(league_id): ## Grabs all pages of history for league
    page = 1
    all_results = []

    while True:
        url = f"{base_url}leagues-h2h-matches/league/{league_id}/?page={page}"
        response = requests.get(url)

        print(f"Request URL: {url}")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            league_data = response.json()
            all_results.extend(league_data['results'])

            if not league_data['has_next']:
                break
            page += 1
        else:
            print("League not found")
            break
    return all_results


def print_league_info(league_id, page=1):
    url = f"{base_url}leagues-h2h-matches/league/{league_id}/?page={page}"
    response = requests.get(url)

    if response.status_code == 200:
        league_data = response.json()
        return league_data
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None

# Replace with your league ID
#league_id = 611235 # 2024/25 Season
league_id = 388845 # 2025/26 Season

# Fetch the first page of league data
league_data = print_league_info(league_id)

# Print the JSON response in a readable format
if league_data:
    print(json.dumps(league_data, indent=4))
else:
    print("No data received.")



def restructure_results(results): # Takes League history and restructures it into a DataFrame
    data = {}
    max_event = max(result['event'] for result in results)
    most_recent_week = 0

    for result in results:
        event = result['event']
        entry_1 = result['entry_1_name']
        entry_2 = result['entry_2_name']

        if entry_1 not in data:
            data[entry_1] = {
                'Team Name': entry_1,
                'Owner Name': result.get('entry_1_owner', 'N/A')
            }
            for e in range(1, max_event + 1):
                data[entry_1][f'Wk {e} Score'] = None
                data[entry_1][f'Wk {e} Opponent Team'] = None
                data[entry_1][f'Wk {e} Opponent Score'] = None
                data[entry_1][f'Wk {e} Result'] = None
                data[entry_1][f'Wk {e} Points'] = None
                data[entry_1][f'Wk {e} FFPts'] = None

        if entry_2 not in data:
            data[entry_2] = {
                'Team Name': entry_2,
                'Owner Name': result.get('entry_2_owner', 'N/A')
            }
            for e in range(1, max_event + 1):
                data[entry_2][f'Wk {e} Score'] = None
                data[entry_2][f'Wk {e} Opponent Team'] = None
                data[entry_2][f'Wk {e} Opponent Score'] = None
                data[entry_2][f'Wk {e} Result'] = None
                data[entry_2][f'Wk {e} Points'] = None
                data[entry_2][f'Wk {e} FFPts'] = None

        if result['entry_1_points'] == 0 and result['entry_2_points'] == 0:
            # Assume it's a future week
            if data[entry_1][f'Wk {event} Score'] is None:
                data[entry_1][f'Wk {event} Score'] = 0
                data[entry_1][f'Wk {event} Opponent Team'] = entry_2
                data[entry_1][f'Wk {event} Opponent Score'] = 0
                data[entry_1][f'Wk {event} Result'] = 'TBD'
                data[entry_1][f'Wk {event} Points'] = 0
                data[entry_1][f'Wk {event} FFPts'] = 0

            if data[entry_2][f'Wk {event} Score'] is None:
                data[entry_2][f'Wk {event} Score'] = 0
                data[entry_2][f'Wk {event} Opponent Team'] = entry_1
                data[entry_2][f'Wk {event} Opponent Score'] = 0
                data[entry_2][f'Wk {event} Result'] = 'TBD'
                data[entry_2][f'Wk {event} Points'] = 0
                data[entry_2][f'Wk {event} FFPts'] = 0
        else:
            data[entry_1][f'Wk {event} Score'] = result['entry_1_points']
            data[entry_1][f'Wk {event} Opponent Team'] = entry_2
            data[entry_1][f'Wk {event} Opponent Score'] = result['entry_2_points']
            data[entry_1][f'Wk {event} Result'] = 'W' if result['entry_1_points'] > result['entry_2_points'] else 'L' if result['entry_1_points'] < result['entry_2_points'] else 'D'
            data[entry_1][f'Wk {event} Points'] = 3 if result['entry_1_points'] > result['entry_2_points'] else 1 if result['entry_1_points'] == result['entry_2_points'] else 0
            # FFPts will be calculated later after all scores are collected

            data[entry_2][f'Wk {event} Score'] = result['entry_2_points']
            data[entry_2][f'Wk {event} Opponent Team'] = entry_1
            data[entry_2][f'Wk {event} Opponent Score'] = result['entry_1_points']
            data[entry_2][f'Wk {event} Result'] = 'W' if result['entry_2_points'] > result['entry_1_points'] else 'L' if result['entry_2_points'] < result['entry_1_points'] else 'D'
            data[entry_2][f'Wk {event} Points'] = 3 if result['entry_2_points'] > result['entry_1_points'] else 1 if result['entry_2_points'] == result['entry_1_points'] else 0
            # FFPts will be calculated later after all scores are collected
            
            # Update most_recent_week if this event has non-zero scores
            if result['entry_1_points'] > 0 or result['entry_2_points'] > 0:
                most_recent_week = max(most_recent_week, event)
    
    print(f'Last gameweek with data: Week {most_recent_week}')
    return data, most_recent_week

def calculate_ffpts(df, most_recent_week):
    """Calculate FFPts for each week based on score rankings"""
    # For each week with actual results (not TBD)
    for week in range(1, most_recent_week + 1):
        score_col = f'Wk {week} Score'
        ffpts_col = f'Wk {week} FFPts'
        
        if score_col in df.columns:
            # Get all scores for this week (exclude TBD/future weeks)
            week_scores = df[score_col].dropna()
            if len(week_scores) > 0:
                # Create a list of (score, team_index) pairs and sort by score descending
                score_team_pairs = [(score, idx) for idx, score in week_scores.items()]
                score_team_pairs.sort(key=lambda x: x[0], reverse=True)
                
                # Assign FFPts based on position, handling ties properly
                score_to_ffpts = {}
                position = 0
                
                i = 0
                while i < len(score_team_pairs):
                    current_score = score_team_pairs[i][0]
                    
                    # Count how many teams have this score
                    teams_with_score = 1
                    j = i + 1
                    while j < len(score_team_pairs) and score_team_pairs[j][0] == current_score:
                        teams_with_score += 1
                        j += 1
                    
                    # Determine FFPts bracket based on current position
                    if position < 4:
                        ffpts = 5
                    elif position < 8:
                        ffpts = 4
                    elif position < 12:
                        ffpts = 3
                    elif position < 16:
                        ffpts = 2
                    else:
                        ffpts = 1
                    
                    # Assign the same FFPts to all teams with this score
                    score_to_ffpts[current_score] = ffpts
                    
                    # Move to next position group
                    position += teams_with_score
                    i = j
                
                # Apply FFPts to each team
                df[ffpts_col] = df[score_col].map(score_to_ffpts).fillna(0)
            else:
                df[ffpts_col] = 0
        else:
            df[ffpts_col] = 0
    
    # Calculate Total FFPts
    ffpts_cols = [f'Wk {week} FFPts' for week in range(1, most_recent_week + 1) if f'Wk {week} FFPts' in df.columns]
    if ffpts_cols:
        df['Total FFPts'] = df[ffpts_cols].sum(axis=1)
    else:
        df['Total FFPts'] = 0
    
    return df

def calculate_rankings(df, most_recent_week): # Calculates the rankings for the league based on the results
    # First calculate FFPts
    df = calculate_ffpts(df, most_recent_week)
    
    # Exclude future weeks with 'TBD' results from the total points calculation
    for col in df.columns:
        if 'Result' in col:
            week_num = col.split()[1]
            df[f'Wk {week_num} Points'] = df.apply(lambda row: 0 if row[f'Wk {week_num} Result'] == 'TBD' else row[f'Wk {week_num} Points'], axis=1)

    # Calculate total points and total scores for each team
    df['Total Points'] = df[[col for col in df.columns if 'Points' in col and 'FFPts' not in col]].sum(axis=1)
    df['Total Score'] = df[[col for col in df.columns if 'Score' in col and 'Opponent' not in col]].sum(axis=1)

    # Compute W / D / L counts based on available 'Wk X Result' columns (ignore TBD / NaN)
    result_cols = [f'Wk {gw} Result' for gw in range(1, most_recent_week + 1) if f'Wk {gw} Result' in df.columns]
    if result_cols:
        df['W'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'W'), axis=1)
        df['D'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'D'), axis=1)
        df['L'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'L'), axis=1)
    else:
        df['W'] = 0
        df['D'] = 0
        df['L'] = 0

    # Add FFPts Rank and FFPts Behind
    df['FFPts Rank'] = df['Total FFPts'].rank(ascending=False, method='min').astype(int)
    
    # Calculate the highest Total FFPts
    highest_ffpts = df['Total FFPts'].max()
    
    # Add FFPts Behind column (negative values showing how far behind the leader each team is)
    df['FFPts Behind'] = df['Total FFPts'] - highest_ffpts
    
    # Add FFPts Avg column (Total FFPts divided by number of weeks with data)
    df['FFPts Avg'] = df['Total FFPts'] / most_recent_week

    # MoTM 1 (Wk 1-3)
    df['MoTM 1 Score'] = df[['Wk 1 Score', 'Wk 2 Score', 'Wk 3 Score']].sum(axis=1)
    df['MoTM 1 Points'] = df[['Wk 1 Points', 'Wk 2 Points', 'Wk 3 Points']].sum(axis=1)

    # MoTM 2 (Wk 4-6)
    df['MoTM 2 Score'] = df[['Wk 4 Score', 'Wk 5 Score', 'Wk 6 Score']].sum(axis=1)
    df['MoTM 2 Points'] = df[['Wk 4 Points', 'Wk 5 Points', 'Wk 6 Points']].sum(axis=1)

    # MoTM 3 (Wk 7-9)
    df['MoTM 3 Score'] = df[['Wk 7 Score', 'Wk 8 Score', 'Wk 9 Score']].sum(axis=1)
    df['MoTM 3 Points'] = df[['Wk 7 Points', 'Wk 8 Points', 'Wk 9 Points']].sum(axis=1)

    # MoTM 4 (Wk 10-13)
    df['MoTM 4 Score'] = df[['Wk 10 Score', 'Wk 11 Score', 'Wk 12 Score', 'Wk 13 Score']].sum(axis=1)
    df['MoTM 4 Points'] = df[['Wk 10 Points', 'Wk 11 Points', 'Wk 12 Points', 'Wk 13 Points']].sum(axis=1)

    # MoTM 5 (Wk 14-16)
    df['MoTM 5 Score'] = df[['Wk 14 Score', 'Wk 15 Score', 'Wk 16 Score']].sum(axis=1)
    df['MoTM 5 Points'] = df[['Wk 14 Points', 'Wk 15 Points', 'Wk 16 Points']].sum(axis=1)

    # MoTM 6 (Wk 17-20)
    df['MoTM 6 Score'] = df[['Wk 17 Score', 'Wk 18 Score', 'Wk 19 Score', 'Wk 20 Score']].sum(axis=1)
    df['MoTM 6 Points'] = df[['Wk 17 Points', 'Wk 18 Points', 'Wk 19 Points', 'Wk 20 Points']].sum(axis=1)

    # MoTM 7 (Wk 21-24)
    df['MoTM 7 Score'] = df[['Wk 21 Score', 'Wk 22 Score', 'Wk 23 Score', 'Wk 24 Score']].sum(axis=1)
    df['MoTM 7 Points'] = df[['Wk 21 Points', 'Wk 22 Points', 'Wk 23 Points', 'Wk 24 Points']].sum(axis=1)

    # MoTM 8 (Wk 25-28)
    df['MoTM 8 Score'] = df[['Wk 25 Score', 'Wk 26 Score', 'Wk 27 Score', 'Wk 28 Score']].sum(axis=1)
    df['MoTM 8 Points'] = df[['Wk 25 Points', 'Wk 26 Points', 'Wk 27 Points', 'Wk 28 Points']].sum(axis=1)

    # MoTM 9 (Wk 29-31)
    df['MoTM 9 Score'] = df[['Wk 29 Score', 'Wk 30 Score', 'Wk 31 Score']].sum(axis=1)
    df['MoTM 9 Points'] = df[['Wk 29 Points', 'Wk 30 Points', 'Wk 31 Points']].sum(axis=1)

    # MoTM 10 (Wk 32-35)
    df['MoTM 10 Score'] = df[['Wk 32 Score', 'Wk 33 Score', 'Wk 34 Score', 'Wk 35 Score']].sum(axis=1)
    df['MoTM 10 Points'] = df[['Wk 32 Points', 'Wk 33 Points', 'Wk 34 Points', 'Wk 35 Points']].sum(axis=1)

    # MoTM 1
    highest_motm_1_score = df['MoTM 1 Score'].max()
    df['MoTM 1 Score Behind'] = df['MoTM 1 Score'] - highest_motm_1_score

    # MoTM 2
    highest_motm_2_score = df['MoTM 2 Score'].max()
    df['MoTM 2 Score Behind'] = df['MoTM 2 Score'] - highest_motm_2_score

    # MoTM 3
    highest_motm_3_score = df['MoTM 3 Score'].max()
    df['MoTM 3 Score Behind'] = df['MoTM 3 Score'] - highest_motm_3_score

    # MoTM 4
    highest_motm_4_score = df['MoTM 4 Score'].max()
    df['MoTM 4 Score Behind'] = df['MoTM 4 Score'] - highest_motm_4_score

    # MoTM 5
    highest_motm_5_score = df['MoTM 5 Score'].max()
    df['MoTM 5 Score Behind'] = df['MoTM 5 Score'] - highest_motm_5_score

    # MoTM 6
    highest_motm_6_score = df['MoTM 6 Score'].max()
    df['MoTM 6 Score Behind'] = df['MoTM 6 Score'] - highest_motm_6_score

    # MoTM 7
    highest_motm_7_score = df['MoTM 7 Score'].max()
    df['MoTM 7 Score Behind'] = df['MoTM 7 Score'] - highest_motm_7_score

    # MoTM 8
    highest_motm_8_score = df['MoTM 8 Score'].max()
    df['MoTM 8 Score Behind'] = df['MoTM 8 Score'] - highest_motm_8_score

    # MoTM 9
    highest_motm_9_score = df['MoTM 9 Score'].max()
    df['MoTM 9 Score Behind'] = df['MoTM 9 Score'] - highest_motm_9_score

    # MoTM 10
    highest_motm_10_score = df['MoTM 10 Score'].max()
    df['MoTM 10 Score Behind'] = df['MoTM 10 Score'] - highest_motm_10_score

    # Calculate the highest total score
    highest_score = df['Total Score'].max()

    # Add a new column 'Behind Highest Score'
    df['Behind Highest Score'] = df['Total Score'] - highest_score

    # Calculate 5 Week Score
    df['5 Week Score'] = df.apply(lambda row: sum([row[f'Wk {week} Score'] for week in range(most_recent_week, most_recent_week-5, -1) if f'Wk {week} Score' in df.columns]), axis=1)
    print(f"Last 5 weeks: Week {most_recent_week} to Week {most_recent_week-4}")
    
    # Calculate the highest 5 Week Score
    highest_5wk_score = df['5 Week Score'].max()  

    # Add a new column 'Behind Highest 5Wk Score'
    df['Behind Highest 5Wk Score'] = df['5 Week Score'] - highest_5wk_score

    # Add a new column '5 Week Rank'
    df['5 Week Rank'] = df['5 Week Score'].rank(ascending=False, method='min').astype(int)
    
    # Sort teams by total points and total scores
    df = df.sort_values(by=['Total Points', 'Total Score'], ascending=[False, False])

    # Assign ranks
    df['Rank'] = range(1, len(df) + 1)

    # Reorder columns: Rank, FFPts Rank, FFPts Behind, FFPts Avg, 5 Week Rank, then the rest
    desired_order = ['Rank', 'FFPts Rank', 'FFPts Behind', 'FFPts Avg', '5 Week Rank']
    df = df[desired_order + [col for col in df.columns if col not in desired_order]]
    
    return df

def calculate_streak(row, latest_gw):
    result_columns = [f'Wk {gw} Result' for gw in range(latest_gw, 0, -1)]

    streak_type = None
    streak_length = 0

    for col in result_columns:
        result = row[col]
        if pd.isna(result) or result == 'TBD':
            continue  # Skip blank or future GWs
        if streak_type is None:
            streak_type = result
            streak_length = 1
        elif result == streak_type:
            streak_length += 1
        else:
            break  # Streak broken

    return f"{streak_type}{streak_length}" if streak_type else "N/A"

def calculate_WDL_streaks(df, latest_gw):
# Get all 'Week X Result' columns
    result_columns = [f'Wk {gw} Result' for gw in range(latest_gw, 0, -1)]

    # Create new columns: Wins, Draws, Losses
    df['Wins'] = df[result_columns].apply(lambda row: sum(r == 'W' for r in row), axis=1)
    df['Draws'] = df[result_columns].apply(lambda row: sum(r == 'D' for r in row), axis=1)
    df['Losses'] = df[result_columns].apply(lambda row: sum(r == 'L' for r in row), axis=1)




    # Preview the new table
    df[['Rank','Team Name', 'Wins', 'Draws', 'Losses', 'Total Score', 'Total Points']]

    print("W-D-L calculated for each team.")
    ## STREAK CALCULATIONS
    
    calculate_streak(df, latest_gw)  # Calculate the current streak for each team
    return df

def calculate_streak(row, latest_gw):
    result_columns = [f'Wk {gw} Result' for gw in range(latest_gw, 0, -1)]

    streak_type = None
    streak_length = 0

    for col in result_columns:
        result = row[col]
        if pd.isna(result) or result == 'TBD':
            continue  # Skip blank or future GWs
        if streak_type is None:
            streak_type = result
            streak_length = 1
        elif result == streak_type:
            streak_length += 1
        else:
            break  # Streak broken

    return f"{streak_type}{streak_length}" if streak_type else "N/A"

def SOMETHING(df, latest_gw): # Placeholder for any additional calculations or modifications

    # Step 4: Build a list of result columns, newest to oldest, ONLY up to the current week
    result_columns = [f'Wk {gw} Result' for gw in range(latest_gw, 0, -1)]

    # Step 5: Function to calculate current streak for each row
    def calculate_streak(row):
        streak_type = None
        streak_length = 0

        for col in result_columns:
            result = row[col]
            if pd.isna(result) or result == 'TBD':
                continue  # Skip blank or future GWs
            if streak_type is None:
                streak_type = result
                streak_length = 1
            elif result == streak_type:
                streak_length += 1
            else:
                break  # Streak broken

        return f"{streak_type}{streak_length}" if streak_type else "N/A"

    # Step 6: Apply the function to each team
    df['Active Streak'] = df.apply(calculate_streak, axis=1)

def save_to_excel_with_calculated_stats(df, file_path): # Saves the resulting DataFrame to an Excel file with one tab
    with pd.ExcelWriter(file_path) as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    print(f"Data saved to {file_path} with one tab: 'Sheet1'")


############ ACTUAL CALL TO GET LEAGUE DATA ############
PRINT_MODE = False

#league_id = 611235 # 2024/25 Season
league_id = 388845 # 2025/26 Season

if PRINT_MODE:
    print_league_info(league_id)  # PRINT FOR RESEARCH ONLY (OTHERWISE BELOW IS NORMAL OPERATION)

else:
    all_league_info = get_all_league_info(league_id)
    restructured_data, most_recent_week = restructure_results(all_league_info)

    if len(restructured_data) > 0:
        df = pd.DataFrame.from_dict(restructured_data, orient='index')

        # Calculate rankings
        df = calculate_rankings(df, most_recent_week)

        # Save to Excel with one tab
        save_to_excel_with_calculated_stats(df, 'C:/Users/randy/OneDrive/Desktop/FPL/DATA/2025/1_league_results_2025.xlsx')
        save_to_excel_with_calculated_stats(df, 'C:/Users/randy/OneDrive/Desktop/FPL/DATA/2025/league_results_2025.xlsx')
        save_to_excel_with_calculated_stats(df, 'C:/Users/randy/OneDrive/Desktop/footyapi/GABI/league_results_2025.xlsx')
    else:
        print("No data to process.")

    print("FPL BOT COMPLETE")