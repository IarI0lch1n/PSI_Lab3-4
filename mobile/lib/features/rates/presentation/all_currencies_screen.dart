import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';
import '../../../core/presentation/currency_amount_formatter.dart';
import '../../../core/presentation/currency_hub_widgets.dart';
import '../../../core/presentation/searchable_currency_picker.dart';
import '../domain/all_currencies_calculator.dart';

class AllCurrenciesScreen extends StatefulWidget {
  const AllCurrenciesScreen({
    required this.apiClient,
    super.key,
    this.onNavigate,
  });

  final RatesApiClient apiClient;
  final ValueChanged<CurrencyHubDestination>? onNavigate;

  @override
  State<AllCurrenciesScreen> createState() => _AllCurrenciesScreenState();
}

class _AllCurrenciesScreenState extends State<AllCurrenciesScreen> {
  final _amount = TextEditingController(text: '1');
  final _calculator = const AllCurrenciesCalculator();
  List<CurrencyModel> _currencies = const [];
  RateSnapshot? _snapshot;
  String? _source;
  CurrencyFilter _filter = CurrencyFilter.all;
  bool _loading = true;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final responses = await Future.wait<Object>([
        widget.apiClient.getCurrencies(),
        widget.apiClient.getLatestRates(),
      ]);
      final currencies = (responses[0] as CurrenciesResponse).currencies
          .where((currency) => currency.isSupported)
          .toList(growable: false);
      final snapshot = responses[1] as RateSnapshot;
      _validateSnapshot(currencies, snapshot);
      if (!mounted) return;
      setState(() {
        _currencies = currencies;
        _snapshot = snapshot;
        _source = currencies.first.code;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  void _validateSnapshot(
    List<CurrencyModel> currencies,
    RateSnapshot snapshot,
  ) {
    final codes = {for (final currency in currencies) currency.code};
    final rateCodes = {for (final rate in snapshot.rates) rate.currency};
    if (currencies.isEmpty ||
        codes.length != currencies.length ||
        snapshot.snapshotId.trim().isEmpty ||
        DateTime.tryParse(snapshot.capturedAt) == null ||
        rateCodes.length != snapshot.rates.length ||
        codes.length != rateCodes.length ||
        !codes.containsAll(rateCodes) ||
        currencies.any(
          (currency) =>
              currency.name.trim().isEmpty || currency.code.trim().isEmpty,
        )) {
      throw const FormatException('Incomplete snapshot.');
    }
    for (final rate in snapshot.rates) {
      final currency = currencies.firstWhere(
        (currency) => currency.code == rate.currency,
      );
      if (rate.providerName.trim().isEmpty ||
          DateTime.tryParse(rate.effectiveAt) == null ||
          currency.type != rate.providerType ||
          rate.nominalUnit <= 0) {
        throw const FormatException('Invalid rate metadata.');
      }
    }
    _calculator.calculate(
      amount: '1',
      sourceCurrency: currencies.first.code,
      rates: snapshot.rates,
    );
  }

  String? get _amountError {
    final value = _amount.text.trim();
    if (!RegExp(r'^(?:\d+(?:\.\d*)?|\.\d+)$').hasMatch(value)) {
      return 'Enter a valid positive decimal amount.';
    }
    if (!RegExp(r'[1-9]').hasMatch(value)) {
      return 'Amount must be greater than zero.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) => CurrencyHubScaffold(
    title: 'All Currencies',
    destination: CurrencyHubDestination.allCurrencies,
    onDestinationSelected: widget.onNavigate ?? (_) {},
    body: _content(context),
  );

  Widget _content(BuildContext context) {
    if (_loading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading currency comparison...'),
          ],
        ),
      );
    }
    if (_failed) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Comparison is unavailable. A complete rate snapshot is required.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: _load, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final snapshot = _snapshot!;
    final values = _amountError == null && _source != null
        ? _calculator.calculate(
            amount: _amount.text,
            sourceCurrency: _source!,
            rates: snapshot.rates,
          )
        : <CalculatedCurrencyValue>[];
    final visibleValues = values
        .where((value) {
          if (value.currency.currency == _source) return false;
          return switch (_filter) {
            CurrencyFilter.all => true,
            CurrencyFilter.fiat =>
              value.currency.providerType == CurrencyType.fiat,
            CurrencyFilter.crypto =>
              value.currency.providerType == CurrencyType.crypto,
          };
        })
        .toList(growable: false);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        Text(
          'Compare currencies',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 4),
        const Text('All values use the same validated rate snapshot.'),
        const SizedBox(height: 16),
        TextField(
          key: const Key('comparison-amount'),
          controller: _amount,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: 'Amount',
            errorText: _amountError,
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 14),
        SearchableCurrencyPicker(
          key: const Key('comparison-source'),
          currencies: _currencies,
          value: _source,
          label: 'Entry currency',
          onChanged: (value) => setState(() => _source = value),
        ),
        if (_source == null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Select a supported entry currency.',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        const SizedBox(height: 12),
        CurrencyTypeFilter(
          value: _filter,
          onChanged: (value) => setState(() => _filter = value),
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
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
                const Text('Rate details remain available on each result.'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        if (_amountError == null && _source != null && visibleValues.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 28),
            child: Text(
              'No other currencies match this filter.',
              textAlign: TextAlign.center,
            ),
          ),
        for (final value in visibleValues)
          _ComparisonCard(
            key: ValueKey('comparison-${value.currency.currency}'),
            value: value,
            name: _currencies
                .firstWhere(
                  (currency) => currency.code == value.currency.currency,
                )
                .name,
          ),
      ],
    );
  }
}

class _ComparisonCard extends StatelessWidget {
  const _ComparisonCard({required this.value, required this.name, super.key});

  final CalculatedCurrencyValue value;
  final String name;

  @override
  Widget build(BuildContext context) {
    final rate = value.currency;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  rate.currency,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                Text(name, style: Theme.of(context).textTheme.titleMedium),
                CurrencyTypeBadge(type: rate.providerType),
              ],
            ),
            const SizedBox(height: 8),
            SelectableText(
              CurrencyAmountFormatter.format(value.amount),
              key: ValueKey('value-${rate.currency}'),
              style: Theme.of(context).textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            FreshnessBadges(rate: rate),
            ExpandableDetails(
              children: [
                ProvenanceLine(label: 'Provider', value: rate.providerName),
                ProvenanceLine(
                  label: 'Rate effective',
                  value: rate.effectiveAt,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
