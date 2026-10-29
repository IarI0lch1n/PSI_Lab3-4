import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({required this.apiClient, super.key});
  final RatesApiClient apiClient;

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  List<CurrencyModel> _currencies = const [];
  String? _base;
  String? _quote;
  AnalyticsPeriod _period = AnalyticsPeriod.sevenDays;
  HistoryResponse? _history;
  AnalyticsResponse? _analytics;
  bool _loading = true;
  bool _failed = false;
  int _requestSequence = 0;

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
  }

  Future<void> _loadCurrencies() async {
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final response = await widget.apiClient.getCurrencies();
      final currencies = response.currencies
          .where((currency) => currency.isSupported)
          .toList(growable: false);
      if (currencies.length < 2 ||
          {for (final currency in currencies) currency.code}.length !=
              currencies.length ||
          currencies.any(
            (currency) =>
                currency.code.trim().isEmpty || currency.name.trim().isEmpty,
          )) {
        throw const FormatException('Invalid currency metadata.');
      }
      if (!mounted) return;
      setState(() {
        _currencies = currencies;
        _base = _preferredCode(currencies, 'EUR', 0);
        _quote = _preferredCode(currencies, 'BTC', 1);
      });
      await _loadAnalytics();
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  String _preferredCode(
    List<CurrencyModel> currencies,
    String preferred,
    int fallbackIndex,
  ) => currencies
      .firstWhere(
        (currency) => currency.code == preferred,
        orElse: () => currencies[fallbackIndex],
      )
      .code;

  Future<void> _loadAnalytics() async {
    final base = _base;
    final quote = _quote;
    if (base == null || quote == null) return;
    final period = _period;
    final sequence = ++_requestSequence;
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final responses = await Future.wait<Object>([
        widget.apiClient.getHistory(base, quote, period),
        widget.apiClient.getAnalytics(base, quote, period),
      ]);
      final history = responses[0] as HistoryResponse;
      final analytics = responses[1] as AnalyticsResponse;
      _validateResponses(history, analytics, base, quote, period);
      if (!mounted || sequence != _requestSequence) return;
      setState(() {
        _history = history;
        _analytics = analytics;
        _loading = false;
      });
    } on Exception {
      if (!mounted || sequence != _requestSequence) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  void _validateResponses(
    HistoryResponse history,
    AnalyticsResponse analytics,
    String base,
    String quote,
    AnalyticsPeriod period,
  ) {
    if (history.baseCurrency != base ||
        history.quoteCurrency != quote ||
        history.period != period ||
        analytics.baseCurrency != base ||
        analytics.quoteCurrency != quote ||
        analytics.period != period ||
        history.empty != analytics.empty ||
        history.points.length != analytics.points.length) {
      throw const FormatException('Mismatched analytics responses.');
    }
    for (var index = 0; index < history.points.length; index++) {
      final point = history.points[index];
      final summaryPoint = analytics.points[index];
      if (!_validDate(point.date) ||
          !_validDecimal(point.value) ||
          summaryPoint.date != point.date ||
          summaryPoint.value != point.value ||
          point.rateContext.snapshotId.trim().isEmpty ||
          !_validLeg(point.rateContext.sourceRate, base) ||
          !_validLeg(point.rateContext.targetRate, quote)) {
        throw const FormatException('Invalid historical point.');
      }
    }
    final summary = analytics.provenanceSummary;
    final counts = summary.rateEntryFreshnessCounts;
    final entryCount = history.points.length * 2;
    if (summary.pointCount != history.points.length ||
        [
          counts.live,
          counts.fallback,
          counts.cached,
          summary.staleEntryCount,
          summary.fallbackEntryCount,
        ].any((count) => count < 0) ||
        counts.live + counts.fallback + counts.cached != entryCount ||
        summary.staleEntryCount > entryCount ||
        summary.fallbackEntryCount > entryCount ||
        summary.sourceProviders.any((provider) => provider.trim().isEmpty) ||
        summary.targetProviders.any((provider) => provider.trim().isEmpty)) {
      throw const FormatException('Invalid provenance summary.');
    }
    if (!history.empty &&
        ([
              analytics.minimum,
              analytics.maximum,
              analytics.average,
              analytics.absoluteChange,
              analytics.percentageChange,
            ].any((value) => value == null || !_validDecimal(value)) ||
            analytics.trend == null)) {
      throw const FormatException('Incomplete analytics metrics.');
    }
  }

  bool _validLeg(RateProvenance leg, String code) =>
      leg.currency == code &&
      leg.providerName.trim().isNotEmpty &&
      DateTime.tryParse(leg.effectiveAt) != null;

  bool _validDate(String value) =>
      RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value) &&
      DateTime.tryParse(value) != null;

  bool _validDecimal(String value) =>
      RegExp(r'^-?(?:\d+(?:\.\d*)?|\.\d+)$').hasMatch(value);

  void _setPeriod(Set<AnalyticsPeriod> selection) {
    final value = selection.first;
    if (value == _period) return;
    setState(() => _period = value);
    _loadAnalytics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Rate Analytics')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Historical Analytics',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const Text(
              'Every point keeps the provider and effective time for both rates.',
            ),
            if (_currencies.isNotEmpty) ...[
              const SizedBox(height: 16),
              _controls(),
            ],
            const SizedBox(height: 16),
            _content(),
          ],
        ),
      ),
    );
  }

  Widget _controls() => Column(
    children: [
      DropdownButtonFormField<String>(
        key: const Key('analytics-base'),
        initialValue: _base,
        isExpanded: true,
        decoration: const InputDecoration(labelText: 'Base currency'),
        items: _currencyItems(),
        onChanged: (value) {
          if (value == null || value == _base) return;
          setState(() => _base = value);
          _loadAnalytics();
        },
      ),
      const SizedBox(height: 12),
      DropdownButtonFormField<String>(
        key: const Key('analytics-quote'),
        initialValue: _quote,
        isExpanded: true,
        decoration: const InputDecoration(labelText: 'Quote currency'),
        items: _currencyItems(),
        onChanged: (value) {
          if (value == null || value == _quote) return;
          setState(() => _quote = value);
          _loadAnalytics();
        },
      ),
      const SizedBox(height: 12),
      SegmentedButton<AnalyticsPeriod>(
        key: const Key('analytics-period'),
        segments: const [
          ButtonSegment(
            value: AnalyticsPeriod.sevenDays,
            label: Text('7 days'),
          ),
          ButtonSegment(
            value: AnalyticsPeriod.thirtyDays,
            label: Text('30 days'),
          ),
        ],
        selected: {_period},
        onSelectionChanged: _setPeriod,
      ),
    ],
  );

  List<DropdownMenuItem<String>> _currencyItems() => [
    for (final currency in _currencies)
      DropdownMenuItem(
        value: currency.code,
        child: Text('${currency.code} - ${currency.name}'),
      ),
  ];

  Widget _content() {
    if (_loading) {
      return const Center(
        child: Column(
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 12),
            Text('Loading historical analytics...'),
          ],
        ),
      );
    }
    if (_failed) {
      return Center(
        child: Column(
          children: [
            const Text('Analytics are unavailable.'),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _currencies.isEmpty ? _loadCurrencies : _loadAnalytics,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }
    final history = _history!;
    final analytics = _analytics!;
    if (history.empty) {
      return Text(
        history.message ?? 'No historical data available for this pair in the selected period.',
        key: const Key('analytics-empty'),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _MetricsCard(analytics: analytics),
        _ProvenanceCard(summary: analytics.provenanceSummary),
        for (final point in history.points)
          _PointCard(
            key: ValueKey('analytics-${point.rateContext.snapshotId}'),
            point: point,
          ),
      ],
    );
  }
}

class _MetricsCard extends StatelessWidget {
  const _MetricsCard({required this.analytics});
  final AnalyticsResponse analytics;

  @override
  Widget build(BuildContext context) => Card(
    key: const Key('analytics-metrics'),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Wrap(
        spacing: 20,
        runSpacing: 12,
        children: [
          _Metric('Minimum', analytics.minimum!),
          _Metric('Maximum', analytics.maximum!),
          _Metric('Average', analytics.average!),
          _Metric('Absolute change', analytics.absoluteChange!),
          _Metric('Percentage change', '${analytics.percentageChange!}%'),
          _Metric('Trend', _trendLabel(analytics.trend!)),
        ],
      ),
    ),
  );
}

class _Metric extends StatelessWidget {
  const _Metric(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 140,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [Text(label), SelectableText(value)],
    ),
  );
}

class _ProvenanceCard extends StatelessWidget {
  const _ProvenanceCard({required this.summary});
  final ProvenanceSummary summary;

  @override
  Widget build(BuildContext context) {
    final counts = summary.rateEntryFreshnessCounts;
    return Card(
      key: const Key('analytics-provenance'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Data context', style: Theme.of(context).textTheme.titleLarge),
            Text('Base providers: ${summary.sourceProviders.join(', ')}'),
            Text('Quote providers: ${summary.targetProviders.join(', ')}'),
            Text('Live entries: ${counts.live}'),
            Text('Fallback entries: ${counts.fallback}'),
            Text('Cached entries: ${counts.cached}'),
            Text('Stale entries: ${summary.staleEntryCount}'),
            Text('Fallback used: ${summary.fallbackEntryCount}'),
          ],
        ),
      ),
    );
  }
}

class _PointCard extends StatelessWidget {
  const _PointCard({required this.point, super.key});
  final HistoryPoint point;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(point.date, style: Theme.of(context).textTheme.titleLarge),
          SelectableText(point.value),
          const SizedBox(height: 12),
          _RateLeg(label: 'Base', rate: point.rateContext.sourceRate),
          const Divider(),
          _RateLeg(label: 'Quote', rate: point.rateContext.targetRate),
          Text('Snapshot ${point.rateContext.snapshotId}'),
        ],
      ),
    ),
  );
}

class _RateLeg extends StatelessWidget {
  const _RateLeg({required this.label, required this.rate});
  final String label;
  final RateProvenance rate;

  @override
  Widget build(BuildContext context) => Column(
    key: ValueKey('analytics-leg-$label-${rate.currency}'),
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text('$label: ${rate.currency}'),
      Text(rate.providerName),
      Text(rate.effectiveAt),
      Wrap(
        spacing: 8,
        children: [
          Chip(label: Text(_freshnessLabel(rate.freshnessState))),
          if (rate.isFallback) const Chip(label: Text('Fallback used')),
          if (rate.isStale) const Chip(label: Text('Stale')),
        ],
      ),
    ],
  );
}

String _freshnessLabel(FreshnessState state) => switch (state) {
  FreshnessState.live => 'Live',
  FreshnessState.fallback => 'Fallback',
  FreshnessState.cached => 'Cached',
};

String _trendLabel(AnalyticsTrend trend) => switch (trend) {
  AnalyticsTrend.growth => 'Growth',
  AnalyticsTrend.decline => 'Decline',
  AnalyticsTrend.unchanged => 'Unchanged',
};
