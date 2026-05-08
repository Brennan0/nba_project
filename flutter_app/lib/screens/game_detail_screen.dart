import 'dart:async';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../models/game.dart';
import '../models/live_game_data.dart';
import '../services/api_service.dart';
import '../widgets/win_probability_chart.dart';

/// Detail screen for a single game.
///
/// Shows:
/// * Live score and clock (if in progress)
/// * Animated win-probability gauge (pie chart)
/// * Historical win-probability line chart (accumulated during the session)
/// * Auto-refreshes every 30 seconds while the game is live
class GameDetailScreen extends StatefulWidget {
  final Game game;

  const GameDetailScreen({super.key, required this.game});

  @override
  State<GameDetailScreen> createState() => _GameDetailScreenState();
}

class _GameDetailScreenState extends State<GameDetailScreen> {
  final ApiService _api = ApiService();
  LiveGameData? _liveData;
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;

  // Accumulate win-probability history for the line chart
  final List<FlSpot> _probHistory = [];
  double _timeElapsed = 0.0;

  @override
  void initState() {
    super.initState();
    _fetchLiveData();
    if (widget.game.isLive) {
      _refreshTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => _fetchLiveData(),
      );
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchLiveData() async {
    setState(() {
      _loading = _liveData == null;
      _error = null;
    });
    try {
      final data = await _api.getLiveGameData(
        widget.game.gameId,
        period: widget.game.period > 0 ? widget.game.period : 1,
      );
      if (mounted) {
        setState(() {
          _liveData = data;
          _loading = false;
          // record history for the chart
          _timeElapsed = (data.period - 1) / 4.0 +
              (1.0 - data.secondsRemaining / (12.0 * 60.0)) / 4.0;
          _probHistory.add(FlSpot(
            _timeElapsed.clamp(0.0, 1.0),
            data.homeWinProb,
          ));
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final game = widget.game;

    return Scaffold(
      appBar: AppBar(
        title: Text('${game.awayTeamAbbr} @ ${game.homeTeamAbbr}'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchLiveData,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : _buildContent(theme),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text(_error ?? 'Unknown error'),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _fetchLiveData,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(ThemeData theme) {
    final live = _liveData!;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Scoreboard card
          _ScoreboardCard(game: widget.game, liveData: live),
          const SizedBox(height: 20),

          // Win probability section
          Card(
            elevation: 2,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Text(
                    'Win Probability',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  WinProbabilityChart(
                    liveData: live,
                    historySpots:
                        _probHistory.length >= 2 ? _probHistory : null,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Key stats card
          _StatsCard(liveData: live),

          // Auto-refresh note
          if (widget.game.isLive) ...[
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Auto-refreshes every 30 seconds',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Helper widgets
// ---------------------------------------------------------------------------

class _ScoreboardCard extends StatelessWidget {
  final Game game;
  final LiveGameData liveData;

  const _ScoreboardCard({required this.game, required this.liveData});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 24),
        child: Column(
          children: [
            Text(game.status, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _ScoreColumn(
                  abbr: game.awayTeamAbbr,
                  name: game.awayTeamName,
                  score: liveData.awayPts,
                  isLeading: liveData.scoreDiff < 0,
                ),
                Text(
                  '-',
                  style: theme.textTheme.headlineMedium,
                ),
                _ScoreColumn(
                  abbr: game.homeTeamAbbr,
                  name: game.homeTeamName,
                  score: liveData.homePts,
                  isLeading: liveData.scoreDiff > 0,
                ),
              ],
            ),
            if (game.isLive) ...[
              const SizedBox(height: 8),
              Text(
                '${liveData.periodLabel}  •  ${liveData.formattedClock}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.green,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ScoreColumn extends StatelessWidget {
  final String abbr;
  final String name;
  final int score;
  final bool isLeading;

  const _ScoreColumn({
    required this.abbr,
    required this.name,
    required this.score,
    required this.isLeading,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(
          abbr,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: isLeading ? FontWeight.bold : FontWeight.normal,
            color: isLeading
                ? theme.colorScheme.primary
                : theme.colorScheme.onSurface,
          ),
        ),
        Text(name, style: theme.textTheme.bodySmall),
        const SizedBox(height: 4),
        Text(
          score.toString(),
          style: theme.textTheme.displaySmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: isLeading ? theme.colorScheme.primary : null,
          ),
        ),
      ],
    );
  }
}

class _StatsCard extends StatelessWidget {
  final LiveGameData liveData;

  const _StatsCard({required this.liveData});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Game Summary',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            _StatRow(
              label: 'Score Differential',
              value: liveData.scoreDiff >= 0
                  ? '+${liveData.scoreDiff.toStringAsFixed(0)} ${liveData.homeTeam}'
                  : '${liveData.scoreDiff.toStringAsFixed(0)} ${liveData.awayTeam}',
            ),
            _StatRow(
              label: 'Leading Team',
              value: liveData.leadingTeam,
            ),
            _StatRow(
              label: '${liveData.homeTeam} Win Prob',
              value: '${(liveData.homeWinProb * 100).toStringAsFixed(1)}%',
            ),
            _StatRow(
              label: '${liveData.awayTeam} Win Prob',
              value: '${(liveData.awayWinProb * 100).toStringAsFixed(1)}%',
            ),
          ],
        ),
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final String label;
  final String value;

  const _StatRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  )),
          Text(value,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
