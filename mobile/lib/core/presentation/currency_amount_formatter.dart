import 'package:decimal/decimal.dart';

class CurrencyAmountFormatter {
  const CurrencyAmountFormatter._();

  static final _tinyThreshold = Decimal.parse('0.005');
  static final _scientificThreshold = Decimal.parse('0.0000000001');

  static String format(String value) {
    final amount = Decimal.parse(value.trim());
    if (amount == Decimal.zero) {
      return '0.00';
    }

    final absoluteAmount = amount.abs();
    if (absoluteAmount < _tinyThreshold) {
      if (absoluteAmount < _scientificThreshold) {
        final exponential = amount.toStringAsExponential(5).split('e');
        final mantissa = _trimFractionZeros(exponential.first);
        return '$mantissa e${exponential.last}'.replaceAll(' ', '');
      }
      return _trimFractionZeros(amount.toStringAsPrecision(6));
    }

    return amount.toStringAsFixed(2);
  }

  static String _trimFractionZeros(String value) => value.contains('.')
      ? value.replaceFirst(RegExp(r'0+$'), '').replaceFirst(RegExp(r'\.$'), '')
      : value;
}
