# NBA Win Predictor

A full-stack NBA win predictor and live win-probability app built with Python (scikit-learn + Flask) and Flutter.

---

## Project Structure

```
nba_project/
├── backend/                  Python ML backend
│   ├── requirements.txt      Python dependencies
│   ├── data_collector.py     NBA data collection via nba_api
│   ├── feature_engineering.py  Feature extraction & transformation
│   ├── train_model.py        Model training CLI
│   ├── predictor.py          WinPredictor & LiveWinPredictor classes
│   ├── api.py                Flask REST API
│   └── models/               Saved joblib model files (generated)
├── flutter_app/              Flutter mobile/web app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── models/           Game, LiveGameData, Prediction
│   │   ├── screens/          HomeScreen, GameDetailScreen
│   │   ├── services/         ApiService (HTTP client)
│   │   └── widgets/          GameCard, WinProbabilityChart
│   └── test/                 Flutter unit tests
└── tests/
    └── test_backend.py       Python backend unit tests (22 tests)
```

---

## Features

| Feature | Details |
|---|---|
| **Pre-game win prediction** | Uses season win%, point differential, and home/away splits |
| **Live win probability** | Updates every 30 s during live games based on score diff & clock |
| **Today's schedule** | Fetches real-time games from the NBA API scoreboard |
| **Team stats** | Aggregates per-team season statistics from LeagueGameFinder |
| **Flutter UI** | Material 3 app with pie-chart win-probability gauge and line chart history |

---

## Backend

### Setup

```bash
cd backend
pip install -r requirements.txt
```

> Use a supported Python 3.x version (3.9+). The requirements include version pins that vary at Python 3.13 for NumPy/scikit-learn compatibility.

### Train models

```bash
# Train on live NBA season data (requires internet)
python train_model.py --season 2023-24

# Train on synthetic data only (offline / CI)
python train_model.py --skip-season-data
```

### Run the API

```bash
python api.py
# Server starts at http://localhost:5000
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/teams` | List all NBA teams |
| GET | `/games/today` | Today's schedule with win predictions |
| GET | `/games/<game_id>/live` | Live win probability for a game |
| POST | `/predict` | Predict win prob for a custom matchup |

#### Example – custom prediction

```bash
curl -X POST http://localhost:5000/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "home_team": "LAL",
    "away_team": "BOS",
    "home_stats": {"win_pct": 0.60, "avg_pt_diff": 4.2,
                   "home_win_pct": 0.65, "away_win_pct": 0.55},
    "away_stats": {"win_pct": 0.70, "avg_pt_diff": 6.1,
                   "home_win_pct": 0.75, "away_win_pct": 0.65}
  }'
```

Response:
```json
{
  "home_team": "LAL",
  "away_team": "BOS",
  "home_win_prob": 0.4312,
  "away_win_prob": 0.5688,
  "predicted_winner": "BOS"
}
```

### Run tests

```bash
python -m pytest tests/ -v
```

---

## Flutter App

### Requirements

- Flutter SDK ≥ 3.3
- Dart SDK ≥ 3.3

### Setup

```bash
cd flutter_app
flutter pub get
```

### Configure backend URL

By default the app connects to `http://localhost:5000`.  
Change the `baseUrl` in `lib/services/api_service.dart` for production.

### Run

```bash
flutter run
```

### Test

```bash
flutter test
```

---

## Machine Learning

### Pre-game Win Predictor

Uses a **HistGradientBoostingClassifier** (fallback: Logistic Regression) with 8 features:

| Feature | Description |
|---|---|
| `home_win_pct` | Home team season win % |
| `away_win_pct` | Away team season win % |
| `home_avg_pt_diff` | Home team average point differential |
| `away_avg_pt_diff` | Away team average point differential |
| `home_home_win_pct` | Home team's win % in home games |
| `away_away_win_pct` | Away team's win % in away games |
| `win_pct_diff` | Difference in season win % |
| `avg_pt_diff_diff` | Difference in average point differential |

### Live Win Probability Model

Uses a **calibrated Logistic Regression** trained on a probabilistic simulation of game states (20 000 synthetic samples):

| Feature | Description |
|---|---|
| `score_diff` | home_score − away_score |
| `time_elapsed_fraction` | Fraction of regulation time elapsed (0→1) |
| `period` | Current period (1–4, >4 = OT) |

Live model validation: **74.7% accuracy**, log-loss 0.49.
