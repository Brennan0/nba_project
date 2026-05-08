import 'package:flutter_test/flutter_test.dart';
import 'package:nba_win_predictor/models/game.dart';
import 'package:nba_win_predictor/models/live_game_data.dart';
import 'package:nba_win_predictor/models/prediction.dart';

void main() {
  // ---------------------------------------------------------------------------
  // Game model
  // ---------------------------------------------------------------------------
  group('Game model', () {
    final Map<String, dynamic> sampleJson = {
      'game_id': '0022300001',
      'home_team_abbr': 'LAL',
      'home_team_name': 'Lakers',
      'away_team_abbr': 'BOS',
      'away_team_name': 'Celtics',
      'status': '7:30 pm ET',
      'home_score': 0,
      'away_score': 0,
      'period': 0,
      'clock': '',
      'home_win_prob': 0.55,
      'away_win_prob': 0.45,
      'predicted_winner': 'LAL',
    };

    test('fromJson parses all fields', () {
      final game = Game.fromJson(sampleJson);
      expect(game.gameId, '0022300001');
      expect(game.homeTeamAbbr, 'LAL');
      expect(game.awayTeamAbbr, 'BOS');
      expect(game.homeWinProb, closeTo(0.55, 1e-6));
      expect(game.awayWinProb, closeTo(0.45, 1e-6));
      expect(game.predictedWinner, 'LAL');
    });

    test('isLive returns false for pre-game status', () {
      final game = Game.fromJson(sampleJson);
      expect(game.isLive, isFalse);
    });

    test('isLive returns true for Q2 status', () {
      final game = Game.fromJson({...sampleJson, 'status': 'Q2 10:00', 'period': 2});
      expect(game.isLive, isTrue);
    });

    test('isFinal returns true for Final status', () {
      final game = Game.fromJson({...sampleJson, 'status': 'Final'});
      expect(game.isFinal, isTrue);
    });

    test('fromJson handles missing optional fields gracefully', () {
      final game = Game.fromJson({'game_id': '123'});
      expect(game.gameId, '123');
      expect(game.homeWinProb, 0.5);
      expect(game.awayWinProb, 0.5);
    });
  });

  // ---------------------------------------------------------------------------
  // LiveGameData model
  // ---------------------------------------------------------------------------
  group('LiveGameData model', () {
    final Map<String, dynamic> sampleJson = {
      'home_team': 'LAL',
      'away_team': 'BOS',
      'home_win_prob': 0.72,
      'away_win_prob': 0.28,
      'home_pts': 85,
      'away_pts': 79,
      'score_diff': 6.0,
      'period': 3,
      'seconds_remaining': 300.0,
    };

    test('fromJson parses correctly', () {
      final data = LiveGameData.fromJson('0022300001', sampleJson);
      expect(data.gameId, '0022300001');
      expect(data.homeTeam, 'LAL');
      expect(data.awayTeam, 'BOS');
      expect(data.homeWinProb, closeTo(0.72, 1e-6));
      expect(data.homePts, 85);
      expect(data.period, 3);
    });

    test('leadingTeam returns home team when score_diff > 0', () {
      final data = LiveGameData.fromJson('001', sampleJson);
      expect(data.leadingTeam, 'LAL');
    });

    test('leadingTeam returns away team when score_diff < 0', () {
      final data = LiveGameData.fromJson(
        '001',
        {...sampleJson, 'score_diff': -6.0},
      );
      expect(data.leadingTeam, 'BOS');
    });

    test('leadingTeam returns Tied when score_diff == 0', () {
      final data = LiveGameData.fromJson(
        '001',
        {...sampleJson, 'score_diff': 0.0},
      );
      expect(data.leadingTeam, 'Tied');
    });

    test('periodLabel returns Q3 for period 3', () {
      final data = LiveGameData.fromJson('001', sampleJson);
      expect(data.periodLabel, 'Q3');
    });

    test('periodLabel returns OT1 for period 5', () {
      final data =
          LiveGameData.fromJson('001', {...sampleJson, 'period': 5});
      expect(data.periodLabel, 'OT1');
    });

    test('formattedClock formats correctly', () {
      final data = LiveGameData.fromJson(
        '001',
        {...sampleJson, 'seconds_remaining': 125.0},
      );
      expect(data.formattedClock, '02:05');
    });
  });

  // ---------------------------------------------------------------------------
  // Prediction model
  // ---------------------------------------------------------------------------
  group('Prediction model', () {
    test('fromJson parses all fields', () {
      final p = Prediction.fromJson({
        'home_team': 'LAL',
        'away_team': 'BOS',
        'home_win_prob': 0.6,
        'away_win_prob': 0.4,
        'predicted_winner': 'LAL',
      });
      expect(p.homeTeam, 'LAL');
      expect(p.awayTeam, 'BOS');
      expect(p.homeWinProb, closeTo(0.6, 1e-6));
      expect(p.awayWinProb, closeTo(0.4, 1e-6));
      expect(p.predictedWinner, 'LAL');
    });

    test('awayWinProb falls back to 1 - homeWinProb', () {
      final p = Prediction.fromJson({
        'home_team': 'LAL',
        'away_team': 'BOS',
        'home_win_prob': 0.65,
        'predicted_winner': 'LAL',
      });
      expect(p.awayWinProb, closeTo(0.35, 1e-6));
    });
  });
}
