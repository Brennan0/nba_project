import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/game.dart';
import '../models/live_game_data.dart';
import '../models/prediction.dart';

/// Service class that wraps all calls to the Python Flask backend API.
class ApiService {
  /// Base URL of the Flask backend.  Override in tests or when deploying.
  final String baseUrl;
  final http.Client _client;

  ApiService({
    this.baseUrl = 'http://localhost:5000',
    http.Client? client,
  }) : _client = client ?? http.Client();

  // ---------------------------------------------------------------------------
  // Today's games
  // ---------------------------------------------------------------------------

  /// Fetch today's NBA schedule with pre-game win predictions.
  Future<List<Game>> getTodaysGames() async {
    final uri = Uri.parse('$baseUrl/games/today');
    final response = await _client.get(uri);

    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body) as List<dynamic>;
      return data
          .map((e) => Game.fromJson(e as Map<String, dynamic>))
          .toList();
    } else {
      throw ApiException(
        statusCode: response.statusCode,
        message: 'Failed to load today\'s games',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Live game data
  // ---------------------------------------------------------------------------

  /// Fetch live win probabilities for a specific game.
  ///
  /// [gameId] is the NBA API game ID (e.g. '0022300001').
  /// [period] and [secondsRemaining] refine the clock context.
  Future<LiveGameData> getLiveGameData(
    String gameId, {
    int period = 4,
    double secondsRemaining = 0,
  }) async {
    final uri = Uri.parse('$baseUrl/games/$gameId/live').replace(
      queryParameters: {
        'period': period.toString(),
        'seconds_remaining': secondsRemaining.toStringAsFixed(1),
      },
    );
    final response = await _client.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      return LiveGameData.fromJson(gameId, data);
    } else {
      throw ApiException(
        statusCode: response.statusCode,
        message: 'Failed to load live data for game $gameId',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Custom prediction
  // ---------------------------------------------------------------------------

  /// Request a win-probability prediction for a custom matchup.
  ///
  /// [homeStats] and [awayStats] must contain at minimum:
  ///   * `win_pct`       – season win percentage (0.0 – 1.0)
  ///   * `avg_pt_diff`   – average point differential
  ///   * `home_win_pct`  – home / away split win percentage
  ///   * `away_win_pct`
  Future<Prediction> getPrediction({
    required String homeTeam,
    required String awayTeam,
    required Map<String, dynamic> homeStats,
    required Map<String, dynamic> awayStats,
  }) async {
    final uri = Uri.parse('$baseUrl/predict');
    final body = json.encode({
      'home_team': homeTeam,
      'away_team': awayTeam,
      'home_stats': homeStats,
      'away_stats': awayStats,
    });

    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: body,
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      return Prediction.fromJson(data);
    } else {
      throw ApiException(
        statusCode: response.statusCode,
        message: 'Prediction request failed',
      );
    }
  }

  /// Check if the backend is reachable.
  Future<bool> checkHealth() async {
    try {
      final uri = Uri.parse('$baseUrl/health');
      final response = await _client
          .get(uri)
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

/// Exception thrown when the API returns a non-success status code.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException($statusCode): $message';
}
