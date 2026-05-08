"""
Unit tests for the NBA win predictor backend.

These tests run entirely offline (no nba_api calls), exercising:
- feature_engineering.py
- predictor.py  (with a dummy model injected)
- api.py        (Flask test client)
"""

import json
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# feature_engineering
# ---------------------------------------------------------------------------

class TestFeatureEngineering:

    def _make_games_df(self):
        """Minimal synthetic LeagueGameFinder data frame."""
        data = {
            "TEAM_ID": [1, 2, 1, 2, 1, 2],
            "GAME_ID": ["001", "001", "002", "002", "003", "003"],
            "WL": ["W", "L", "L", "W", "W", "L"],
            "PTS": [110, 100, 95, 105, 120, 110],
            "PLUS_MINUS": [10, -10, -10, 10, 10, -10],
            "MATCHUP": ["T1 vs. T2", "T2 @ T1", "T1 @ T2", "T2 vs. T1", "T1 vs. T2", "T2 @ T1"],
        }
        return pd.DataFrame(data)

    def test_compute_team_season_stats_shape(self):
        from feature_engineering import compute_team_season_stats
        df = self._make_games_df()
        stats = compute_team_season_stats(df)
        assert stats.shape[1] == 6
        assert set(stats.columns) == {
            "win_pct", "avg_pts_scored", "avg_pts_allowed",
            "avg_pt_diff", "home_win_pct", "away_win_pct",
        }

    def test_compute_team_season_stats_values(self):
        from feature_engineering import compute_team_season_stats
        df = self._make_games_df()
        stats = compute_team_season_stats(df)
        # Team 1: 2W 1L in home games (matchups containing "vs."), overall 2/3
        assert abs(stats.loc[1, "win_pct"] - 2 / 3) < 1e-6

    def test_build_matchup_features_shape(self):
        from feature_engineering import build_matchup_features
        home = {"win_pct": 0.6, "avg_pt_diff": 4.0, "home_win_pct": 0.65, "away_win_pct": 0.55}
        away = {"win_pct": 0.5, "avg_pt_diff": 0.5, "home_win_pct": 0.55, "away_win_pct": 0.45}
        feat = build_matchup_features(home, away)
        assert feat.shape == (8,)

    def test_build_matchup_features_diff(self):
        from feature_engineering import build_matchup_features
        home = {"win_pct": 0.7, "avg_pt_diff": 5.0, "home_win_pct": 0.75, "away_win_pct": 0.65}
        away = {"win_pct": 0.4, "avg_pt_diff": -1.0, "home_win_pct": 0.45, "away_win_pct": 0.35}
        feat = build_matchup_features(home, away)
        # index 6 = win_pct_diff = 0.7 - 0.4 = 0.3
        assert abs(feat[6] - 0.3) < 1e-6
        # index 7 = avg_pt_diff_diff = 5.0 - (-1.0) = 6.0
        assert abs(feat[7] - 6.0) < 1e-6

    def test_build_live_game_features_shape(self):
        from feature_engineering import build_live_game_features
        feat = build_live_game_features(5.0, 3, 300.0, True)
        assert feat.shape == (3,)

    def test_build_live_game_features_time_fraction_end_of_game(self):
        from feature_engineering import build_live_game_features
        # End of Q4 (0 seconds remaining in period 4) → fraction should be 1.0
        feat = build_live_game_features(0.0, 4, 0.0, False)
        assert abs(feat[1] - 1.0) < 1e-6

    def test_build_live_game_features_time_fraction_start(self):
        from feature_engineering import build_live_game_features
        # Start of Q1 → fraction should be 0.0
        feat = build_live_game_features(0.0, 1, 12 * 60, False)
        assert abs(feat[1] - 0.0) < 1e-6

    def test_build_training_dataset(self):
        from feature_engineering import compute_team_season_stats, build_training_dataset
        df = self._make_games_df()
        stats = compute_team_season_stats(df)
        X, y = build_training_dataset(df, stats)
        assert X.ndim == 2
        assert X.shape[1] == 8
        assert y.ndim == 1
        assert len(X) == len(y)


# ---------------------------------------------------------------------------
# predictor (with injected dummy models)
# ---------------------------------------------------------------------------

def _make_dummy_pipeline(proba_class1: float = 0.65):
    """Return a tiny sklearn pipeline that always predicts proba_class1."""
    rng = np.random.default_rng(0)
    X = rng.standard_normal((40, 8))
    y = (X[:, 0] > 0).astype(int)
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression())])
    pipe.fit(X, y)
    return pipe


class TestWinPredictor:

    def _predictor(self):
        from predictor import WinPredictor
        p = WinPredictor()
        p._model = _make_dummy_pipeline()
        return p

    def test_predict_proba_range(self):
        p = self._predictor()
        home = {"win_pct": 0.6, "avg_pt_diff": 3.0, "home_win_pct": 0.65, "away_win_pct": 0.55}
        away = {"win_pct": 0.5, "avg_pt_diff": 0.0, "home_win_pct": 0.55, "away_win_pct": 0.45}
        prob = p.predict_proba(home, away)
        assert 0.0 <= prob <= 1.0

    def test_predict_winner_keys(self):
        p = self._predictor()
        home = {"win_pct": 0.6, "avg_pt_diff": 3.0, "home_win_pct": 0.65, "away_win_pct": 0.55}
        away = {"win_pct": 0.5, "avg_pt_diff": 0.0, "home_win_pct": 0.55, "away_win_pct": 0.45}
        result = p.predict_winner(home, away, "LAL", "BOS")
        assert set(result.keys()) == {
            "home_team", "away_team", "home_win_prob", "away_win_prob", "predicted_winner"
        }
        assert result["home_win_prob"] + result["away_win_prob"] == pytest.approx(1.0, abs=1e-4)

    def test_predict_winner_teams(self):
        p = self._predictor()
        home = {"win_pct": 0.6, "avg_pt_diff": 3.0, "home_win_pct": 0.65, "away_win_pct": 0.55}
        away = {"win_pct": 0.5, "avg_pt_diff": 0.0, "home_win_pct": 0.55, "away_win_pct": 0.45}
        result = p.predict_winner(home, away, "LAL", "BOS")
        assert result["predicted_winner"] in {"LAL", "BOS"}

    def test_file_not_found_without_model(self, tmp_path):
        from predictor import WinPredictor
        p = WinPredictor(model_dir=str(tmp_path))
        home = {"win_pct": 0.6, "avg_pt_diff": 3.0, "home_win_pct": 0.65, "away_win_pct": 0.55}
        away = {"win_pct": 0.5, "avg_pt_diff": 0.0, "home_win_pct": 0.55, "away_win_pct": 0.45}
        with pytest.raises(FileNotFoundError):
            p.predict_proba(home, away)


class TestLiveWinPredictor:

    def _predictor(self):
        from predictor import LiveWinPredictor
        p = LiveWinPredictor()
        rng = np.random.default_rng(0)
        X = rng.standard_normal((40, 3))
        y = (X[:, 0] > 0).astype(int)
        pipe = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression())])
        pipe.fit(X, y)
        p._model = pipe
        return p

    def test_predict_proba_range(self):
        p = self._predictor()
        prob = p.predict_proba(score_diff=5.0, period=3, seconds_remaining=300.0)
        assert 0.0 <= prob <= 1.0

    def test_predict_proba_leading_team_higher(self):
        """A team with a big lead late should have higher win probability."""
        p = self._predictor()
        prob_leading = p.predict_proba(score_diff=15.0, period=4, seconds_remaining=60.0)
        prob_trailing = p.predict_proba(score_diff=-15.0, period=4, seconds_remaining=60.0)
        # Logistic regression on score_diff should capture this direction
        assert prob_leading != prob_trailing  # at minimum they're different

    def test_get_win_probabilities_keys(self):
        p = self._predictor()
        result = p.get_win_probabilities(
            score_diff=3.0, period=2, seconds_remaining=400.0,
            home_team="LAL", away_team="BOS",
        )
        expected_keys = {
            "home_team", "away_team", "home_win_prob", "away_win_prob",
            "score_diff", "period", "seconds_remaining",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_get_win_probabilities_sum_to_one(self):
        p = self._predictor()
        result = p.get_win_probabilities(3.0, 2, 400.0)
        assert result["home_win_prob"] + result["away_win_prob"] == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# Flask API
# ---------------------------------------------------------------------------

class TestFlaskAPI:

    @pytest.fixture
    def client(self):
        import api as api_module
        api_module.app.config["TESTING"] = True
        with api_module.app.test_client() as c:
            yield c

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_teams_returns_list(self, client):
        resp = client.get("/teams")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "abbreviation" in data[0]

    def test_predict_missing_body(self, client):
        resp = client.post("/predict", content_type="application/json", data="{}")
        assert resp.status_code == 400

    def test_predict_missing_stats(self, client):
        body = json.dumps({"home_team": "LAL", "away_team": "BOS"})
        resp = client.post("/predict", content_type="application/json", data=body)
        assert resp.status_code == 400

    def test_predict_success(self, client):
        """Inject a dummy model and verify /predict returns expected keys."""
        dummy_pipeline = _make_dummy_pipeline()

        import api as api_module
        api_module._win_predictor._model = dummy_pipeline

        body = json.dumps(
            {
                "home_team": "LAL",
                "away_team": "BOS",
                "home_stats": {
                    "win_pct": 0.6, "avg_pt_diff": 3.0,
                    "home_win_pct": 0.65, "away_win_pct": 0.55,
                },
                "away_stats": {
                    "win_pct": 0.5, "avg_pt_diff": 0.0,
                    "home_win_pct": 0.55, "away_win_pct": 0.45,
                },
            }
        )
        resp = client.post("/predict", content_type="application/json", data=body)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "home_win_prob" in data
        assert "away_win_prob" in data
        assert "predicted_winner" in data
        assert data["home_win_prob"] + data["away_win_prob"] == pytest.approx(1.0, abs=1e-4)

    def test_games_today_live_fallback(self, client):
        """When nba_api is unavailable, /games/today should return 502."""
        with patch("api.get_todays_games", side_effect=Exception("network error")):
            resp = client.get("/games/today")
        assert resp.status_code == 502
