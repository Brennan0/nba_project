"""
Flask REST API for the NBA Win Predictor.

Endpoints
---------
GET  /health
    Health check.

GET  /teams
    List all NBA teams.

GET  /games/today
    Today's schedule with pre-game win predictions.

GET  /games/<game_id>/live
    Live win probability for an in-progress game.

POST /predict
    Predict win probability for a custom matchup.
    Body (JSON):
        {
          "home_team": "LAL",
          "away_team": "BOS",
          "home_stats": { "win_pct": 0.60, "avg_pt_diff": 4.2,
                          "home_win_pct": 0.65, "away_win_pct": 0.55 },
          "away_stats": { "win_pct": 0.70, "avg_pt_diff": 6.1,
                          "home_win_pct": 0.75, "away_win_pct": 0.65 }
        }
"""

import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from data_collector import get_all_teams, get_todays_games, get_live_box_score
from predictor import WinPredictor, LiveWinPredictor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

_win_predictor = WinPredictor()
_live_predictor = LiveWinPredictor()


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/teams")
def teams():
    """Return a list of all NBA teams."""
    return jsonify(get_all_teams())


@app.get("/games/today")
def games_today():
    """
    Return today's games.  For each game we include a pre-game win prediction
    if season stats are available in the request's ``stats`` query param, or
    fall back to a 50/50 placeholder.
    """
    try:
        games = get_todays_games()
    except Exception as exc:
        logger.error("Failed to fetch today's games: %s", exc)
        return jsonify({"error": "Unable to retrieve today's games"}), 502

    # Try to attach a default 50/50 prediction for each game so the app
    # always has something to display.
    for game in games:
        game.setdefault("home_win_prob", 0.50)
        game.setdefault("away_win_prob", 0.50)
        game.setdefault("predicted_winner", None)

    return jsonify(games)


@app.get("/games/<game_id>/live")
def game_live(game_id: str):
    """
    Return live win probabilities for a game.

    Fetches the current box score, extracts the score and clock information,
    then runs the live model.
    """
    try:
        box = get_live_box_score(game_id)
    except Exception as exc:
        logger.error("Failed to fetch box score for %s: %s", game_id, exc)
        return jsonify({"error": "Unable to retrieve live box score"}), 502

    teams = box.get("teams", [])
    if len(teams) < 2:
        return jsonify({"error": "Incomplete box score data"}), 422

    # nba_api returns home team first in BoxScoreTraditionalV2 team stats
    home = teams[0]
    away = teams[1]
    home_pts = home.get("pts") or 0
    away_pts = away.get("pts") or 0
    score_diff = float(home_pts) - float(away_pts)

    # period / clock come from the game object, not the box; default to Q4/0
    period = int(request.args.get("period", 4))
    seconds_remaining = float(request.args.get("seconds_remaining", 0))

    try:
        result = _live_predictor.get_win_probabilities(
            score_diff=score_diff,
            period=period,
            seconds_remaining=seconds_remaining,
            home_team=home.get("team_abbreviation", "HOME"),
            away_team=away.get("team_abbreviation", "AWAY"),
        )
    except FileNotFoundError as exc:
        logger.error("Live model not found: %s", exc)
        return jsonify({"error": "Live win-probability model is unavailable"}), 503
    result["home_pts"] = home_pts
    result["away_pts"] = away_pts
    return jsonify(result)


@app.post("/predict")
def predict():
    """
    Predict win probability for a custom matchup given pre-game stats.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    home_team = body.get("home_team", "Home")
    away_team = body.get("away_team", "Away")
    home_stats = body.get("home_stats")
    away_stats = body.get("away_stats")

    if not home_stats or not away_stats:
        return jsonify({"error": "home_stats and away_stats are required"}), 400

    required_keys = {"win_pct", "avg_pt_diff"}
    for label, stats in [("home_stats", home_stats), ("away_stats", away_stats)]:
        missing = required_keys - set(stats.keys())
        if missing:
            return jsonify({"error": f"{label} missing keys: {missing}"}), 400

    try:
        prediction = _win_predictor.predict_winner(
            home_stats=home_stats,
            away_stats=away_stats,
            home_team=home_team,
            away_team=away_team,
        )
    except FileNotFoundError as exc:
        logger.error("Win predictor model not found: %s", exc)
        return jsonify({"error": "Win predictor model is unavailable"}), 503

    return jsonify(prediction)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting NBA Win Predictor API on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
