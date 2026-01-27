import requests
import json
import pandas as pd
import time
from pathlib import Path

base_url = "https://fantasy.premierleague.com/api/"

def get_current_gameweek():
    """Get the current gameweek from FPL API"""
    bs = requests.get(f"{base_url}bootstrap-static/").json()
    
    # Find the current gameweek
    for event in bs['events']:
        if event['is_current']:
            return event['id']
    
    # If no current gameweek, find the most recent finished one
    for event in bs['events']:
        if event['finished']:
            return event['id']
    
    return 1  # fallback

def get_league_teams(league_id):
    """Get team entries from H2H league results"""
    page = 1
    all_results = []
    
    # Get all H2H results
    while True:
        url = f"{base_url}leagues-h2h-matches/league/{league_id}/?page={page}"
        response = requests.get(url)
        
        if response.status_code == 200:
            league_data = response.json()
            all_results.extend(league_data['results'])
            
            if not league_data['has_next']:
                break
            page += 1
        else:
            print(f"Error getting H2H results: {response.status_code}")
            break
    
    # Extract unique teams from H2H results
    entry_map = {}
    for result in all_results:
        # Add team 1
        if 'entry_1_entry' in result:
            entry_id = result['entry_1_entry']
            team_name = result['entry_1_name']
            player_name = result.get('entry_1_player_name', 'Unknown')
            entry_map[entry_id] = {'team_name': team_name, 'player_name': player_name}
        
        # Add team 2
        if 'entry_2_entry' in result:
            entry_id = result['entry_2_entry']
            team_name = result['entry_2_name']
            player_name = result.get('entry_2_player_name', 'Unknown')
            entry_map[entry_id] = {'team_name': team_name, 'player_name': player_name}
    
    return entry_map

def get_player_data():
    """Get all player data from bootstrap-static"""
    bs = requests.get(f"{base_url}bootstrap-static/").json()
    
    element_map = {e['id']: e.get('web_name', '') for e in bs.get('elements', [])}
    positions_map = {p['id']: p['singular_name_short'] for p in bs.get('element_types', [])}
    element_pos_map = {e['id']: positions_map.get(e.get('element_type'), '') for e in bs.get('elements', [])}
    
    return element_map, element_pos_map

def get_team_lineup_for_gw(entry_id, gameweek, element_map, element_pos_map):
    """Get lineup for a specific team and gameweek"""
    url = f"{base_url}entry/{entry_id}/event/{gameweek}/picks/"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Error getting lineup for entry {entry_id}, GW {gameweek}: {response.status_code}")
            return []
        
        picks_data = response.json()
        picks = picks_data.get('picks', [])
        
        # Get player scores for this gameweek
        player_scores = {}
        for pick in picks:
            element_id = pick['element']
            
            # Get player's score for this gameweek
            player_url = f"{base_url}element-summary/{element_id}/"
            try:
                player_response = requests.get(player_url, timeout=10)
                if player_response.status_code == 200:
                    player_data = player_response.json()
                    
                    # Find score for this specific gameweek
                    for history in player_data.get('history', []):
                        if history['round'] == gameweek:
                            player_scores[element_id] = history['total_points']
                            break
                    
                    if element_id not in player_scores:
                        player_scores[element_id] = 0
                else:
                    player_scores[element_id] = 0
                    
                time.sleep(0.15)  # Rate limiting
                
            except Exception as e:
                print(f"Error getting score for player {element_id}: {e}")
                player_scores[element_id] = 0
        
        lineup = []
        for i, pick in enumerate(picks):
            element_id = pick['element']
            player_name = element_map.get(element_id, f"Player {element_id}")
            position = element_pos_map.get(element_id, "Unknown")
            score = player_scores.get(element_id, 0)
            
            lineup.append({
                'position': i + 1,
                'player_name': player_name,
                'element_id': element_id,
                'position_type': position,
                'score': score,
                'is_captain': pick.get('is_captain', False),
                'is_vice_captain': pick.get('is_vice_captain', False),
                'multiplier': pick.get('multiplier', 1)
            })
        
        return lineup
        
    except Exception as e:
        print(f"Error processing team {entry_id}: {e}")
        return []

def collect_current_gameweek_data(league_id):
    """Collect lineup data for current gameweek only"""
    print("=== Collecting Current Gameweek Data ===")
    
    # Get current gameweek
    current_gw = get_current_gameweek()
    print(f"Current gameweek: {current_gw}")
    
    # Get team entries
    print("Getting team entries...")
    entry_map = get_league_teams(league_id)
    print(f"Found {len(entry_map)} teams")
    
    # Get player data
    print("Getting player data...")
    element_map, element_pos_map = get_player_data()
    
    # Collect lineup data
    all_lineup_data = []
    
    for i, (entry_id, team_info) in enumerate(entry_map.items()):
        print(f"Processing team {i+1}/{len(entry_map)}: {team_info['team_name']}")
        
        lineup = get_team_lineup_for_gw(entry_id, current_gw, element_map, element_pos_map)
        
        for player in lineup:
            all_lineup_data.append({
                'Manager': team_info['player_name'],
                'Team Name': team_info['team_name'],
                'Position': player['position'],
                'Player': player['player_name'],
                'Position Type': player['position_type'],
                f'GW {current_gw} Score': player['score'],
                'Is Captain': player['is_captain'],
                'Is Vice Captain': player['is_vice_captain'],
                'Multiplier': player['multiplier']
            })
        
        # Small delay between teams
        time.sleep(0.5)
    
    # Save to Excel
    if all_lineup_data:
        df = pd.DataFrame(all_lineup_data)
        output_path = Path("data") / "lineup_data.xlsx"
        df.to_excel(output_path, index=False)
        print(f"Saved {len(all_lineup_data)} lineup records to {output_path}")
        return df
    else:
        print("No lineup data collected")
        return None

def main():
    league_id = 388845  # 2025/26 season
    df = collect_current_gameweek_data(league_id)
    
    if df is not None:
        print(f"\n=== Collection Complete ===")
        print(f"Total records: {len(df)}")
        print(f"Teams: {df['Team Name'].nunique()}")
        print(f"Players with scores > 0: {len(df[df[f'GW {get_current_gameweek()} Score'] > 0])}")
    else:
        print("Data collection failed")

if __name__ == "__main__":
    main()