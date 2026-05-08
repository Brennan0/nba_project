/// Data model for a single NBA game (today's schedule).
class Game {
  final String gameId;
  final String homeTeamAbbr;
  final String homeTeamName;
  final String awayTeamAbbr;
  final String awayTeamName;
  final String status;
  final int homeScore;
  final int awayScore;
  final int period;
  final String clock;
  final double homeWinProb;
  final double awayWinProb;
  final String? predictedWinner;

  const Game({
    required this.gameId,
    required this.homeTeamAbbr,
    required this.homeTeamName,
    required this.awayTeamAbbr,
    required this.awayTeamName,
    required this.status,
    required this.homeScore,
    required this.awayScore,
    required this.period,
    required this.clock,
    required this.homeWinProb,
    required this.awayWinProb,
    this.predictedWinner,
  });

  factory Game.fromJson(Map<String, dynamic> json) {
    return Game(
      gameId: json['game_id']?.toString() ?? '',
      homeTeamAbbr: json['home_team_abbr']?.toString() ?? '',
      homeTeamName: json['home_team_name']?.toString() ?? '',
      awayTeamAbbr: json['away_team_abbr']?.toString() ?? '',
      awayTeamName: json['away_team_name']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      homeScore: (json['home_score'] as num?)?.toInt() ?? 0,
      awayScore: (json['away_score'] as num?)?.toInt() ?? 0,
      period: (json['period'] as num?)?.toInt() ?? 0,
      clock: json['clock']?.toString() ?? '',
      homeWinProb: (json['home_win_prob'] as num?)?.toDouble() ?? 0.5,
      awayWinProb: (json['away_win_prob'] as num?)?.toDouble() ?? 0.5,
      predictedWinner: json['predicted_winner']?.toString(),
    );
  }

  bool get isLive => status.toLowerCase().contains('q') ||
      status.toLowerCase().contains('half') ||
      (period > 0 && !isFinal);

  bool get isFinal =>
      status.toLowerCase().contains('final') ||
      status.toLowerCase().contains('end');

  @override
  String toString() =>
      'Game($awayTeamAbbr @ $homeTeamAbbr, status: $status)';
}
