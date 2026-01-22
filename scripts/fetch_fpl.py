from pathlib import Path
import requests
import pandas as pd

BASE_URL = "https://fantasy.premierleague.com/api/"

def get_all_league_info(league_id: int):
    page = 1
    all_results = []
    while True:
        url = f"{BASE_URL}leagues-h2h-matches/league/{league_id}/?page={page}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        league_data = r.json()
        all_results.extend(league_data["results"])
        if not league_data.get("has_next"):
            break
        page += 1
    return all_results

def restructure_results(results):
    data = {}
    max_event = max(result["event"] for result in results)
    most_recent_week = 0

    for result in results:
        event = result["event"]
        entry_1 = result["entry_1_name"]
        entry_2 = result["entry_2_name"]

        for entry_key, owner_key in [(entry_1, "entry_1_owner"), (entry_2, "entry_2_owner")]:
            if entry_key not in data:
                data[entry_key] = {"Team Name": entry_key, "Owner Name": result.get(owner_key, "N/A")}
                for e in range(1, max_event + 1):
                    data[entry_key][f"Wk {e} Score"] = None
                    data[entry_key][f"Wk {e} Opponent Team"] = None
                    data[entry_key][f"Wk {e} Opponent Score"] = None
                    data[entry_key][f"Wk {e} Result"] = None
                    data[entry_key][f"Wk {e} Points"] = None
                    data[entry_key][f"Wk {e} FFPts"] = None

        # future week
        if result["entry_1_points"] == 0 and result["entry_2_points"] == 0:
            if data[entry_1][f"Wk {event} Score"] is None:
                data[entry_1][f"Wk {event} Score"] = 0
                data[entry_1][f"Wk {event} Opponent Team"] = entry_2
                data[entry_1][f"Wk {event} Opponent Score"] = 0
                data[entry_1][f"Wk {event} Result"] = "TBD"
                data[entry_1][f"Wk {event} Points"] = 0
                data[entry_1][f"Wk {event} FFPts"] = 0

            if data[entry_2][f"Wk {event} Score"] is None:
                data[entry_2][f"Wk {event} Score"] = 0
                data[entry_2][f"Wk {event} Opponent Team"] = entry_1
                data[entry_2][f"Wk {event} Opponent Score"] = 0
                data[entry_2][f"Wk {event} Result"] = "TBD"
                data[entry_2][f"Wk {event} Points"] = 0
                data[entry_2][f"Wk {event} FFPts"] = 0
        else:
            data[entry_1][f"Wk {event} Score"] = result["entry_1_points"]
            data[entry_1][f"Wk {event} Opponent Team"] = entry_2
            data[entry_1][f"Wk {event} Opponent Score"] = result["entry_2_points"]
            data[entry_1][f"Wk {event} Result"] = (
                "W" if result["entry_1_points"] > result["entry_2_points"]
                else "L" if result["entry_1_points"] < result["entry_2_points"]
                else "D"
            )
            data[entry_1][f"Wk {event} Points"] = 3 if result["entry_1_points"] > result["entry_2_points"] else 1 if result["entry_1_points"] == result["entry_2_points"] else 0

            data[entry_2][f"Wk {event} Score"] = result["entry_2_points"]
            data[entry_2][f"Wk {event} Opponent Team"] = entry_1
            data[entry_2][f"Wk {event} Opponent Score"] = result["entry_1_points"]
            data[entry_2][f"Wk {event} Result"] = (
                "W" if result["entry_2_points"] > result["entry_1_points"]
                else "L" if result["entry_2_points"] < result["entry_1_points"]
                else "D"
            )
            data[entry_2][f"Wk {event} Points"] = 3 if result["entry_2_points"] > result["entry_1_points"] else 1 if result["entry_2_points"] == result["entry_1_points"] else 0

            if result["entry_1_points"] > 0 or result["entry_2_points"] > 0:
                most_recent_week = max(most_recent_week, event)

    return data, most_recent_week

def calculate_ffpts(df, most_recent_week):
    for week in range(1, most_recent_week + 1):
        score_col = f"Wk {week} Score"
        ffpts_col = f"Wk {week} FFPts"
        if score_col in df.columns:
            week_scores = df[score_col].dropna()
            if len(week_scores) > 0:
                pairs = [(score, idx) for idx, score in week_scores.items()]
                pairs.sort(key=lambda x: x[0], reverse=True)

                score_to_ffpts = {}
                position = 0
                i = 0
                while i < len(pairs):
                    current_score = pairs[i][0]
                    teams_with_score = 1
                    j = i + 1
                    while j < len(pairs) and pairs[j][0] == current_score:
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

    ffpts_cols = [f"Wk {week} FFPts" for week in range(1, most_recent_week + 1) if f"Wk {week} FFPts" in df.columns]
    df["Total FFPts"] = df[ffpts_cols].sum(axis=1) if ffpts_cols else 0
    return df

def calculate_rankings(df, most_recent_week):
    df = calculate_ffpts(df, most_recent_week)

    for col in df.columns:
        if "Result" in col:
            week_num = col.split()[1]
            df[f"Wk {week_num} Points"] = df.apply(
                lambda row: 0 if row[f"Wk {week_num} Result"] == "TBD" else row[f"Wk {week_num} Points"],
                axis=1,
            )

    df["Total Points"] = df[[c for c in df.columns if "Points" in c and "FFPts" not in c]].sum(axis=1)
    df["Total Score"] = df[[c for c in df.columns if "Score" in c and "Opponent" not in c]].sum(axis=1)

    result_cols = [f"Wk {gw} Result" for gw in range(1, most_recent_week + 1) if f"Wk {gw} Result" in df.columns]
    if result_cols:
        df["W"] = df[result_cols].apply(lambda r: sum(v == "W" for v in r), axis=1)
        df["D"] = df[result_cols].apply(lambda r: sum(v == "D" for v in r), axis=1)
        df["L"] = df[result_cols].apply(lambda r: sum(v == "L" for v in r), axis=1)
    else:
        df["W"] = df["D"] = df["L"] = 0

    df = df.sort_values(by=["Total Points", "Total Score"], ascending=[False, False])
    df["Rank"] = range(1, len(df) + 1)
    return df

def save_to_excel(df, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path) as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)

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