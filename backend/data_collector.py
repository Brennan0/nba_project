"""
NBA data collection using nba_api.
Fetches historical game data, today's games, and live box scores.
"""

import time
import pandas as pd
from nba_api.stats.endpoints import (
    leaguegamefinder,
    scoreboard,
    boxscoretraditionalv2,
    teamgamelog,
)
from nba_api.stats.static import teams as nba_teams_static


# nba_api requires a small delay between requests to avoid rate limiting
REQUEST_DELAY = 0.6


def get_all_teams() -> list[dict]:
    """Return a list of all NBA teams with id, abbreviation and full name."""
    return nba_teams_static.get_teams()


def get_team_id(abbreviation: str) -> int | None:
    """Look up a team ID by its three-letter abbreviation (e.g. 'LAL')."""
    for team in get_all_teams():
        if team["abbreviation"].upper() == abbreviation.upper():
            return team["id"]
    return None


def get_season_games(season: str = "2023-24") -> pd.DataFrame:
    """
    Fetch all regular-season games for the given season using
    LeagueGameFinder.

    Parameters
    ----------
    season : str
        NBA season string, e.g. '2023-24'.

    Returns
    -------
    pd.DataFrame
        One row per team-game (two rows per actual game).
    """
    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Regular Season",
        league_id_nullable="00",
    )
    time.sleep(REQUEST_DELAY)
    df = finder.get_data_frames()[0]
    return df


def get_team_game_log(team_id: int, season: str = "2023-24") -> pd.DataFrame:
    """
    Fetch the full game log for a single team in a given season.

    Parameters
    ----------
    team_id : int
        NBA team ID.
    season : str
        NBA season string.

    Returns
    -------
    pd.DataFrame
        One row per game, sorted most-recent first.
    """
    log = teamgamelog.TeamGameLog(
        team_id=team_id,
        season=season,
        season_type_all_star="Regular Season",
    )
    time.sleep(REQUEST_DELAY)
    return log.get_data_frames()[0]


def get_todays_games() -> list[dict]:
    """
    Fetch today's NBA game schedule from the live Scoreboard endpoint.

    Returns
    -------
    list[dict]
        Each dict contains: game_id, home_team_id, home_team_abbr,
        away_team_id, away_team_abbr, status, home_score, away_score,
        period, clock.
    """
    board = scoreboard.ScoreBoard()
    time.sleep(REQUEST_DELAY)
    games_raw = board.get_dict().get("scoreboard", {}).get("games", [])

    games = []
    for g in games_raw:
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        games.append(
            {
                "game_id": g.get("gameId"),
                "home_team_id": home.get("teamId"),
                "home_team_abbr": home.get("teamTricode"),
                "home_team_name": home.get("teamName"),
                "away_team_id": away.get("teamId"),
                "away_team_abbr": away.get("teamTricode"),
                "away_team_name": away.get("teamName"),
                "status": g.get("gameStatusText"),
                "home_score": home.get("score", 0),
                "away_score": away.get("score", 0),
                "period": g.get("period", 0),
                "clock": g.get("gameClock", ""),
            }
        )
    return games


def get_live_box_score(game_id: str) -> dict:
    """
    Fetch a live (or completed) box score for a specific game.

    Parameters
    ----------
    game_id : str
        NBA game ID string, e.g. '0022300001'.

    Returns
    -------
    dict
        Contains 'home' and 'away' keys with team stats, and game metadata.
    """
    box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
    time.sleep(REQUEST_DELAY)
    team_stats = box.get_data_frames()[1]  # team summary data frame

    result: dict = {"game_id": game_id, "teams": []}
    for _, row in team_stats.iterrows():
        result["teams"].append(
            {
                "team_id": row.get("TEAM_ID"),
                "team_abbreviation": row.get("TEAM_ABBREVIATION"),
                "pts": row.get("PTS"),
                "reb": row.get("REB"),
                "ast": row.get("AST"),
                "fg_pct": row.get("FG_PCT"),
                "fg3_pct": row.get("FG3_PCT"),
                "ft_pct": row.get("FT_PCT"),
                "tov": row.get("TO"),
            }
        )
    return result
