/// Data model for a win-probability prediction result.
class Prediction {
  final String homeTeam;
  final String awayTeam;
  final double homeWinProb;
  final double awayWinProb;
  final String predictedWinner;

  const Prediction({
    required this.homeTeam,
    required this.awayTeam,
    required this.homeWinProb,
    required this.awayWinProb,
    required this.predictedWinner,
  });

  factory Prediction.fromJson(Map<String, dynamic> json) {
    final homeWinProb = (json['home_win_prob'] as num?)?.toDouble() ?? 0.5;
    return Prediction(
      homeTeam: json['home_team']?.toString() ?? '',
      awayTeam: json['away_team']?.toString() ?? '',
      homeWinProb: homeWinProb,
      awayWinProb: (json['away_win_prob'] as num?)?.toDouble() ??
          (1.0 - homeWinProb),
      predictedWinner: json['predicted_winner']?.toString() ?? '',
    );
  }
}
