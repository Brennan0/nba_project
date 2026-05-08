import 'package:flutter/material.dart';
import '../models/game.dart';

/// A card displaying a single game's matchup and pre-game win prediction.
class GameCard extends StatelessWidget {
  final Game game;
  final VoidCallback? onTap;

  const GameCard({super.key, required this.game, this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              // Status chip
              _StatusChip(status: game.status),
              const SizedBox(height: 12),
              // Teams row
              Row(
                children: [
                  Expanded(
                    child: _TeamColumn(
                      abbr: game.awayTeamAbbr,
                      name: game.awayTeamName,
                      score: game.awayScore,
                      winProb: game.awayWinProb,
                      isWinner: game.predictedWinner == game.awayTeamAbbr,
                      showScore: game.period > 0,
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text(
                      '@',
                      style: theme.textTheme.titleLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                  Expanded(
                    child: _TeamColumn(
                      abbr: game.homeTeamAbbr,
                      name: game.homeTeamName,
                      score: game.homeScore,
                      winProb: game.homeWinProb,
                      isWinner: game.predictedWinner == game.homeTeamAbbr,
                      showScore: game.period > 0,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Win probability bar
              _WinProbBar(
                homeProb: game.homeWinProb,
                awayProb: game.awayWinProb,
                homeAbbr: game.homeTeamAbbr,
                awayAbbr: game.awayTeamAbbr,
              ),
              if (game.predictedWinner != null) ...[
                const SizedBox(height: 8),
                Text(
                  'Predicted: ${game.predictedWinner}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final isLive = status.toLowerCase().contains('q') ||
        status.toLowerCase().contains('half');
    final isFinal = status.toLowerCase().contains('final') ||
        status.toLowerCase().contains('end');

    Color color;
    if (isLive) {
      color = Colors.green;
    } else if (isFinal) {
      color = Colors.grey;
    } else {
      color = Theme.of(context).colorScheme.primaryContainer;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(30),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withAlpha(100)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isLive) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: Colors.green,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
          ],
          Text(
            status,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _TeamColumn extends StatelessWidget {
  final String abbr;
  final String name;
  final int score;
  final double winProb;
  final bool isWinner;
  final bool showScore;

  const _TeamColumn({
    required this.abbr,
    required this.name,
    required this.score,
    required this.winProb,
    required this.isWinner,
    required this.showScore,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(
          abbr,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: isWinner ? FontWeight.bold : FontWeight.normal,
            color: isWinner
                ? theme.colorScheme.primary
                : theme.colorScheme.onSurface,
          ),
        ),
        Text(
          name,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        if (showScore) ...[
          const SizedBox(height: 4),
          Text(
            score.toString(),
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
        const SizedBox(height: 4),
        Text(
          '${(winProb * 100).toStringAsFixed(1)}%',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.primary,
          ),
        ),
      ],
    );
  }
}

class _WinProbBar extends StatelessWidget {
  final double homeProb;
  final double awayProb;
  final String homeAbbr;
  final String awayAbbr;

  const _WinProbBar({
    required this.homeProb,
    required this.awayProb,
    required this.homeAbbr,
    required this.awayAbbr,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: SizedBox(
        height: 8,
        child: Row(
          children: [
            Expanded(
              flex: (awayProb * 1000).round(),
              child: Container(
                color: theme.colorScheme.secondary,
              ),
            ),
            Expanded(
              flex: (homeProb * 1000).round(),
              child: Container(
                color: theme.colorScheme.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
