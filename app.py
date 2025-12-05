import os
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd


CSV_PATH = "Generative AI Tools - Platforms 2025.csv"
WHITEPAPER_PATH = "Velar WhitePaper.pdf"
CSV_PATH = os.environ.get("VELAR_DATA_CSV", CSV_PATH)
WHITEPAPER_PATH = os.environ.get("VELAR_WHITEPAPER", WHITEPAPER_PATH)

app = Flask(__name__, static_folder="static", template_folder="templates")

def load_dataset(path=CSV_PATH):
    df = pd.read_csv(path)
    # Normalize column names (strip)
    df.columns = [c.strip() for c in df.columns]
    # Basic typed conversions (where obvious)
    if "release_year" in df.columns:
        df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce").fillna(0).astype(int)
    # Ensure boolean-like columns exist
    for c in ["open_source", "api_available"]:
        if c in df.columns:
            df[c] = df[c].apply(lambda v: int(v) if (str(v).strip() != "") else 0)
    return df

try:
    DF = load_dataset(CSV_PATH)
except Exception as e:
    # if load fails, use empty DF with expected columns
    print("Failed to load CSV at", CSV_PATH, ":", e)
    DF = pd.DataFrame()

# ---------- Helper analytics & recommender ----------
def summary_stats(df: pd.DataFrame):
    total = len(df)
    by_category = df["category_canonical"].value_counts().to_dict() if "category_canonical" in df.columns else {}
    modalities = df["modality_canonical"].value_counts().to_dict() if "modality_canonical" in df.columns else {}
    open_source_pct = None
    if "open_source" in df.columns and total>0:
        open_source_pct = int(df["open_source"].sum() / total * 100)
    apis_pct = None
    if "api_available" in df.columns and total>0:
        apis_pct = int(df["api_available"].sum() / total * 100)
    latest_year = int(df["release_year"].max()) if "release_year" in df.columns and not df["release_year"].isnull().all() else None
    return {
        "total": total,
        "by_category": by_category,
        "modalities": modalities,
        "open_source_pct": open_source_pct,
        "apis_pct": apis_pct,
        "latest_year": latest_year
    }

def find_white_space(df: pd.DataFrame):
    # crude heuristics to find gaps relevant to Velar
    categories = (df["category_canonical"].value_counts().to_dict() if "category_canonical" in df.columns else {})
    # count tools mentioning "DeFi", "Bitcoin", "Stacks" in company or website? Basic idea: none exist
    text_columns = []
    for col in ["company", "tool_name", "website", "source_domain"]:
        if col in df.columns:
            text_columns.append(col)
    text_blob = " ".join(df[col].astype(str).str.lower().str.cat(sep=" ") for col in text_columns) if text_columns else ""
    has_defi = "defi" in text_blob
    has_bitcoin = "bitcoin" in text_blob or "sbtc" in text_blob or "stacks" in text_blob
    # Find categories with low counts
    low_count_categories = [k for k,v in categories.items() if v <= 2]
    return {
        "has_defi": bool(has_defi),
        "has_bitcoin": bool(has_bitcoin),
        "low_count_categories": low_count_categories,
        "major_gap_recommendation": (
            "Build AI tools for Bitcoin DeFi: AMM modeling, on-chain risk engine, Clarity contract interpreter, governance copilot"
            if not (has_defi or has_bitcoin) else "There is some DeFi/Bitcoin presence; focus on deep integration and risk engines."
        )
    }

def build_recommendations(df: pd.DataFrame):
    # Produce prioritized feature list mapping to Velar phases
    preds = [
        {"phase": "Dharma (0-3m)", "features": [
            "Velar Copilot: swap & LP explainers (deterministic math backed)",
            "Clarity Contract Interpreter (read & explain)",
            "Staking & IDO advisor (basic projections)"
        ]},
        {"phase": "Artha (3-9m)", "features": [
            "Perps Risk Engine (liquidation sims, funding forecasts)",
            "AI Market-Maker assistant (optimal LP ranges)",
            "Governance Copilot (proposal summarizer)"
        ]},
        {"phase": "Kama (9-18m)", "features": [
            "Personalized strategy engine",
            "Autonomous trading agent (with heavy guardrails)",
            "Protocol-level risk monitoring"
        ]},
        {"phase": "Moksha (18m+)", "features": [
            "Autonomous Finance Layer (protocol orchestration)",
            "AI-enforced governance",
            "Developer platform for Clarity + AI"
        ]}
    ]
    return preds

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/summary")
def api_summary():
    stats = summary_stats(DF)
    whitespace = find_white_space(DF)
    return jsonify({
        "stats": stats,
        "whitespace": whitespace
    })

@app.route("/api/tools")
def api_tools():
    # support simple filters via query params
    df = DF.copy()
    q_category = request.args.get("category")
    q_modality = request.args.get("modality")
    q_open = request.args.get("open")  # "1" or "0"
    year_min = request.args.get("year_min", type=int)
    year_max = request.args.get("year_max", type=int)
    if q_category:
        df = df[df["category_canonical"].str.lower() == q_category.lower()]
    if q_modality:
        df = df[df["modality_canonical"].str.lower() == q_modality.lower()]
    if q_open in ("1", "0"):
        df = df[df["open_source"] == int(q_open)]
    if year_min:
        df = df[df["release_year"] >= year_min]
    if year_max:
        df = df[df["release_year"] <= year_max]
    # return first 100 rows to keep payload small
    records = df.head(500).to_dict(orient="records")
    return jsonify({"count": len(df), "rows": records})

@app.route("/api/recommendations")
def api_recommendations():
    recs = build_recommendations(DF)
    return jsonify({"recommendations": recs})

@app.route("/api/download-whitepaper")
def api_download_whitepaper():
    # serves the uploaded Velar Whitepaper
    if os.path.exists(WHITEPAPER_PATH):
        return send_file(WHITEPAPER_PATH, as_attachment=True)
    return jsonify({"error": "whitepaper not found on server path."}), 404

# basic health
@app.route("/api/ping")
def ping():
    return jsonify({"status": "ok", "tools_count": len(DF)})

if __name__ == "__main__":
    # dev server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
