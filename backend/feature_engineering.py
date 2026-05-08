"""
Feature engineering for the NBA win predictor.

Transforms raw game-log data fetched by data_collector.py into a tidy
feature matrix that can be consumed by the ML model.
"""

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _win_flag(wl: str) -> int:
    """Convert a 'W'/'L' string to 1/0."""
    return 1 if str(wl).upper() == "W" else 0


def compute_team_season_stats(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-team season statistics from a LeagueGameFinder data frame.

    The raw data frame has one row per *team-game* (i.e. two rows per actual
    game).  We aggregate to one row per team with the following features:

    * ``win_pct``        – overall win percentage
    * ``avg_pts_scored`` – average points scored per game
    * ``avg_pts_allowed``– average points allowed per game
    * ``avg_pt_diff``    – average point differential (scored − allowed)
    * ``home_win_pct``   – win % in home games
    * ``away_win_pct``   – win % in away games

    Parameters
    ----------
    games_df : pd.DataFrame
        Raw data from :func:`data_collector.get_season_games`.

    Returns
    -------
    pd.DataFrame
        Index = TEAM_ID, columns as listed above.
    """
    df = games_df.copy()

    # normalise column names coming from the API
    df.columns = [c.upper() for c in df.columns]

    required = {"TEAM_ID", "WL", "PTS", "PLUS_MINUS", "MATCHUP"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in games_df: {missing}")

    df["WIN"] = df["WL"].apply(_win_flag)
    df["IS_HOME"] = df["MATCHUP"].str.contains(r"vs\.", na=False).astype(int)
    df["PTS_ALLOWED"] = df["PTS"] - df["PLUS_MINUS"]

    grouped = df.groupby("TEAM_ID")

    stats = pd.DataFrame(
        {
            "win_pct": grouped["WIN"].mean(),
            "avg_pts_scored": grouped["PTS"].mean(),
            "avg_pts_allowed": grouped["PTS_ALLOWED"].mean(),
            "avg_pt_diff": grouped["PLUS_MINUS"].mean(),
        }
    )

    # home / away splits
    home_df = df[df["IS_HOME"] == 1]
    away_df = df[df["IS_HOME"] == 0]

    stats["home_win_pct"] = home_df.groupby("TEAM_ID")["WIN"].mean()
    stats["away_win_pct"] = away_df.groupby("TEAM_ID")["WIN"].mean()

    # fill teams that have no home / away games yet (edge case)
    stats.fillna(stats["win_pct"], inplace=True)

    return stats


def compute_recent_form(game_log_df: pd.DataFrame, n: int = 10) -> dict:
    """
    Compute a team's recent form from a TeamGameLog data frame.

    Parameters
    ----------
    game_log_df : pd.DataFrame
        From :func:`data_collector.get_team_game_log`. Most-recent game first.
    n : int
        Number of most-recent games to consider.

    Returns
    -------
    dict
        ``recent_win_pct`` and ``recent_avg_pt_diff``.
    """
    df = game_log_df.head(n).copy()
    df.columns = [c.upper() for c in df.columns]
    df["WIN"] = df["WL"].apply(_win_flag)

    return {
        "recent_win_pct": df["WIN"].mean(),
        "recent_avg_pt_diff": df["PLUS_MINUS"].mean() if "PLUS_MINUS" in df.columns else 0.0,
    }


def build_matchup_features(
    home_stats: dict | pd.Series,
    away_stats: dict | pd.Series,
) -> np.ndarray:
    """
    Combine home-team and away-team statistics into a single feature vector.

    Features (in order):
    0  home_win_pct
    1  away_win_pct
    2  home_avg_pt_diff
    3  away_avg_pt_diff
    4  home_home_win_pct
    5  away_away_win_pct
    6  win_pct_diff          (home − away)
    7  avg_pt_diff_diff      (home − away)

    Parameters
    ----------
    home_stats, away_stats : dict or pd.Series
        Must contain: win_pct, avg_pt_diff, home_win_pct / away_win_pct.

    Returns
    -------
    np.ndarray, shape (8,)
    """
    def _get(d, key, default=0.5):
        if isinstance(d, pd.Series):
            return float(d.get(key, default))
        return float(d.get(key, default))

    h_wp   = _get(home_stats, "win_pct")
    a_wp   = _get(away_stats, "win_pct")
    h_diff = _get(home_stats, "avg_pt_diff")
    a_diff = _get(away_stats, "avg_pt_diff")
    h_hwp  = _get(home_stats, "home_win_pct")
    a_awp  = _get(away_stats, "away_win_pct")

    return np.array(
        [
            h_wp,
            a_wp,
            h_diff,
            a_diff,
            h_hwp,
            a_awp,
            h_wp - a_wp,
            h_diff - a_diff,
        ],
        dtype=float,
    )


def build_training_dataset(
    games_df: pd.DataFrame,
    season_stats: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the (X, y) training dataset from a season's games and per-team
    season stats.

    Each *actual* game (two rows in ``games_df``) becomes one training sample.
    The label ``y=1`` means the home team won.

    Parameters
    ----------
    games_df : pd.DataFrame
        Raw LeagueGameFinder data for the season.
    season_stats : pd.DataFrame
        Output of :func:`compute_team_season_stats`.

    Returns
    -------
    X : np.ndarray, shape (n_games, 8)
    y : np.ndarray, shape (n_games,)
    """
    df = games_df.copy()
    df.columns = [c.upper() for c in df.columns]
    df["WIN"] = df["WL"].apply(_win_flag)
    df["IS_HOME"] = df["MATCHUP"].str.contains(r"vs\.", na=False).astype(int)

    # Keep only home-team rows (one row per unique game)
    home_rows = df[df["IS_HOME"] == 1].copy()

    X_list, y_list = [], []
    for _, row in home_rows.iterrows():
        home_id = row["TEAM_ID"]
        game_id = row["GAME_ID"]

        # find away team row for the same game
        away_rows = df[(df["GAME_ID"] == game_id) & (df["IS_HOME"] == 0)]
        if away_rows.empty:
            continue
        away_id = away_rows.iloc[0]["TEAM_ID"]

        if home_id not in season_stats.index or away_id not in season_stats.index:
            continue

        features = build_matchup_features(
            season_stats.loc[home_id],
            season_stats.loc[away_id],
        )
        X_list.append(features)
        y_list.append(row["WIN"])

    return np.array(X_list), np.array(y_list)


def build_live_game_features(
    score_diff: float,
    period: int,
    seconds_remaining_in_period: float,
    is_home_leading: bool,
) -> np.ndarray:
    """
    Build a feature vector for the live win-probability model.

    The live model works on *score differential* plus game-clock info.

    Features:
    0  score_diff              – home_score − away_score
    1  time_elapsed_fraction   – fraction of regulation time elapsed (0→1)
    2  period                  – current quarter / period (1–4, or OT)

    Parameters
    ----------
    score_diff : float
        home_score − away_score (negative means away team is leading).
    period : int
        Current period (1-indexed; values > 4 indicate overtime).
    seconds_remaining_in_period : float
        Seconds left in the current period.
    is_home_leading : bool
        Convenience flag (derived from score_diff, included for clarity).

    Returns
    -------
    np.ndarray, shape (3,)
    """
    regulation_seconds = 4 * 12 * 60  # 2 880 s

    # Clamp period to at most 4 for time-elapsed calculation
    clamped_period = min(period, 4)
    seconds_elapsed = (
        (clamped_period - 1) * 12 * 60
        + max(0.0, 12 * 60 - seconds_remaining_in_period)
    )
    time_elapsed_frac = min(seconds_elapsed / regulation_seconds, 1.0)

    return np.array([score_diff, time_elapsed_frac, float(period)], dtype=float)
