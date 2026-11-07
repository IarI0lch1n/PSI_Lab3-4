import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';
import '../../../core/presentation/currency_amount_formatter.dart';
import '../../../core/presentation/currency_hub_widgets.dart';
import '../../../l10n/app_localizations.dart';

class CurrentRatesScreen extends StatefulWidget {
  const CurrentRatesScreen({
    required this.apiClient,
    super.key,
    this.onNavigate,
  });

  final RatesApiClient apiClient;
  final ValueChanged<CurrencyHubDestination>? onNavigate;

  @override
  State<CurrentRatesScreen> createState() => _CurrentRatesScreenState();
}

class _CurrentRatesScreenState extends State<CurrentRatesScreen> {
  final _searchController = TextEditingController();
  _CurrentRatesState _state = const _LoadingRates();
  CurrencyFilter _filter = CurrencyFilter.all;

  @override
  void initState() {
    super.initState();
    _loadRates();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
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
          .where((rate) => rate.currency != 'MDL')
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

      if (!mounted) return;
      setState(() {
        _state = _LoadedRates(snapshot: snapshot, rows: rows);
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _state = const _FailedRates());
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return CurrencyHubScaffold(
      title: l10n.appName,
      destination: CurrencyHubDestination.currentRates,
      onDestinationSelected: widget.onNavigate ?? (_) {},
      body: _buildContent(context, l10n),
    );
  }

  Widget _buildContent(BuildContext context, AppLocalizations l10n) =>
      switch (_state) {
        _LoadingRates() => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(l10n.loadingCurrentRates),
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
                  l10n.currentRatesUnavailable,
                  style: Theme.of(context).textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton(onPressed: _loadRates, child: Text(l10n.retry)),
              ],
            ),
          ),
        ),
        _LoadedRates(:final snapshot, :final rows) => _buildLoaded(
          context,
          snapshot,
          rows,
          l10n,
        ),
      };

  Widget _buildLoaded(
    BuildContext context,
    RateSnapshot snapshot,
    List<_CurrentRateRow> rows,
    AppLocalizations l10n,
  ) {
    final query = _searchController.text.trim().toLowerCase();
    final visibleRows = rows
        .where((row) {
          final typeMatches = switch (_filter) {
            CurrencyFilter.all => true,
            CurrencyFilter.fiat => row.currency.type == CurrencyType.fiat,
            CurrencyFilter.crypto => row.currency.type == CurrencyType.crypto,
          };
          final searchMatches =
              query.isEmpty ||
              row.currency.code.toLowerCase().contains(query) ||
              row.currency.name.toLowerCase().contains(query);
          return typeMatches && searchMatches;
        })
        .toList(growable: false);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        Text(
          l10n.currentRates,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('current-rates-search'),
          controller: _searchController,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            labelText: l10n.searchCurrencies,
            hintText: l10n.searchCodeOrName,
            prefixIcon: const Icon(Icons.search),
          ),
        ),
        const SizedBox(height: 12),
        CurrencyTypeFilter(
          value: _filter,
          onChanged: (value) => setState(() => _filter = value),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.snapshotCollected,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 4),
                SelectableText(snapshot.capturedAt),
                const SizedBox(height: 4),
                Text(
                  l10n.eachRateEffectiveTime,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        if (visibleRows.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 12),
            child: Text(
              l10n.noCurrenciesMatch,
              key: const Key('current-rates-no-match'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          )
        else
          for (final row in visibleRows) _RateCard(row: row),
      ],
    );
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
    final l10n = AppLocalizations.of(context)!;
    return Card(
      key: Key('rate-${row.currency.code}'),
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
                CurrencyTypeBadge(type: row.currency.type),
              ],
            ),
            const SizedBox(height: 12),
            Text(l10n.rateToMdl, style: theme.textTheme.labelLarge),
            SelectableText(
              CurrencyAmountFormatter.format(rate.normalizedRateToMdl),
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 10),
            FreshnessBadges(rate: rate),
            ExpandableDetails(
              children: [
                ProvenanceLine(label: l10n.provider, value: rate.providerName),
                ProvenanceLine(
                  label: l10n.providerType,
                  value: rate.providerType == CurrencyType.fiat
                      ? l10n.filterFiat
                      : l10n.filterCrypto,
                ),
                ProvenanceLine(
                  label: l10n.rateEffective,
                  value: rate.effectiveAt,
                ),
                ProvenanceLine(
                  label: l10n.nominalUnit,
                  value: rate.nominalUnit.toString(),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
