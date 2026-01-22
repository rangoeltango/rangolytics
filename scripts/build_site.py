from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sample.csv"
OUT_DIR = ROOT / "site"
OUT_FILE = OUT_DIR / "index.html"

def main():
    df = pd.read_excel(ROOT / "data" / "league_results.xlsx", sheet_name="Sheet1")

    display_cols = ["Rank", "Team Name", "Owner Name", "W", "D", "L", "Total Score", "Total Points", "Total FFPts"]
    display_cols = [c for c in display_cols if c in df.columns]
    table_html = df[display_cols].sort_values("Rank").to_html(index=False)

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
  <h1>My Data MVP</h1>
  <p class="muted">Auto-published with GitHub Actions + Pages.</p>

  <div class="kpis">
    <div class="kpi"><div class="muted">Latest date</div><div><b>{latest_date}</b></div></div>
    <div class="kpi"><div class="muted">Total value</div><div><b>{total:.0f}</b></div></div>
    <div class="kpi"><div class="muted">Average value</div><div><b>{avg:.2f}</b></div></div>
  </div>

  <div class="card">
    <h2>Latest rows</h2>
    {table_html}
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
