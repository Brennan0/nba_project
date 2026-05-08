import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/live_game_data.dart';

/// A gauge-style chart showing home vs away win probability.
class WinProbabilityChart extends StatelessWidget {
  final LiveGameData liveData;
  final List<FlSpot>? historySpots;

  const WinProbabilityChart({
    super.key,
    required this.liveData,
    this.historySpots,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Donut pie chart for current win probabilities
        SizedBox(
          height: 220,
          child: PieChart(
            PieChartData(
              sectionsSpace: 3,
              centerSpaceRadius: 55,
              sections: [
                PieChartSectionData(
                  value: liveData.homeWinProb * 100,
                  color: theme.colorScheme.primary,
                  title:
                      '${(liveData.homeWinProb * 100).toStringAsFixed(1)}%',
                  radius: 55,
                  titleStyle: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                PieChartSectionData(
                  value: liveData.awayWinProb * 100,
                  color: theme.colorScheme.secondary,
                  title:
                      '${(liveData.awayWinProb * 100).toStringAsFixed(1)}%',
                  radius: 50,
                  titleStyle: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        // Legend
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _LegendItem(
              color: theme.colorScheme.primary,
              label: liveData.homeTeam,
            ),
            const SizedBox(width: 24),
            _LegendItem(
              color: theme.colorScheme.secondary,
              label: liveData.awayTeam,
            ),
          ],
        ),
        // Optional line chart for probability history
        if (historySpots != null && historySpots!.isNotEmpty) ...[
          const SizedBox(height: 24),
          const Text(
            'Win Probability Over Time',
            textAlign: TextAlign.center,
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 160,
            child: LineChart(
              LineChartData(
                minX: 0,
                maxX: 1,
                minY: 0,
                maxY: 1,
                gridData: const FlGridData(show: false),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      getTitlesWidget: (value, meta) => Text(
                        '${(value * 100).toInt()}%',
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) => Text(
                        'Q${(value * 4 + 1).toInt()}',
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ),
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: historySpots!,
                    isCurved: true,
                    color: theme.colorScheme.primary,
                    barWidth: 2.5,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: theme.colorScheme.primary.withAlpha(60),
                    ),
                  ),
                  // Mirror line for away team
                  LineChartBarData(
                    spots: historySpots!
                        .map((s) => FlSpot(s.x, 1 - s.y))
                        .toList(),
                    isCurved: true,
                    color: theme.colorScheme.secondary,
                    barWidth: 2.5,
                    dotData: const FlDotData(show: false),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }
}
