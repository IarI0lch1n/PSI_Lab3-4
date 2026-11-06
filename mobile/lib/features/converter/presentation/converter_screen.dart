import 'package:flutter/material.dart';

import '../../../core/api/rates_api_client.dart';
import '../../../core/models/rate_models.dart';
import '../../../core/presentation/currency_amount_formatter.dart';
import '../../../core/presentation/currency_hub_widgets.dart';
import '../../../core/presentation/searchable_currency_picker.dart';

class ConverterScreen extends StatefulWidget {
  const ConverterScreen({required this.apiClient, super.key, this.onNavigate});

  final RatesApiClient apiClient;
  final ValueChanged<CurrencyHubDestination>? onNavigate;

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
      if (!mounted) return;
      setState(() {
        _currencies = supported;
        _isLoadingCurrencies = false;
        if (supported.isEmpty) {
          _currencyError = 'No supported currencies are available.';
        }
      });
    } on Exception {
      if (!mounted) return;
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
    if (!_canConvert) return;

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
      if (!mounted) return;
      setState(() {
        _result = result;
        _isConverting = false;
      });
    } on Exception catch (error) {
      if (!mounted) return;
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

  void _onCurrencyChanged({
    String? source,
    String? target,
    bool clear = false,
  }) {
    setState(() {
      if (clear) {
        if (source != null) _sourceCurrency = null;
        if (target != null) _targetCurrency = null;
      } else {
        if (source != null) _sourceCurrency = source;
        if (target != null) _targetCurrency = target;
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
  Widget build(BuildContext context) => CurrencyHubScaffold(
    title: 'Currency Converter',
    destination: CurrencyHubDestination.converter,
    onDestinationSelected: widget.onNavigate ?? (_) {},
    body: _buildContent(context),
  );

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
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        Text('Convert one amount', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 6),
        const Text('Using the latest validated rate snapshot.'),
        const SizedBox(height: 18),
        TextField(
          key: const Key('converter-amount'),
          controller: _amountController,
          enabled: !_isConverting,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: 'Amount',
            hintText: 'e.g. 123.45',
            errorText: _amountError,
          ),
          onChanged: _onAmountChanged,
        ),
        const SizedBox(height: 14),
        SearchableCurrencyPicker(
          key: const Key('converter-source'),
          currencies: _currencies,
          value: _sourceCurrency,
          label: 'From',
          enabled: !_isConverting,
          onChanged: (value) =>
              _onCurrencyChanged(source: value ?? '', clear: value == null),
        ),
        const SizedBox(height: 12),
        SearchableCurrencyPicker(
          key: const Key('converter-target'),
          currencies: _currencies,
          value: _targetCurrency,
          label: 'To',
          enabled: !_isConverting,
          onChanged: (value) =>
              _onCurrencyChanged(target: value ?? '', clear: value == null),
        ),
        const SizedBox(height: 18),
        FilledButton.icon(
          onPressed: _canConvert ? _convert : null,
          icon: _isConverting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.currency_exchange),
          label: Text(_isConverting ? 'Converting…' : 'Convert'),
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
          const SizedBox(height: 20),
          _ConversionResultCard(result: result),
        ],
      ],
    );
  }

  String? _validateAmount(String value) {
    final amount = value.trim();
    if (amount.isEmpty) return 'Enter a positive decimal amount.';
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
    final theme = Theme.of(context);
    return Card(
      key: const Key('conversion-result'),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Conversion result', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            Text(
              '${CurrencyAmountFormatter.format(result.sourceAmount)} ${result.sourceCurrency}',
              style: theme.textTheme.titleMedium,
            ),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Icon(Icons.south, size: 18),
            ),
            SelectableText(
              '${CurrencyAmountFormatter.format(result.convertedAmount)} ${result.targetCurrency}',
              key: const Key('formatted-converted-amount'),
              style: theme.textTheme.headlineMedium?.copyWith(
                color: theme.colorScheme.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '1 ${result.sourceCurrency} = '
              '${CurrencyAmountFormatter.format(result.rateValue)} '
              '${result.targetCurrency}',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (result.sourceCurrency == result.targetCurrency)
              FreshnessBadges(
                rate: result.rateContext.sourceRate,
                prefix: 'Rate status',
              )
            else ...[
              FreshnessBadges(
                rate: result.rateContext.sourceRate,
                prefix: 'Source ${result.sourceCurrency}',
              ),
              const SizedBox(height: 6),
              FreshnessBadges(
                rate: result.rateContext.targetRate,
                prefix: 'Target ${result.targetCurrency}',
              ),
            ],
            ExpandableDetails(
              children: [
                ProvenanceLine(
                  label: 'Snapshot',
                  value: result.rateContext.snapshotId,
                ),
                _RateDetail(
                  rate: result.rateContext.sourceRate,
                  label: 'Source',
                ),
                if (result.sourceCurrency != result.targetCurrency)
                  _RateDetail(
                    rate: result.rateContext.targetRate,
                    label: 'Target',
                  ),
                const Text(
                  'Pair rate is target-currency units per one source-currency unit.',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RateDetail extends StatelessWidget {
  const _RateDetail({required this.rate, required this.label});

  final RateProvenance rate;
  final String label;

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.surfaceContainerHighest,
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$label rate context — ${rate.currency}',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          ProvenanceLine(label: 'Provider', value: rate.providerName),
          ProvenanceLine(label: 'Rate effective', value: rate.effectiveAt),
          FreshnessBadges(rate: rate),
        ],
      ),
    ),
  );
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.errorContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Text(
        message,
        style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
      ),
    ),
  );
}
