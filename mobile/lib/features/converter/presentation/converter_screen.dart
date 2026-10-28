import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';

class ConverterScreen extends StatefulWidget {
  const ConverterScreen({required this.apiClient, super.key});

  final RatesApiClient apiClient;

  @override
  State<ConverterScreen> createState() => _ConverterScreenState();
}

class _ConverterScreenState extends State<ConverterScreen> {
  final _amountController = TextEditingController();
  List<CurrencyModel> _currencies = const [];
  String? _sourceCurrency;
  String? _targetCurrency;
  String? _currencyError;
  String? _conversionError;
  ConversionResponse? _result;
  bool _isLoadingCurrencies = true;
  bool _isConverting = false;

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrencies() async {
    setState(() {
      _isLoadingCurrencies = true;
      _currencyError = null;
      _currencies = const [];
      _sourceCurrency = null;
      _targetCurrency = null;
      _result = null;
      _conversionError = null;
    });

    try {
      final response = await widget.apiClient.getCurrencies();
      final supported = response.currencies
          .where((currency) => currency.isSupported)
          .toList(growable: false);
      if (!mounted) {
        return;
      }
      setState(() {
        _currencies = supported;
        _isLoadingCurrencies = false;
        if (supported.isEmpty) {
          _currencyError = 'No supported currencies are available.';
        }
      });
    } on Exception {
      if (!mounted) {
        return;
      }
      setState(() {
        _isLoadingCurrencies = false;
        _currencyError = 'Supported currencies are unavailable.';
      });
    }
  }

  String? get _amountError => _validateAmount(_amountController.text);

  bool get _canConvert =>
      !_isLoadingCurrencies &&
      _currencyError == null &&
      _amountError == null &&
      _sourceCurrency != null &&
      _targetCurrency != null &&
      !_isConverting;

  Future<void> _convert() async {
    if (!_canConvert) {
      return;
    }

    setState(() {
      _isConverting = true;
      _result = null;
      _conversionError = null;
    });

    try {
      final result = await widget.apiClient.convert(
        ConversionRequest(
          amount: _amountController.text.trim(),
          sourceCurrency: _sourceCurrency!,
          targetCurrency: _targetCurrency!,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _isConverting = false;
      });
    } on Exception catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _conversionError = _conversionErrorMessage(error);
        _isConverting = false;
      });
    }
  }

  void _onAmountChanged(String _) {
    setState(() {
      _result = null;
      _conversionError = null;
    });
  }

  void _onCurrencyChanged({String? source, String? target}) {
    setState(() {
      if (source != null) {
        _sourceCurrency = source;
      }
      if (target != null) {
        _targetCurrency = target;
      }
      _result = null;
      _conversionError = null;
    });
  }

  String _conversionErrorMessage(Exception error) {
    if (error is! RatesApiException) {
      return 'Conversion could not be completed. Please try again.';
    }

    return switch (error.errorCode) {
      'rate_unavailable' =>
        error.safeMessage ?? 'A required currency rate is unavailable.',
      'invalid_conversion_input' =>
        'Enter a valid amount and select supported currencies.',
      'conversion_unavailable' =>
        'Conversion is currently unavailable. Try again later.',
      _ => 'Conversion could not be completed. Please try again.',
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Currency Converter')),
      body: SafeArea(child: _buildContent(context)),
    );
  }

  Widget _buildContent(BuildContext context) {
    if (_isLoadingCurrencies) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading supported currencies…'),
          ],
        ),
      );
    }

    if (_currencyError case final error?) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(error, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _loadCurrencies,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
      children: [
        Text('Convert one amount', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text('The conversion uses the latest validated rate snapshot.'),
        const SizedBox(height: 20),
        TextField(
          controller: _amountController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: 'Amount',
            hintText: 'e.g. 123.45',
            errorText: _amountError,
          ),
          onChanged: _onAmountChanged,
        ),
        const SizedBox(height: 16),
        _currencySelector(
          label: 'From',
          value: _sourceCurrency,
          onChanged: (value) => _onCurrencyChanged(source: value),
        ),
        const SizedBox(height: 12),
        _currencySelector(
          label: 'To',
          value: _targetCurrency,
          onChanged: (value) => _onCurrencyChanged(target: value),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _canConvert ? _convert : null,
          child: _isConverting
              ? const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    SizedBox(width: 12),
                    Text('Converting…'),
                  ],
                )
              : const Text('Convert'),
        ),
        if (_isConverting) ...[
          const SizedBox(height: 16),
          const Center(child: Text('Converting…')),
        ],
        if (_conversionError case final error?) ...[
          const SizedBox(height: 16),
          _ErrorPanel(message: error),
        ],
        if (_result case final result?) ...[
          const SizedBox(height: 24),
          _ConversionResultCard(result: result),
        ],
      ],
    );
  }

  Widget _currencySelector({
    required String label,
    required String? value,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      hint: const Text('Select a currency'),
      items: [
        for (final currency in _currencies)
          DropdownMenuItem(
            value: currency.code,
            child: Text('${currency.code} — ${currency.name}'),
          ),
      ],
      onChanged: _isConverting ? null : onChanged,
    );
  }

  String? _validateAmount(String value) {
    final amount = value.trim();
    if (amount.isEmpty) {
      return 'Enter a positive decimal amount.';
    }
    if (!RegExp(r'^(?:\d+(?:\.\d*)?|\.\d+)$').hasMatch(amount)) {
      return 'Enter a valid positive decimal amount.';
    }
    if (!RegExp(r'[1-9]').hasMatch(amount)) {
      return 'Amount must be greater than zero.';
    }
    return null;
  }
}

class _ConversionResultCard extends StatelessWidget {
  const _ConversionResultCard({required this.result});

  final ConversionResponse result;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Conversion result',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            SelectableText('${result.sourceAmount} ${result.sourceCurrency}'),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Text('converts to'),
            ),
            SelectableText(
              '${result.convertedAmount} ${result.targetCurrency}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            _ResultDetail(
              label: 'Pair rate',
              value:
                  '1 ${result.sourceCurrency} = ${result.rateValue} ${result.targetCurrency}',
            ),
            const Text(
              'Rate value is target-currency units per one source-currency unit.',
            ),
            const SizedBox(height: 8),
            _ResultDetail(
              label: 'Snapshot',
              value: result.rateContext.snapshotId,
            ),
            const SizedBox(height: 16),
            _RateContextCard(
              title: 'Source rate context',
              rate: result.rateContext.sourceRate,
            ),
            const SizedBox(height: 8),
            _RateContextCard(
              title: 'Target rate context',
              rate: result.rateContext.targetRate,
            ),
          ],
        ),
      ),
    );
  }
}

class _RateContextCard extends StatelessWidget {
  const _RateContextCard({required this.title, required this.rate});

  final String title;
  final RateProvenance rate;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$title — ${rate.currency}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            _ResultDetail(label: 'Provider', value: rate.providerName),
            _ResultDetail(label: 'Rate effective', value: rate.effectiveAt),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StateBadge(label: _freshnessLabel(rate.freshnessState)),
                if (rate.isFallback) const _StateBadge(label: 'Fallback used'),
                if (rate.isStale) const _StateBadge(label: 'Stale'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _freshnessLabel(FreshnessState state) => switch (state) {
    FreshnessState.live => 'Live',
    FreshnessState.fallback => 'Fallback',
    FreshnessState.cached => 'Cached',
  };
}

class _ResultDetail extends StatelessWidget {
  const _ResultDetail({required this.label, required this.value});

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

class _StateBadge extends StatelessWidget {
  const _StateBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text(label), visualDensity: VisualDensity.compact);
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.errorContainer,
      child: Padding(padding: const EdgeInsets.all(16), child: Text(message)),
    );
  }
}
