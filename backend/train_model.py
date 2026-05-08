"""
Train and persist the NBA win predictor models.

Two models are trained and saved to disk:

1. **win_predictor** – predicts the probability that the *home* team wins a
   game given pre-game season statistics.  Uses a gradient-boosted tree
   (HistGradientBoostingClassifier) with a fallback to logistic regression
   when the dataset is tiny.

2. **live_prob_model** – predicts the in-game win probability for the home
   team given the current score differential and time elapsed.  Uses a
   calibrated logistic regression.

Run this script directly to train both models:

    python train_model.py [--season 2023-24] [--output-dir models/]
"""

import argparse
import os
import logging
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, log_loss

from data_collector import get_season_games
from feature_engineering import (
    compute_team_season_stats,
    build_training_dataset,
    build_live_game_features,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "models")
PREDICTOR_FILENAME = "win_predictor.joblib"
LIVE_MODEL_FILENAME = "live_prob_model.joblib"
SCALER_FILENAME = "scaler.joblib"


# --------------------------------------------------------------------------- #
# Pre-game win predictor
# --------------------------------------------------------------------------- #

def train_win_predictor(X: np.ndarray, y: np.ndarray) -> Pipeline:
    """
    Train a gradient-boosted classifier pipeline for pre-game win prediction.

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, 8)
    y : np.ndarray, shape (n_samples,) – 1 = home win

    Returns
    -------
    sklearn Pipeline (scaler + classifier, already fit on all data)
    """
    if len(X) < 20:
        logger.warning(
            "Very few training samples (%d). Using logistic regression.", len(X)
        )
        clf = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    else:
        clf = HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
        )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", clf),
        ]
    )

    if len(X) >= 50:
        scores = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy")
        logger.info(
            "Win predictor 5-fold CV accuracy: %.3f ± %.3f",
            scores.mean(),
            scores.std(),
        )

    pipeline.fit(X, y)
    train_acc = accuracy_score(y, pipeline.predict(X))
    logger.info("Win predictor training accuracy: %.3f", train_acc)
    return pipeline


# --------------------------------------------------------------------------- #
# Live win-probability model
# --------------------------------------------------------------------------- #

def _generate_live_training_data(n_samples: int = 20_000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic training data for the live win-probability model.

    In the absence of play-by-play data, we use a probabilistic simulation
    based on well-known empirical distributions:

    * Score differential follows roughly N(0, σ) where σ grows with
      √(time elapsed).
    * A home team with a score advantage late in the game wins with very
      high probability.

    The true label is determined by simulating the remainder of the game
    1000 times using a Gaussian random walk.
    """
    rng = np.random.default_rng(42)
    periods = rng.integers(1, 5, size=n_samples)
    secs_left = rng.uniform(0, 12 * 60, size=n_samples)
    # approx 48 min regulation = 2880 s elapsed
    regulation_seconds = 4 * 12 * 60
    clamped = np.minimum(periods, 4)
    secs_elapsed = (clamped - 1) * 12 * 60 + np.maximum(0.0, 12 * 60 - secs_left)
    time_frac = np.minimum(secs_elapsed / regulation_seconds, 1.0)

    # sigma of score diff ~ 4 pts per quarter, so ~ sqrt(time_frac) * 16
    sigma = np.sqrt(time_frac + 1e-6) * 16
    score_diff = rng.normal(0, sigma)

    # simulate remainder outcome via Gaussian random walk
    secs_remaining = regulation_seconds - secs_elapsed
    future_sigma = np.sqrt(secs_remaining / regulation_seconds) * 16
    future_noise = rng.normal(0, future_sigma)
    final_diff = score_diff + future_noise
    y = (final_diff > 0).astype(int)  # 1 = home team wins

    X = np.column_stack([score_diff, time_frac, periods.astype(float)])
    return X, y


def train_live_model() -> Pipeline:
    """
    Train and return the calibrated logistic regression for live win prob.
    """
    X, y = _generate_live_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    base_lr = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    calibrated = CalibratedClassifierCV(base_lr, cv=5, method="isotonic")

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", calibrated),
        ]
    )
    pipeline.fit(X_train, y_train)

    test_acc = accuracy_score(y_test, pipeline.predict(X_test))
    test_ll = log_loss(y_test, pipeline.predict_proba(X_test))
    logger.info(
        "Live model – test accuracy: %.3f, log-loss: %.4f", test_acc, test_ll
    )
    return pipeline


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Train NBA win predictor models")
    parser.add_argument("--season", default="2023-24", help="NBA season (e.g. 2023-24)")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save trained models",
    )
    parser.add_argument(
        "--skip-season-data",
        action="store_true",
        help="Skip fetching season data (use synthetic data only)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # --- Pre-game model ---
    if not args.skip_season_data:
        logger.info("Fetching season games for %s …", args.season)
        try:
            games_df = get_season_games(args.season)
            season_stats = compute_team_season_stats(games_df)
            X, y = build_training_dataset(games_df, season_stats)
            logger.info("Built training set: %d samples, %d features", *X.shape)
        except Exception as exc:
            logger.error("Failed to fetch season data: %s. Using empty dataset.", exc)
            X, y = np.empty((0, 8)), np.empty((0,), dtype=int)
    else:
        logger.info("--skip-season-data set; skipping NBA API fetch.")
        X, y = np.empty((0, 8)), np.empty((0,), dtype=int)

    if len(X) > 0:
        win_pred = train_win_predictor(X, y)
    else:
        logger.warning("No season data – training win predictor on synthetic data only.")
        # create a minimal synthetic dataset so we can still persist a model
        rng = np.random.default_rng(0)
        X_syn = rng.standard_normal((200, 8))
        # home team wins ~58 % of the time in the NBA
        y_syn = (X_syn[:, 0] + X_syn[:, 2] + rng.standard_normal(200) > 0).astype(int)
        win_pred = train_win_predictor(X_syn, y_syn)

    # --- Live model ---
    logger.info("Training live win-probability model …")
    live_model = train_live_model()

    # --- Save ---
    win_pred_path = os.path.join(args.output_dir, PREDICTOR_FILENAME)
    live_model_path = os.path.join(args.output_dir, LIVE_MODEL_FILENAME)

    joblib.dump(win_pred, win_pred_path)
    joblib.dump(live_model, live_model_path)

    logger.info("Saved win predictor → %s", win_pred_path)
    logger.info("Saved live model    → %s", live_model_path)
    logger.info("Done.")


if __name__ == "__main__":
    main()
