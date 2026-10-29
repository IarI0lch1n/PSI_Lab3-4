import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';
import '../domain/all_currencies_calculator.dart';

class AllCurrenciesScreen extends StatefulWidget {
  const AllCurrenciesScreen({required this.apiClient, super.key});

  final RatesApiClient apiClient;

  @override
  State<AllCurrenciesScreen> createState() => _AllCurrenciesScreenState();
}

class _AllCurrenciesScreenState extends State<AllCurrenciesScreen> {
  final _amount = TextEditingController(text: '1');
  final _calculator = const AllCurrenciesCalculator();
  List<CurrencyModel> _currencies = const [];
  RateSnapshot? _snapshot;
  String? _source;
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
    // Validate every normalized rate before presenting any complete comparison.
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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('All Currencies')),
      body: SafeArea(child: _content(context)),
    );
  }

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
    final values = _amountError == null
        ? _calculator.calculate(
            amount: _amount.text,
            sourceCurrency: _source!,
            rates: snapshot.rates,
          )
        : <CalculatedCurrencyValue>[];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Compare currencies using the same rate snapshot.'),
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
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          key: const Key('comparison-source'),
          initialValue: _source,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Entry currency'),
          items: [
            for (final currency in _currencies)
              DropdownMenuItem(
                value: currency.code,
                child: Text('${currency.code} — ${currency.name}'),
              ),
          ],
          onChanged: (value) {
            if (value != null) setState(() => _source = value);
          },
        ),
        const SizedBox(height: 16),
        const Text('Snapshot collected'),
        SelectableText(snapshot.capturedAt),
        const Text(
          'Each currency below has its own provider and effective time.',
        ),
        const SizedBox(height: 16),
        for (final value in values)
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
    final state = switch (rate.freshnessState) {
      FreshnessState.live => 'Live',
      FreshnessState.fallback => 'Fallback',
      FreshnessState.cached => 'Cached',
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(rate.currency, style: Theme.of(context).textTheme.titleLarge),
            Text(name),
            const SizedBox(height: 8),
            SelectableText(
              value.amount,
              key: ValueKey('value-${rate.currency}'),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            const Text('Provider'),
            Text(rate.providerName),
            const Text('Rate effective'),
            Text(rate.effectiveAt),
            Wrap(
              spacing: 8,
              children: [
                Chip(label: Text(state)),
                if (rate.isFallback) const Chip(label: Text('Fallback used')),
                if (rate.isStale) const Chip(label: Text('Stale')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
