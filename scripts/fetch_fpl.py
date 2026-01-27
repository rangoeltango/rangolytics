from pathlib import Path
import requests
import json
import pandas as pd
import time
import os

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

# Lineup data collection functions (integrated from lineup_sample_script.py)

def extract_entry_map_from_results(results):
    """Extract entry ID to team name mapping from H2H results"""
    entry_map = {}
    for r in results:
        # handle keys like entry_1_entry / entry_1_name etc.
        for id_key, name_key in (("entry_1_entry","entry_1_name"), ("entry_1_entry","entry_1_player_name"),
                                 ("entry_2_entry","entry_2_name"), ("entry_2_entry","entry_2_player_name"),
                                 ("entry_1","entry_1_name"), ("entry_2","entry_2_name")):
            eid = r.get(id_key)
            if eid is None:
                continue
            name = r.get(name_key) or r.get(f"{id_key.replace('_entry','')}_name") or str(eid)
            entry_map.setdefault(eid, name or str(eid))
        # generic fallback for *_entry keys
        for k, v in list(r.items()):
            if k.endswith("_entry") and v is not None:
                nk = k.replace("_entry","_name")
                entry_map.setdefault(v, r.get(nk) or str(v))
    return entry_map

def fetch_entries_from_standings(league_id, sleep=0.05):
    """Fallback method to get entry map from standings if H2H results don't contain entry IDs"""
    page = 1
    entries = {}
    while True:
        url = f"{base_url}leagues-classic-standings/league/{league_id}/?page={page}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            break
        data = r.json()
        results = data.get("standings", {}).get("results") or data.get("results") or []
        for item in results:
            eid = item.get("entry") or item.get("entry_id") or item.get("id")
            name = item.get("player_name") or item.get("entry_name") or item.get("player")
            if eid is not None:
                entries.setdefault(eid, name or str(eid))
        if not data.get("standings", {}).get("has_next") and not data.get("has_next"):
            break
        page += 1
        time.sleep(sleep)
    return entries

def load_cache(cache_file):
    """Load element points cache from disk"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                # Convert string keys back to int
                return {int(k): v for k, v in cache.items()}
        except Exception:
            pass
    return {}

def save_cache(cache, cache_file):
    """Save element points cache to disk"""
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass

def get_existing_gameweeks(lineup_file_path):
    """Determine which gameweeks already have complete lineup data"""
    existing_gws = set()
    if not lineup_file_path.exists():
        return existing_gws
    
    try:
        df = pd.read_excel(lineup_file_path)
        if df.empty:
            return existing_gws
        
        # Check for GW columns that have complete data (non-null players and scores)
        for col in df.columns:
            if col.startswith('GW ') and col.endswith(' Player'):
                gw_num = int(col.split()[1])
                score_col = f'GW {gw_num} Score'
                
                # Check if this GW has complete data (players and scores filled)
                if (score_col in df.columns and 
                    df[col].notna().sum() > 0 and 
                    df[score_col].notna().sum() > 0):
                    existing_gws.add(gw_num)
                    
        print(f"Found existing complete data for gameweeks: {sorted(existing_gws)}")
        return existing_gws
        
    except Exception as e:
        print(f"Could not read existing lineup data: {e}")
        return existing_gws

def get_element_points_for_gw(element_id, gw, cache, timeout=10, sleep=0.1):
    """Fetch element-summary for element_id and cache mapping gw -> points"""
    if element_id is None:
        return None
    if element_id in cache:
        return cache[element_id].get(gw)
    # fetch and build mapping
    url = f"{base_url}element-summary/{element_id}/"
    try:
        print(f"Fetching data for player {element_id}...")
        r = requests.get(url, timeout=timeout)
        if r.status_code == 429:  # Rate limited
            print("Rate limited, waiting 5 seconds...")
            time.sleep(5)
            r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            print(f"Failed to fetch player {element_id}: Status {r.status_code}")
            cache[element_id] = {}
            return None
        j = r.json()
        history = j.get("history", []) or j.get("history_past", []) or []
        gw_map = {}
        for h in history:
            round_num = h.get("round") or h.get("event") or h.get("fixture")
            try:
                round_num = int(round_num)
            except Exception:
                continue
            pts = h.get("points", h.get("total_points"))
            try:
                pts = int(pts) if pts is not None else 0
            except Exception:
                try:
                    pts = int(float(pts))
                except Exception:
                    pts = 0
            gw_map[round_num] = pts
        cache[element_id] = gw_map
        time.sleep(sleep)  # Increased default sleep
        return gw_map.get(gw)
    except Exception as e:
        print(f"Error fetching player {element_id}: {e}")
        cache[element_id] = {}
        return None

def build_lineup_data(entry_map, most_recent_week, max_positions=15, sleep=0.15, timeout=10, start_team=0, batch_size=5, existing_gameweeks=None):
    """Build detailed lineup data for all teams and weeks with optimized processing"""
    if existing_gameweeks is None:
        existing_gameweeks = set()
    
    missing_gws = [gw for gw in range(1, most_recent_week + 1) if gw not in existing_gameweeks]
    
    if not missing_gws:
        print("All gameweek data is already complete!")
        return {}, {}
    
    print(f"Building lineup data for {len(entry_map)} teams...")
    print(f"Missing gameweeks to fetch: {missing_gws}")
    print(f"Processing teams {start_team+1}-{min(start_team+batch_size, len(entry_map))} of {len(entry_map)}")
    
    # Load persistent cache
    cache_file = Path("data") / "element_points_cache.json"
    element_points_cache = load_cache(cache_file)
    print(f"Loaded cache with {len(element_points_cache)} players")
    
    # Get bootstrap data for player names and positions
    print("Fetching player data...")
    bs = requests.get(f"{base_url}bootstrap-static/", timeout=timeout).json()
    element_map = {e['id']: e.get('web_name', '') for e in bs.get('elements', [])}
    positions_map = {p['id']: p['singular_name_short'] for p in bs.get('element_types', [])}
    element_pos_map = {e['id']: positions_map.get(e.get('element_type'), '') for e in bs.get('elements', [])}

    # storage: data[entry_id]['pos_{pos}'][f"GW {gw} Player"] = {name, element_id, position_type, status, score, is_captain, is_vice}
    data = {}
    
    # Process only a batch of teams
    entry_items = list(entry_map.items())
    batch_entries = entry_items[start_team:start_team + batch_size]
    
    for entry_id, entry_name in batch_entries:
        data[entry_id] = {"entry_name": entry_name}
        for pos in range(1, max_positions + 1):
            data[entry_id].setdefault(f"pos_{pos}", {})

    # collect picks and per-player gw scores/captain flags
    total_teams = len(batch_entries)
    for i, (entry_id, entry_name) in enumerate(batch_entries):
        print(f"\n[{i+1}/{total_teams}] Processing team: {entry_name}")
        
        # Get all picks for this team first to identify unique players
        team_players = set()
        team_picks = {}
        
        for gw in missing_gws:
            picks_url = f"{base_url}entry/{entry_id}/event/{gw}/picks/"
            try:
                r = requests.get(picks_url, timeout=timeout)
                if r.status_code == 429:
                    print("Rate limited, waiting...")
                    time.sleep(5)
                    r = requests.get(picks_url, timeout=timeout)
                    
                if r.status_code != 200:
                    print(f"Failed to get picks for GW{gw}: Status {r.status_code}")
                    time.sleep(sleep)
                    continue
                    
                j = r.json()
                picks = j.get("picks") or []
                team_picks[gw] = picks
                
                # Collect unique players for this team
                for p in picks:
                    element = p.get("element") or p.get("element_id") or p.get("player")
                    if element:
                        team_players.add(element)
                        
                time.sleep(sleep * 0.5)  # Reduced sleep for picks
                
            except Exception as exc:
                print(f"Request error entry {entry_id} GW{gw}: {exc}")
                time.sleep(sleep)
                continue
        
        print(f"Found {len(team_players)} unique players, fetching scores...")
        
        # Pre-fetch all player data for this team
        players_fetched = 0
        for element_id in team_players:
            if element_id not in element_points_cache:
                players_fetched += 1
                if players_fetched % 10 == 0:
                    print(f"Fetched {players_fetched}/{len(team_players) - len([p for p in team_players if p in element_points_cache])} players...")
                get_element_points_for_gw(element_id, 1, element_points_cache, timeout=timeout, sleep=sleep)
        
        # Process all gameweeks for this team (only missing gameweeks)
        for gw in missing_gws:
            picks = team_picks.get(gw, [])
            for p in picks:
                element = p.get("element") or p.get("element_id") or p.get("player")
                pos = p.get("position") or p.get("position_in_squad") or p.get("slot")
                try:
                    pos = int(pos)
                except Exception:
                    continue
                if not (1 <= pos <= max_positions):
                    continue

                name = element_map.get(element, "") if element is not None else ""
                multiplier = p.get("multiplier", 1) or 1
                is_start = isinstance(pos, int) and pos <= 11
                status = "Starter" if is_start else "Bench"

                # detect captain/vice flags
                is_captain = bool(p.get("is_captain") or p.get("is_captain", False))
                is_vice = bool(p.get("is_vice_captain") or p.get("is_vice_captain", False))
                # fallback: if no flags but multiplier==2 assume captain
                if not (is_captain or is_vice) and multiplier == 2:
                    is_captain = True

                # Use cached data
                base_pts = element_points_cache.get(element, {}).get(gw)
                scored_pts = None
                if base_pts is None:
                    scored_pts = None
                else:
                    try:
                        scored_pts = int(base_pts) * int(multiplier)
                    except Exception:
                        try:
                            scored_pts = int(float(base_pts) * float(multiplier))
                        except Exception:
                            scored_pts = None

                data[entry_id].setdefault(f"pos_{pos}", {})[f"GW {gw} Player"] = {
                    "name": name,
                    "element_id": element,
                    "position_type": element_pos_map.get(element, ""),
                    "status": status,
                    "score": scored_pts,
                    "is_captain": is_captain,
                    "is_vice": is_vice
                }
        
        # Save cache periodically
        if (i + 1) % 2 == 0:
            save_cache(element_points_cache, cache_file)
            print(f"Cache saved with {len(element_points_cache)} players")

    # determine actual captain used per team per GW (only for missing gameweeks)
    print("\nCalculating effective captains...")
    actual_captain_by_entry = {eid: {} for eid in data.keys()}
    for entry_id, info in data.items():
        for gw in missing_gws:
            picks = []
            for pos in range(1, max_positions + 1):
                cell = info.get(f"pos_{pos}", {}).get(f"GW {gw} Player")
                if isinstance(cell, dict):
                    picks.append(cell)
            # find declared captain and vice
            declared_cap = next((p for p in picks if p.get("is_captain")), None)
            declared_vc = next((p for p in picks if p.get("is_vice")), None)
            
            def positive_score(p):
                sc = p.get("score")
                try:
                    return sc is not None and int(sc) != 0
                except Exception:
                    return False
            
            chosen = None
            if declared_cap and positive_score(declared_cap):
                chosen = declared_cap.get("element_id")
            elif declared_cap and not positive_score(declared_cap):
                if declared_vc and positive_score(declared_vc):
                    chosen = declared_vc.get("element_id")
                else:
                    chosen = None
            else:
                chosen = None
            actual_captain_by_entry[entry_id][gw] = chosen
    
    # Final cache save
    save_cache(element_points_cache, cache_file)
    print(f"Final cache saved with {len(element_points_cache)} players")

    return data, actual_captain_by_entry

def save_lineup_data_to_excel(data, actual_captain_by_entry, entry_map, most_recent_week, out_path, max_positions=15):
    """Convert lineup data to DataFrame and save to Excel"""
    print("Converting lineup data to Excel format...")
    
    # Build aligned rows with stable baseline and keep players aligned across GWs
    rows = []
    for entry_id, info in data.items():
        entry_name = info.get("entry_name", "")
        baseline = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
        first_gw_with_picks = None
        # Check both existing and missing gameweeks to find first GW with picks
        all_gws_to_check = range(1, most_recent_week + 1)
        for gw in all_gws_to_check:
            any_pick = any(info.get(f"pos_{pos}", {}).get(f"GW {gw} Player") for pos in range(1, max_positions + 1))
            if any_pick:
                first_gw_with_picks = gw
                break
        if first_gw_with_picks is None:
            first_gw_with_picks = 1

        # build baseline slots by position type
        for pos in range(1, max_positions + 1):
            cell = info.get(f"pos_{pos}", {}).get(f"GW {first_gw_with_picks} Player")
            if isinstance(cell, dict):
                ptype = cell.get("position_type", "") or ""
                if ptype in baseline:
                    baseline[ptype].append(pos)

        for ptype in ("GKP", "DEF", "MID", "FWD"):
            slots = baseline.get(ptype, [])
            if not slots:
                continue

            # baseline element ids and names
            baseline_elements = []
            baseline_names = []
            for pos in slots:
                cell = info.get(f"pos_{pos}", {}).get(f"GW {first_gw_with_picks} Player")
                if isinstance(cell, dict):
                    baseline_elements.append(cell.get("element_id"))
                    baseline_names.append(cell.get("name", ""))
                else:
                    baseline_elements.append(None)
                    baseline_names.append("")

            # create rows for each baseline slot
            for idx in range(len(baseline_elements)):
                row = {"Team Name": entry_name, "Ind Pos": idx + 1, "Position": ptype}
                # Process all gameweeks (existing data will be preserved, only missing GWs will be added)
                for gw in range(1, most_recent_week + 1):
                    # collect current players of this type in slot order
                    current_players = []
                    for pos in range(1, max_positions + 1):
                        cell = info.get(f"pos_{pos}", {}).get(f"GW {gw} Player")
                        if isinstance(cell, dict) and cell.get("position_type") == ptype:
                            current_players.append({
                                "pos": pos,
                                "name": cell.get("name", ""),
                                "element_id": cell.get("element_id"),
                                "status": cell.get("status", ""),
                                "score": cell.get("score"),
                                "is_captain": cell.get("is_captain", False),
                                "is_vice": cell.get("is_vice", False)
                            })
                    
                    # align current_players to baseline
                    aligned = [None] * len(baseline_elements)
                    used = set()
                    # pass 1: match by baseline element_id
                    for b_i, b_elem in enumerate(baseline_elements):
                        if b_elem is None:
                            continue
                        for c_i, cur in enumerate(current_players):
                            if c_i in used:
                                continue
                            if cur.get("element_id") == b_elem:
                                aligned[b_i] = cur
                                used.add(c_i)
                                break
                    # pass 2: match by baseline name
                    for b_i, bname in enumerate(baseline_names):
                        if aligned[b_i] is not None or not bname:
                            continue
                        for c_i, cur in enumerate(current_players):
                            if c_i in used:
                                continue
                            if cur.get("name") and cur.get("name") == bname:
                                aligned[b_i] = cur
                                used.add(c_i)
                                break
                    # pass 3: fill remaining
                    cur_idx = 0
                    for b_i in range(len(aligned)):
                        if aligned[b_i] is None:
                            while cur_idx < len(current_players) and cur_idx in used:
                                cur_idx += 1
                            if cur_idx < len(current_players):
                                aligned[b_i] = current_players[cur_idx]
                                used.add(cur_idx)
                                cur_idx += 1
                            else:
                                aligned[b_i] = {"name": "", "element_id": None, "status": "", "score": "", "is_captain": False, "is_vice": False}

                    # write aligned values for this GW and baseline idx
                    chosen = aligned[idx] or {"name": "", "element_id": None, "status": "", "score": "", "is_captain": False, "is_vice": False}
                    row[f"GW {gw} Player"] = chosen.get("name", "")
                    row[f"GW {gw} Player ID"] = chosen.get("element_id")
                    row[f"GW {gw} Status"] = chosen.get("status", "")
                    row[f"GW {gw} Score"] = chosen.get("score", "")
                    # GW Sel Cpt (declared)
                    declared = "N/A"
                    if chosen.get("is_captain"):
                        declared = "C"
                    elif chosen.get("is_vice"):
                        declared = "VC"
                    row[f"GW {gw} Sel Cpt"] = declared

                    # GW Eff Cpt (effective captain)
                    actual_cap_elem = actual_captain_by_entry.get(entry_id, {}).get(gw)
                    if actual_cap_elem is None:
                        row[f"GW {gw} Eff Cpt"] = "N/A"
                    else:
                        row[f"GW {gw} Eff Cpt"] = "C" if chosen.get("element_id") == actual_cap_elem else "N/A"
                rows.append(row)

    df_wide = pd.DataFrame(rows)

    # ensure expected columns exist and order them
    gw_blocks = []
    for gw in range(1, most_recent_week + 1):
        gw_blocks.extend([
            f"GW {gw} Player ID",
            f"GW {gw} Player",
            f"GW {gw} Status",
            f"GW {gw} Score",
            f"GW {gw} Sel Cpt",
            f"GW {gw} Eff Cpt"
        ])
    desired_cols = ["Team Name", "Ind Pos", "Position"] + gw_blocks
    df_wide = df_wide.reindex(columns=desired_cols, fill_value="")

    # save to Excel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_wide.to_excel(out_path, index=False, sheet_name="weekly_fantasy_lineups")
    print(f"Lineup data saved to {out_path} ({len(df_wide)} rows)")
    return df_wide

def main():
    print("Starting data collection...")
    
    # Team-level data collection (existing workflow)
    print("\n=== Collecting Team-Level Data ===")
    league_id = 388845  # 2025/26 season
    base_results = get_all_league_info(league_id)
    data, most_recent_week = restructure_results(base_results)
    final_df = pd.DataFrame.from_dict(data, orient="index")
    final_df = calculate_rankings(final_df, most_recent_week)
    
    # Save team-level data to original location
    team_output_path = Path("data") / "league_results.xlsx"
    save_to_excel(final_df, team_output_path)
    print(f"Team data saved: {team_output_path} (latest GW with data: {most_recent_week})")
    
    # Player-level lineup data collection (new integrated workflow)
    print("\n=== Collecting Player-Level Lineup Data ===")
    
    # First try to extract entry map from H2H results
    entry_map = extract_entry_map_from_results(base_results)
    
    # If H2H results don't contain entry IDs, fallback to standings
    if not entry_map:
        print("No entry IDs found in H2H results, fetching from standings...")
        entry_map = fetch_entries_from_standings(league_id)
    
    if not entry_map:
        print("Warning: Could not determine team entries. Skipping lineup data collection.")
        return final_df
    
    print(f"Found {len(entry_map)} teams for lineup data collection")
    print(f"Collecting lineup data through gameweek {most_recent_week}")
    
    # Check for existing data and determine what gameweeks need to be fetched
    existing_lineup_file = Path("data") / "lineup_data.xlsx"
    existing_gameweeks = get_existing_gameweeks(existing_lineup_file)
    
    # If no missing data, skip lineup collection entirely
    missing_gws = [gw for gw in range(1, most_recent_week + 1) if gw not in existing_gameweeks]
    if not missing_gws and existing_lineup_file.exists():
        print("All lineup data is already up to date! Skipping lineup collection.")
        return final_df
    
    # Check for existing partial team data
    start_team = 0
    if existing_lineup_file.exists():
        try:
            existing_df = pd.read_excel(existing_lineup_file)
            processed_teams = existing_df['Team Name'].nunique() if not existing_df.empty else 0
            # Only resume from partial teams if we're fetching missing gameweeks for existing teams
            if len(existing_gameweeks) > 0 and len(missing_gws) < most_recent_week:
                start_team = processed_teams
                print(f"Found existing data for {processed_teams} teams")
        except Exception:
            print("Could not read existing lineup data, starting from beginning")
    
    # Process teams in batches
    batch_size = 3  # Process 3 teams at a time
    total_teams = len(entry_map)
    all_lineup_data = {}
    all_captain_data = {}
    
    while start_team < total_teams:
        remaining_teams = total_teams - start_team
        current_batch_size = min(batch_size, remaining_teams)
        
        print(f"\n=== Processing batch {start_team//batch_size + 1} ({current_batch_size} teams) ===")
        
        try:
            # Build detailed lineup data for this batch
            lineup_data, actual_captain_by_entry = build_lineup_data(
                entry_map, 
                most_recent_week,
                existing_gameweeks=existing_gameweeks,
                max_positions=15,
                sleep=0.15,  # Increased sleep for better rate limiting
                start_team=start_team,
                batch_size=current_batch_size
            )
            
            # Merge with existing data
            all_lineup_data.update(lineup_data)
            all_captain_data.update(actual_captain_by_entry)
            
            # Save incremental progress
            lineup_df = save_lineup_data_to_excel(
                all_lineup_data, 
                all_captain_data, 
                entry_map, 
                most_recent_week, 
                existing_lineup_file
            )
            
            print(f"Batch complete. Total processed: {len(all_lineup_data)}/{total_teams} teams")
            
        except KeyboardInterrupt:
            print("\nProcessing interrupted. Progress saved.")
            break
        except Exception as e:
            print(f"Error in batch processing: {e}")
            print("Continuing to next batch...")
            
        start_team += current_batch_size
        
        if start_team < total_teams:
            print(f"Waiting 3 seconds before next batch...")
            time.sleep(3)
    
    final_lineup_df = None
    if all_lineup_data:
        final_lineup_df = save_lineup_data_to_excel(
            all_lineup_data, 
            all_captain_data, 
            entry_map, 
            most_recent_week, 
            existing_lineup_file
        )
    
    print(f"\n=== Data Collection Complete ===")
    print(f"Team data: {len(final_df)} teams")
    if final_lineup_df is not None:
        print(f"Lineup data: {len(final_lineup_df)} position records for {len(all_lineup_data)} teams")
    else:
        print("Lineup data: Processing incomplete or failed")
    
    return final_df, final_lineup_df

if __name__ == "__main__":
    main()