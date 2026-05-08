import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mocktail/mocktail.dart';
import 'package:nba_win_predictor/services/api_service.dart';

class MockHttpClient extends Mock implements http.Client {}
class FakeUri extends Fake implements Uri {}

void main() {
  setUpAll(() {
    registerFallbackValue(FakeUri());
  });

  late MockHttpClient mockClient;
  late ApiService api;

  setUp(() {
    mockClient = MockHttpClient();
    api = ApiService(baseUrl: 'http://localhost:5000', client: mockClient);
  });

  group('ApiService.getTodaysGames', () {
    test('returns list of Game on 200', () async {
      final responseBody = json.encode([
        {
          'game_id': '001',
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
        }
      ]);

      when(() => mockClient.get(any()))
          .thenAnswer((_) async => http.Response(responseBody, 200));

      final games = await api.getTodaysGames();
      expect(games.length, 1);
      expect(games.first.homeTeamAbbr, 'LAL');
    });

    test('throws ApiException on non-200', () async {
      when(() => mockClient.get(any()))
          .thenAnswer((_) async => http.Response('error', 502));

      expect(() => api.getTodaysGames(), throwsA(isA<ApiException>()));
    });
  });

  group('ApiService.getPrediction', () {
    test('returns Prediction on 200', () async {
      final responseBody = json.encode({
        'home_team': 'LAL',
        'away_team': 'BOS',
        'home_win_prob': 0.62,
        'away_win_prob': 0.38,
        'predicted_winner': 'LAL',
      });

      when(() => mockClient.post(
            any(),
            headers: any(named: 'headers'),
            body: any(named: 'body'),
          )).thenAnswer((_) async => http.Response(responseBody, 200));

      final prediction = await api.getPrediction(
        homeTeam: 'LAL',
        awayTeam: 'BOS',
        homeStats: {'win_pct': 0.6, 'avg_pt_diff': 3.0},
        awayStats: {'win_pct': 0.5, 'avg_pt_diff': 0.0},
      );

      expect(prediction.homeTeam, 'LAL');
      expect(prediction.homeWinProb, closeTo(0.62, 1e-6));
      expect(prediction.predictedWinner, 'LAL');
    });

    test('throws ApiException on 400', () async {
      when(() => mockClient.post(
            any(),
            headers: any(named: 'headers'),
            body: any(named: 'body'),
          )).thenAnswer((_) async => http.Response('{"error":"bad"}', 400));

      expect(
        () => api.getPrediction(
          homeTeam: 'LAL',
          awayTeam: 'BOS',
          homeStats: {},
          awayStats: {},
        ),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
