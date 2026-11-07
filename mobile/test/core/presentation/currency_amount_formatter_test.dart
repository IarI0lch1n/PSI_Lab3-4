import 'package:currencyhub_mobile/core/presentation/currency_amount_formatter.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('rounds ordinary amounts to two decimal places', () {
    expect(CurrencyAmountFormatter.format('50.048739'), '50.05');
  });

  test('formats large values without changing their order of magnitude', () {
    expect(CurrencyAmountFormatter.format('12647.561197'), '12647.56');
  });

  test('formats zero and values with exactly two decimal places', () {
    expect(CurrencyAmountFormatter.format('0'), '0.00');
    expect(CurrencyAmountFormatter.format('50.04'), '50.04');
  });

  test('retains readable precision for small non-zero values', () {
    expect(CurrencyAmountFormatter.format('0.000714026'), '0.000714026');
    expect(CurrencyAmountFormatter.format('0.0000000000123'), '1.23e-11');
  });

  test('leaves its input string untouched', () {
    const preciseValue = '30.86419725308641972525';
    expect(CurrencyAmountFormatter.format(preciseValue), '30.86');
    expect(preciseValue, '30.86419725308641972525');
  });
}
