import 'package:currencyhub_mobile/core/models/rate_models.dart';
import 'package:currencyhub_mobile/features/rates/domain/all_currencies_calculator.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const calculator = AllCurrenciesCalculator();
  test('division returns decimal strings, not rational fractions', () {
    final rates = [rate('EUR', '2'), rate('USD', '4'), rate('BTC', '8')];
    final result = calculator.calculate(
      amount: '0.100000000000000001',
      sourceCurrency: 'EUR',
      rates: rates,
    );
    expect(result.map((value) => value.amount), [
      '0.100000000000000001',
      '0.0500000000000000005',
      '0.02500000000000000025',
    ]);
    expect(identical(result[2].currency, rates[2]), isTrue);
  });
  test('recurring fractions use a bounded decimal expansion', () {
    final result = calculator.calculate(
      amount: '1',
      sourceCurrency: 'EUR',
      rates: [rate('EUR', '1'), rate('USD', '3')],
    );
    expect(result.last.amount, '0.${List.filled(80, '3').join()}');
  });
  test(
    'source switching uses selected rate and preserves same-currency input',
    () {
      final result = calculator.calculate(
        amount: '1.0000',
        sourceCurrency: 'USD',
        rates: [rate('EUR', '2'), rate('USD', '4')],
      );
      expect(result.map((value) => value.amount), ['2', '1.0000']);
    },
  );
  for (final invalid in ['', '0', '-1', 'NaN', 'Infinity', 'abc']) {
    test('rejects amount $invalid', () {
      expect(
        () => calculator.calculate(
          amount: invalid,
          sourceCurrency: 'EUR',
          rates: [rate('EUR', '1')],
        ),
        throwsFormatException,
      );
    });
  }
  for (final invalid in ['0', '-1', 'NaN', 'Infinity', 'abc']) {
    test('rejects rate $invalid even for same currency', () {
      expect(
        () => calculator.calculate(
          amount: '1',
          sourceCurrency: 'EUR',
          rates: [rate('EUR', invalid)],
        ),
        throwsFormatException,
      );
    });
  }
  test('rejects missing and duplicate entries', () {
    expect(
      () => calculator.calculate(
        amount: '1',
        sourceCurrency: 'EUR',
        rates: [rate('USD', '1')],
      ),
      throwsFormatException,
    );
    expect(
      () => calculator.calculate(
        amount: '1',
        sourceCurrency: 'EUR',
        rates: [rate('EUR', '1'), rate('EUR', '2')],
      ),
      throwsFormatException,
    );
  });
}

RateEntry rate(String code, String value) => RateEntry(
  currency: code,
  normalizedRateToMdl: value,
  nominalUnit: 1,
  providerName: 'BNM',
  providerType: CurrencyType.fiat,
  effectiveAt: '2026-10-28T09:00:00Z',
  freshnessState: FreshnessState.live,
  isFallback: false,
  isStale: false,
);
