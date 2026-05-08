"""
NBA win predictor and live win-probability predictor.

This module exposes two high-level classes:

* ``WinPredictor``    – pre-game home-win probability given season stats.
* ``LiveWinPredictor``– in-game home-win probability given score and clock.

Both classes lazy-load the trained models from disk on first use.
"""

import os
import logging
import numpy as np
import joblib

from feature_engineering import build_matchup_features, build_live_game_features

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
PREDICTOR_FILENAME = "win_predictor.joblib"
LIVE_MODEL_FILENAME = "live_prob_model.joblib"


class WinPredictor:
    """
    Predict the probability that the home team wins a game given pre-game
    team season statistics.

    Usage
    -----
    >>> predictor = WinPredictor()
    >>> prob = predictor.predict_proba(home_stats, away_stats)
    >>> print(f"Home win probability: {prob:.1%}")
    """

    def __init__(self, model_dir: str = MODEL_DIR):
        self._model_dir = model_dir
        self._model = None

    def _load(self):
        if self._model is None:
            path = os.path.join(self._model_dir, PREDICTOR_FILENAME)
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Win predictor model not found at {path}. "
                    "Run `python train_model.py` first."
                )
            self._model = joblib.load(path)
            logger.info("Loaded win predictor from %s", path)

    def predict_proba(
        self,
        home_stats: dict,
        away_stats: dict,
    ) -> float:
        """
        Return the probability (0–1) that the home team wins.

        Parameters
        ----------
        home_stats : dict
            Season statistics for the home team.  Must contain:
            ``win_pct``, ``avg_pt_diff``, ``home_win_pct``.
        away_stats : dict
            Season statistics for the away team.  Must contain:
            ``win_pct``, ``avg_pt_diff``, ``away_win_pct``.

        Returns
        -------
        float
            Home-win probability in [0, 1].
        """
        self._load()
        features = build_matchup_features(home_stats, away_stats).reshape(1, -1)
        proba = self._model.predict_proba(features)[0]
        # index 1 = probability of class 1 (home win)
        return float(proba[1])

    def predict_winner(
        self,
        home_stats: dict,
        away_stats: dict,
        home_team: str = "Home",
        away_team: str = "Away",
    ) -> dict:
        """
        Return a prediction dict with win probabilities for both teams.

        Returns
        -------
        dict
            ``home_team``, ``away_team``, ``home_win_prob``, ``away_win_prob``,
            ``predicted_winner``.
        """
        home_prob = self.predict_proba(home_stats, away_stats)
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_win_prob": round(home_prob, 4),
            "away_win_prob": round(1 - home_prob, 4),
            "predicted_winner": home_team if home_prob >= 0.5 else away_team,
        }


class LiveWinPredictor:
    """
    In-game win-probability predictor.

    Given the current score differential and game clock, returns the
    probability that the *home* team wins.

    Usage
    -----
    >>> live = LiveWinPredictor()
    >>> prob = live.predict_proba(score_diff=6, period=3, seconds_remaining=300)
    >>> print(f"Home win probability: {prob:.1%}")
    """

    def __init__(self, model_dir: str = MODEL_DIR):
        self._model_dir = model_dir
        self._model = None

    def _load(self):
        if self._model is None:
            path = os.path.join(self._model_dir, LIVE_MODEL_FILENAME)
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Live win-probability model not found at {path}. "
                    "Run `python train_model.py` first."
                )
            self._model = joblib.load(path)
            logger.info("Loaded live win-probability model from %s", path)

    def predict_proba(
        self,
        score_diff: float,
        period: int,
        seconds_remaining: float,
    ) -> float:
        """
        Return the probability (0–1) that the home team wins.

        Parameters
        ----------
        score_diff : float
            home_score − away_score.  Negative means away is leading.
        period : int
            Current game period (1-indexed; >4 = overtime).
        seconds_remaining : float
            Seconds remaining in the *current* period.

        Returns
        -------
        float
            Home-win probability in [0, 1].
        """
        self._load()
        is_home_leading = score_diff > 0
        features = build_live_game_features(
            score_diff, period, seconds_remaining, is_home_leading
        ).reshape(1, -1)
        proba = self._model.predict_proba(features)[0]
        return float(proba[1])

    def get_win_probabilities(
        self,
        score_diff: float,
        period: int,
        seconds_remaining: float,
        home_team: str = "Home",
        away_team: str = "Away",
    ) -> dict:
        """
        Return win probabilities for both teams with game context.

        Returns
        -------
        dict
            ``home_team``, ``away_team``, ``home_win_prob``, ``away_win_prob``,
            ``score_diff``, ``period``, ``seconds_remaining``.
        """
        home_prob = self.predict_proba(score_diff, period, seconds_remaining)
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_win_prob": round(home_prob, 4),
            "away_win_prob": round(1 - home_prob, 4),
            "score_diff": score_diff,
            "period": period,
            "seconds_remaining": seconds_remaining,
        }
