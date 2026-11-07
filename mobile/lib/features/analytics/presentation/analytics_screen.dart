import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';
import '../../../core/presentation/currency_amount_formatter.dart';
import '../../../core/presentation/currency_hub_widgets.dart';
import '../../../l10n/app_localizations.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({required this.apiClient, super.key, this.onNavigate});

  final RatesApiClient apiClient;
  final ValueChanged<CurrencyHubDestination>? onNavigate;

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
  int _selectedPointIndex = 0;
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
        _selectedPointIndex = history.points.isEmpty
            ? 0
            : history.points.length - 1;
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

  void _selectPoint(int index) {
    setState(() => _selectedPointIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return CurrencyHubScaffold(
      title: l10n.rateAnalytics,
      destination: CurrencyHubDestination.analytics,
      onDestinationSelected: widget.onNavigate ?? (_) {},
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          Text(
            l10n.historicalAnalytics,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 4),
          Text(l10n.analyticsDescription),
          if (_currencies.isNotEmpty) ...[
            const SizedBox(height: 16),
            _controls(l10n),
          ],
          const SizedBox(height: 14),
          _content(l10n),
        ],
      ),
    );
  }

  Widget _controls(AppLocalizations l10n) => Column(
    children: [
      DropdownButtonFormField<String>(
        key: const Key('analytics-base'),
        initialValue: _base,
        isExpanded: true,
        decoration: InputDecoration(labelText: l10n.baseCurrency),
        items: _currencyItems(),
        onChanged: (value) {
          if (value == null || value == _base) return;
          setState(() => _base = value);
          _loadAnalytics();
        },
      ),
      const SizedBox(height: 10),
      DropdownButtonFormField<String>(
        key: const Key('analytics-quote'),
        initialValue: _quote,
        isExpanded: true,
        decoration: InputDecoration(labelText: l10n.quoteCurrency),
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
        segments: [
          ButtonSegment(
            value: AnalyticsPeriod.sevenDays,
            label: Text(l10n.sevenDays),
          ),
          ButtonSegment(
            value: AnalyticsPeriod.thirtyDays,
            label: Text(l10n.thirtyDays),
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
        child: Text('${currency.code} — ${currency.name}'),
      ),
  ];

  Widget _content(AppLocalizations l10n) {
    if (_loading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 12),
            Text(l10n.loadingAnalytics),
          ],
        ),
      );
    }
    if (_failed) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l10n.analyticsUnavailable),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _currencies.isEmpty ? _loadCurrencies : _loadAnalytics,
              child: Text(l10n.retry),
            ),
          ],
        ),
      );
    }
    final history = _history!;
    final analytics = _analytics!;
    if (history.empty) {
      return Text(l10n.noHistoricalData, key: const Key('analytics-empty'));
    }

    final selectedPoint = history.points[_selectedPointIndex];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _HistoryChart(
          points: history.points,
          selectedIndex: _selectedPointIndex,
          onSelected: _selectPoint,
        ),
        const SizedBox(height: 10),
        _SelectedPointCard(point: selectedPoint),
        const SizedBox(height: 8),
        _MetricsCard(analytics: analytics),
        const SizedBox(height: 8),
        _ProvenanceCard(summary: analytics.provenanceSummary),
      ],
    );
  }
}

class _HistoryChart extends StatelessWidget {
  const _HistoryChart({
    required this.points,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<HistoryPoint> points;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final values = points.map((point) => Decimal.parse(point.value)).toList();
    final maximum = values.reduce((a, b) => a > b ? a : b);
    return Card(
      key: const Key('analytics-chart'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 14, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.rateHistory,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 10),
            SizedBox(
              height: 156,
              child: SingleChildScrollView(
                key: const Key('analytics-chart-scroll'),
                scrollDirection: Axis.horizontal,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    for (var index = 0; index < points.length; index++)
                      _ChartBar(
                        point: points[index],
                        index: index,
                        value: values[index],
                        previousValue: index == 0 ? null : values[index - 1],
                        maximumValue: maximum,
                        selected: selectedIndex == index,
                        onTap: () => onSelected(index),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChartBar extends StatelessWidget {
  const _ChartBar({
    required this.point,
    required this.index,
    required this.value,
    required this.previousValue,
    required this.maximumValue,
    required this.selected,
    required this.onTap,
  });

  final HistoryPoint point;
  final int index;
  final Decimal value;
  final Decimal? previousValue;
  final Decimal maximumValue;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = previousValue == null
        ? CurrencyHubColors.neutral
        : value > previousValue!
        ? CurrencyHubColors.positive
        : value < previousValue!
        ? CurrencyHubColors.negative
        : CurrencyHubColors.neutral;
    final ratio = maximumValue <= Decimal.zero
        ? 0.0
        : (value / maximumValue).toDouble().clamp(0.0, 1.0).toDouble();
    final label = CurrencyAmountFormatter.format(point.value);

    return Semantics(
      button: true,
      selected: selected,
      label: '${point.date}, $label',
      child: InkWell(
        key: Key('analytics-bar-$index'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: 58,
          height: 156,
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
          decoration: selected
              ? BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: scheme.primary),
                )
              : null,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall,
              ),
              const Spacer(),
              Container(
                key: Key('analytics-bar-color-$index'),
                width: 28,
                height: 16 + (ratio * 84),
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(6),
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                point.date.substring(5),
                maxLines: 1,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectedPointCard extends StatelessWidget {
  const _SelectedPointCard({required this.point});

  final HistoryPoint point;

  @override
  Widget build(BuildContext context) {
    final source = point.rateContext.sourceRate;
    final target = point.rateContext.targetRate;
    final l10n = AppLocalizations.of(context)!;
    return Card(
      key: const Key('analytics-selected-point'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.selectedDay,
              style: Theme.of(context).textTheme.labelLarge,
            ),
            Text(point.date, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            SelectableText(
              CurrencyAmountFormatter.format(point.value),
              key: const Key('analytics-selected-value'),
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Theme.of(context).colorScheme.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const Divider(height: 24),
            _RateContextDetails(label: l10n.base, rate: source),
            const SizedBox(height: 12),
            _RateContextDetails(label: l10n.quote, rate: target),
            const SizedBox(height: 10),
            ProvenanceLine(
              label: l10n.snapshot,
              value: point.rateContext.snapshotId,
            ),
          ],
        ),
      ),
    );
  }
}

class _RateContextDetails extends StatelessWidget {
  const _RateContextDetails({required this.label, required this.rate});

  final String label;
  final RateProvenance rate;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final title = label == l10n.base
        ? l10n.baseCurrencyContext(rate.currency)
        : l10n.quoteCurrencyContext(rate.currency);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        ProvenanceLine(label: l10n.provider, value: rate.providerName),
        ProvenanceLine(label: l10n.rateEffective, value: rate.effectiveAt),
        FreshnessBadges(rate: rate),
      ],
    );
  }
}

class _MetricsCard extends StatelessWidget {
  const _MetricsCard({required this.analytics});

  final AnalyticsResponse analytics;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Card(
      key: const Key('analytics-metrics'),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _Metric(l10n.minimum, analytics.minimum!),
            _Metric(l10n.maximum, analytics.maximum!),
            _Metric(l10n.average, analytics.average!),
            _Metric(l10n.absoluteChange, analytics.absoluteChange!),
            _Metric(l10n.percentageChange, '${analytics.percentageChange!}%'),
            _Metric(
              l10n.trend,
              _trendLabel(analytics.trend!, l10n),
              isTrend: true,
            ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric(this.label, this.value, {this.isTrend = false});

  final String label;
  final String value;
  final bool isTrend;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 142,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelMedium),
        SelectableText(
          isTrend
              ? value
              : value.endsWith('%')
              ? '${CurrencyAmountFormatter.format(value.substring(0, value.length - 1))}%'
              : CurrencyAmountFormatter.format(value),
          style: Theme.of(context).textTheme.titleSmall,
        ),
      ],
    ),
  );
}

class _ProvenanceCard extends StatelessWidget {
  const _ProvenanceCard({required this.summary});

  final ProvenanceSummary summary;

  @override
  Widget build(BuildContext context) {
    final counts = summary.rateEntryFreshnessCounts;
    final l10n = AppLocalizations.of(context)!;
    return Card(
      key: const Key('analytics-provenance'),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.dataContext,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(l10n.baseProviders(summary.sourceProviders.join(', '))),
            Text(l10n.quoteProviders(summary.targetProviders.join(', '))),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                _CountChip(l10n.liveCount(counts.live)),
                _CountChip(l10n.fallbackCount(counts.fallback)),
                _CountChip(l10n.cachedCount(counts.cached)),
                _CountChip(l10n.staleCount(summary.staleEntryCount)),
                _CountChip(l10n.fallbackUsedCount(summary.fallbackEntryCount)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CountChip extends StatelessWidget {
  const _CountChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) =>
      Chip(visualDensity: VisualDensity.compact, label: Text(label));
}

String _trendLabel(AnalyticsTrend trend, AppLocalizations l10n) =>
    switch (trend) {
      AnalyticsTrend.growth => l10n.growth,
      AnalyticsTrend.decline => l10n.decline,
      AnalyticsTrend.unchanged => l10n.unchanged,
    };
