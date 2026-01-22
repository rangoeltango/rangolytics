from pathlib import Path
import requests
import json
import pandas as pd

base_url = "https://fantasy.premierleague.com/api/"

def get_all_league_info(league_id):
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

def restructure_results(results):
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
            # Future week
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
            
            data[entry_2][f'Wk {event} Score'] = result['entry_2_points']
            data[entry_2][f'Wk {event} Opponent Team'] = entry_1
            data[entry_2][f'Wk {event} Opponent Score'] = result['entry_1_points']
            data[entry_2][f'Wk {event} Result'] = 'W' if result['entry_2_points'] > result['entry_1_points'] else 'L' if result['entry_2_points'] < result['entry_1_points'] else 'D'
            data[entry_2][f'Wk {event} Points'] = 3 if result['entry_2_points'] > result['entry_1_points'] else 1 if result['entry_2_points'] == result['entry_1_points'] else 0
            
            if result['entry_1_points'] > 0 or result['entry_2_points'] > 0:
                most_recent_week = max(most_recent_week, event)
    
    print(f'Last gameweek with data: Week {most_recent_week}')
    return data, most_recent_week

def calculate_ffpts(df, most_recent_week):
    for week in range(1, most_recent_week + 1):
        score_col = f'Wk {week} Score'
        ffpts_col = f'Wk {week} FFPts'
        
        if score_col in df.columns:
            week_scores = df[score_col].dropna()
            if len(week_scores) > 0:
                score_team_pairs = [(score, idx) for idx, score in week_scores.items()]
                score_team_pairs.sort(key=lambda x: x[0], reverse=True)
                
                score_to_ffpts = {}
                position = 0
                
                i = 0
                while i < len(score_team_pairs):
                    current_score = score_team_pairs[i][0]
                    
                    teams_with_score = 1
                    j = i + 1
                    while j < len(score_team_pairs) and score_team_pairs[j][0] == current_score:
                        teams_with_score += 1
                        j += 1
                    
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
                    
                    score_to_ffpts[current_score] = ffpts
                    position += teams_with_score
                    i = j
                
                df[ffpts_col] = df[score_col].map(score_to_ffpts).fillna(0)
            else:
                df[ffpts_col] = 0
        else:
            df[ffpts_col] = 0
    
    ffpts_cols = [f'Wk {week} FFPts' for week in range(1, most_recent_week + 1) if f'Wk {week} FFPts' in df.columns]
    if ffpts_cols:
        df['Total FFPts'] = df[ffpts_cols].sum(axis=1)
    else:
        df['Total FFPts'] = 0
    
    return df

def calculate_rankings(df, most_recent_week):
    df = calculate_ffpts(df, most_recent_week)
    
    # Exclude future weeks with 'TBD' results from the total points calculation
    for col in df.columns:
        if 'Result' in col:
            week_num = col.split()[1]
            df[f'Wk {week_num} Points'] = df.apply(lambda row: 0 if row[f'Wk {week_num} Result'] == 'TBD' else row[f'Wk {week_num} Points'], axis=1)
    
    # Calculate total points and total scores for each team
    df['Total Points'] = df[[col for col in df.columns if 'Points' in col and 'FFPts' not in col]].sum(axis=1)
    df['Total Score'] = df[[col for col in df.columns if 'Score' in col and 'Opponent' not in col]].sum(axis=1)
    
    # Compute W / D / L counts
    result_cols = [f'Wk {gw} Result' for gw in range(1, most_recent_week + 1) if f'Wk {gw} Result' in df.columns]
    if result_cols:
        df['W'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'W'), axis=1)
        df['D'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'D'), axis=1)
        df['L'] = df[result_cols].apply(lambda r: sum(1 for v in r if v == 'L'), axis=1)
    else:
        df['W'] = df['D'] = df['L'] = 0
    
    # Add FFPts metrics
    df['FFPts Rank'] = df['Total FFPts'].rank(ascending=False, method='min').astype(int)
    highest_ffpts = df['Total FFPts'].max()
    df['FFPts Behind'] = df['Total FFPts'] - highest_ffpts
    df['FFPts Avg'] = df['Total FFPts'] / most_recent_week
    
    # MoTM calculations (Manager of the Month)
    motm_periods = {
        1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12, 13], 5: [14, 15, 16],
        6: [17, 18, 19, 20], 7: [21, 22, 23, 24], 8: [25, 26, 27, 28], 9: [29, 30, 31], 10: [32, 33, 34, 35]
    }
    
    for motm_num, weeks in motm_periods.items():
        score_cols = [f'Wk {w} Score' for w in weeks if f'Wk {w} Score' in df.columns]
        points_cols = [f'Wk {w} Points' for w in weeks if f'Wk {w} Points' in df.columns]
        
        if score_cols:
            df[f'MoTM {motm_num} Score'] = df[score_cols].sum(axis=1)
        if points_cols:
            df[f'MoTM {motm_num} Points'] = df[points_cols].sum(axis=1)
        
        if f'MoTM {motm_num} Score' in df.columns:
            highest_motm_score = df[f'MoTM {motm_num} Score'].max()
            df[f'MoTM {motm_num} Score Behind'] = df[f'MoTM {motm_num} Score'] - highest_motm_score
    
    # Other metrics
    highest_score = df['Total Score'].max()
    df['Behind Highest Score'] = df['Total Score'] - highest_score
    
    # 5 Week Score
    df['5 Week Score'] = df.apply(lambda row: sum([row[f'Wk {week} Score'] for week in range(most_recent_week, most_recent_week-5, -1) if f'Wk {week} Score' in df.columns]), axis=1)
    highest_5wk_score = df['5 Week Score'].max()
    df['Behind Highest 5Wk Score'] = df['5 Week Score'] - highest_5wk_score
    df['5 Week Rank'] = df['5 Week Score'].rank(ascending=False, method='min').astype(int)
    
    # Sort teams and assign ranks
    df = df.sort_values(by=['Total Points', 'Total Score'], ascending=[False, False])
    df['Rank'] = range(1, len(df) + 1)
    
    # Reorder columns
    desired_order = ['Rank', 'FFPts Rank', 'FFPts Behind', 'FFPts Avg', '5 Week Rank']
    df = df[desired_order + [col for col in df.columns if col not in desired_order]]
    
    return df

def save_to_excel(df, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path) as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
    print(f"Data saved to {out_path}")

def main():
    league_id = 388845  # 2025/26 season
    results = get_all_league_info(league_id)
    data, most_recent_week = restructure_results(results)
    df = pd.DataFrame.from_dict(data, orient="index")
    df = calculate_rankings(df, most_recent_week)
    
    out_path = Path("data") / "league_results.xlsx"
    save_to_excel(df, out_path)
    print(f"Saved: {out_path} (latest GW with data: {most_recent_week})")

if __name__ == "__main__":
    main()