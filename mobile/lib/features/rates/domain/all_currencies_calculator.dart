import 'package:decimal/decimal.dart';

import '../../../core/models/rate_models.dart';

class CalculatedCurrencyValue {
  const CalculatedCurrencyValue({required this.currency, required this.amount});

  final RateEntry currency;
  final String amount;
}

class AllCurrenciesCalculator {
  const AllCurrenciesCalculator();

  List<CalculatedCurrencyValue> calculate({
    required String amount,
    required String sourceCurrency,
    required List<RateEntry> rates,
  }) {
    final sourceAmount = _parsePositiveAmount(amount);
    final sourceRate = _findRate(sourceCurrency, rates);
    final sourceNormalizedRate = _parsePositiveRate(sourceRate);

    return rates
        .map(
          (rate) => CalculatedCurrencyValue(
            currency: rate,
            amount: (sourceAmount * sourceNormalizedRate / _parsePositiveRate(rate))
                .toString(),
          ),
        )
        .toList(growable: false);
  }

  Decimal _parsePositiveAmount(String value) {
    try {
      final amount = Decimal.parse(value.trim());
      if (amount <= Decimal.zero) {
        throw const FormatException('Amount must be greater than zero.');
      }
      return amount;
    } on FormatException catch (error) {
      throw FormatException(error.message);
    }
  }

  Decimal _parsePositiveRate(RateEntry rate) {
    final normalizedRate = Decimal.parse(rate.normalizedRateToMdl);
    if (normalizedRate <= Decimal.zero) {
      throw FormatException('Rate for ${rate.currency} must be positive.');
    }
    return normalizedRate;
  }

  RateEntry _findRate(String currency, List<RateEntry> rates) {
    for (final rate in rates) {
      if (rate.currency == currency) {
        return rate;
      }
    }
    throw FormatException('Rate for $currency is unavailable.');
  }
}
