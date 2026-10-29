import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';

class CurrentRatesScreen extends StatefulWidget {
  const CurrentRatesScreen({required this.apiClient, super.key});

  final RatesApiClient apiClient;

  @override
  State<CurrentRatesScreen> createState() => _CurrentRatesScreenState();
}

class _CurrentRatesScreenState extends State<CurrentRatesScreen> {
  _CurrentRatesState _state = const _LoadingRates();

  @override
  void initState() {
    super.initState();
    _loadRates();
  }

  Future<void> _loadRates() async {
    setState(() {
      _state = const _LoadingRates();
    });

    try {
      final responses = await Future.wait<Object>([
        widget.apiClient.getCurrencies(),
        widget.apiClient.getLatestRates(),
      ]);
      final currencies = responses[0] as CurrenciesResponse;
      final snapshot = responses[1] as RateSnapshot;
      final currenciesByCode = {
        for (final currency in currencies.currencies)
          if (currency.isSupported) currency.code: currency,
      };

      if (snapshot.rates.isEmpty) {
        throw const FormatException('The latest rate snapshot is empty.');
      }

      final rows = snapshot.rates
          .map((rate) {
            final currency = currenciesByCode[rate.currency];
            if (currency == null) {
              throw FormatException(
                'No supported currency metadata for ${rate.currency}.',
              );
            }
            return _CurrentRateRow(currency: currency, rate: rate);
          })
          .toList(growable: false);

      if (!mounted) {
        return;
      }
      setState(() {
        _state = _LoadedRates(snapshot: snapshot, rows: rows);
      });
    } on Exception {
      if (!mounted) {
        return;
      }
      setState(() {
        _state = const _FailedRates();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('CurrencyHub'),
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/analytics'),
            icon: const Icon(Icons.insights_outlined),
            tooltip: 'Analytics',
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/all-currencies'),
            icon: const Icon(Icons.table_chart_outlined),
            tooltip: 'All currencies',
          ),
          TextButton.icon(
            onPressed: () => Navigator.of(context).pushNamed('/converter'),
            icon: const Icon(Icons.calculate_outlined),
            label: const Text('Converter'),
          ),
        ],
      ),
      body: SafeArea(child: _buildContent(context)),
    );
  }

  Widget _buildContent(BuildContext context) {
    return switch (_state) {
      _LoadingRates() => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading current rates…'),
          ],
        ),
      ),
      _FailedRates() => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Current rates are unavailable.',
                style: Theme.of(context).textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: _loadRates, child: const Text('Retry')),
            ],
          ),
        ),
      ),
      _LoadedRates(:final snapshot, :final rows) => ListView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
        children: [
          Text(
            'Current Rates',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Snapshot collected',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  const SizedBox(height: 4),
                  SelectableText(snapshot.capturedAt),
                  const SizedBox(height: 4),
                  Text(
                    'Each rate has its own effective time.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          for (final row in rows) _RateCard(row: row),
        ],
      ),
    };
  }
}

class _CurrentRateRow {
  const _CurrentRateRow({required this.currency, required this.rate});

  final CurrencyModel currency;
  final RateEntry rate;
}

sealed class _CurrentRatesState {
  const _CurrentRatesState();
}

class _LoadingRates extends _CurrentRatesState {
  const _LoadingRates();
}

class _FailedRates extends _CurrentRatesState {
  const _FailedRates();
}

class _LoadedRates extends _CurrentRatesState {
  const _LoadedRates({required this.snapshot, required this.rows});

  final RateSnapshot snapshot;
  final List<_CurrentRateRow> rows;
}

class _RateCard extends StatelessWidget {
  const _RateCard({required this.row});

  final _CurrentRateRow row;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final rate = row.rate;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 4,
              children: [
                Text(row.currency.code, style: theme.textTheme.titleLarge),
                Text(row.currency.name, style: theme.textTheme.titleMedium),
                _InfoBadge(label: _currencyTypeLabel(row.currency.type)),
              ],
            ),
            const SizedBox(height: 14),
            Text('Rate to MDL', style: theme.textTheme.labelLarge),
            SelectableText(
              rate.normalizedRateToMdl,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text('Nominal unit: ${rate.nominalUnit}'),
            const SizedBox(height: 12),
            _DetailLine(label: 'Provider', value: rate.providerName),
            _DetailLine(
              label: 'Provider type',
              value: _currencyTypeLabel(rate.providerType),
            ),
            _DetailLine(label: 'Rate effective', value: rate.effectiveAt),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _InfoBadge(
                  label: _freshnessLabel(rate.freshnessState),
                  color: _freshnessColor(rate.freshnessState, theme),
                ),
                if (rate.isFallback) const _InfoBadge(label: 'Fallback used'),
                if (rate.isStale)
                  _InfoBadge(
                    label: 'Stale',
                    color: theme.colorScheme.errorContainer,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _currencyTypeLabel(CurrencyType type) => switch (type) {
    CurrencyType.fiat => 'Fiat',
    CurrencyType.crypto => 'Crypto',
  };

  String _freshnessLabel(FreshnessState state) => switch (state) {
    FreshnessState.live => 'Live',
    FreshnessState.fallback => 'Fallback',
    FreshnessState.cached => 'Cached',
  };

  Color _freshnessColor(FreshnessState state, ThemeData theme) =>
      switch (state) {
        FreshnessState.live => theme.colorScheme.primaryContainer,
        FreshnessState.fallback => theme.colorScheme.tertiaryContainer,
        FreshnessState.cached => theme.colorScheme.secondaryContainer,
      };
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Wrap(
        spacing: 6,
        children: [
          Text('$label:', style: Theme.of(context).textTheme.labelLarge),
          SelectableText(value),
        ],
      ),
    );
  }
}

class _InfoBadge extends StatelessWidget {
  const _InfoBadge({required this.label, this.color});

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Semantics(
      label: label,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: color ?? theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: theme.textTheme.labelMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}
