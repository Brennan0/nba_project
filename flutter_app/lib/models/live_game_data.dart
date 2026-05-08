/// Data model for live win probability data for an ongoing game.
class LiveGameData {
  final String gameId;
  final String homeTeam;
  final String awayTeam;
  final double homeWinProb;
  final double awayWinProb;
  final int homePts;
  final int awayPts;
  final double scoreDiff;
  final int period;
  final double secondsRemaining;

  const LiveGameData({
    required this.gameId,
    required this.homeTeam,
    required this.awayTeam,
    required this.homeWinProb,
    required this.awayWinProb,
    required this.homePts,
    required this.awayPts,
    required this.scoreDiff,
    required this.period,
    required this.secondsRemaining,
  });

  factory LiveGameData.fromJson(String gameId, Map<String, dynamic> json) {
    final homeWinProb = (json['home_win_prob'] as num?)?.toDouble() ?? 0.5;
    final awayWinProb = (json['away_win_prob'] as num?)?.toDouble() ??
        (1.0 - homeWinProb);
    return LiveGameData(
      gameId: gameId,
      homeTeam: json['home_team']?.toString() ?? 'HOME',
      awayTeam: json['away_team']?.toString() ?? 'AWAY',
      homeWinProb: homeWinProb,
      awayWinProb: awayWinProb,
      homePts: (json['home_pts'] as num?)?.toInt() ?? 0,
      awayPts: (json['away_pts'] as num?)?.toInt() ?? 0,
      scoreDiff: (json['score_diff'] as num?)?.toDouble() ?? 0.0,
      period: (json['period'] as num?)?.toInt() ?? 1,
      secondsRemaining:
          (json['seconds_remaining'] as num?)?.toDouble() ?? 0.0,
    );
  }

  String get leadingTeam {
    if (scoreDiff > 0) return homeTeam;
    if (scoreDiff < 0) return awayTeam;
    return 'Tied';
  }

  String get formattedClock {
    final mins = (secondsRemaining / 60).floor();
    final secs = (secondsRemaining % 60).round();
    return '${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  String get periodLabel {
    if (period == 0) return '';
    if (period <= 4) return 'Q$period';
    return 'OT${period - 4}';
  }
}
