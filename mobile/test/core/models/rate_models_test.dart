import 'package:flutter_test/flutter_test.dart';

import 'package:currencyhub_mobile/core/models/rate_models.dart';

void main() {
  group('CurrencyType', () {
    test('parses fiat and crypto strictly', () {
      expect(CurrencyType.fromJson('fiat'), CurrencyType.fiat);
      expect(CurrencyType.fromJson('crypto'), CurrencyType.crypto);
      expect(() => CurrencyType.fromJson('other'), throwsFormatException);
    });
  });

  group('FreshnessState', () {
    test('parses the three primary statuses strictly', () {
      expect(FreshnessState.fromJson('live'), FreshnessState.live);
      expect(FreshnessState.fromJson('fallback'), FreshnessState.fallback);
      expect(FreshnessState.fromJson('cached'), FreshnessState.cached);
      expect(() => FreshnessState.fromJson('stale'), throwsFormatException);
    });
  });

  test('parses snapshot provenance without conflating fallback and stale', () {
    final snapshot = RateSnapshot.fromJson({
      'snapshot_id': 'snapshot-123',
      'captured_at': '2026-10-28T09:00:00Z',
      'rates': [
        {
          'currency': 'RON',
          'normalized_rate_to_mdl': '17.400000000000000001',
          'nominal_unit': 1,
          'provider_name': 'BNM',
          'provider_type': 'fiat',
          'effective_at': '2026-10-28T08:00:00Z',
          'freshness_state': 'fallback',
          'is_fallback': true,
          'is_stale': false,
        },
        {
          'currency': 'BTC',
          'normalized_rate_to_mdl': '542240.10',
          'nominal_unit': 1,
          'provider_name': 'CoinGecko',
          'provider_type': 'crypto',
          'effective_at': '2026-10-28T08:30:00Z',
          'freshness_state': 'cached',
          'is_fallback': false,
          'is_stale': true,
        },
      ],
    });

    final fiat = snapshot.rates[0];
    expect(fiat.freshnessState, FreshnessState.fallback);
    expect(fiat.isFallback, isTrue);
    expect(fiat.isStale, isFalse);
    expect(fiat.normalizedRateToMdl, '17.400000000000000001');
    expect(fiat.normalizedRateToMdl, isA<String>());

    final crypto = snapshot.rates[1];
    expect(crypto.freshnessState, FreshnessState.cached);
    expect(crypto.isFallback, isFalse);
    expect(crypto.isStale, isTrue);
    expect(crypto.providerType, CurrencyType.crypto);
    expect(() => snapshot.rates.add(fiat), throwsUnsupportedError);
  });

  test('parses currency and reusable rate context models', () {
    final currencies = CurrenciesResponse.fromJson({
      'currencies': [
        {
          'code': 'USD',
          'name': 'US Dollar',
          'type': 'fiat',
          'is_supported': true,
        },
      ],
    });
    expect(currencies.currencies.single.isSupported, isTrue);
    expect(currencies.currencies.single.type, CurrencyType.fiat);
    expect(
      () => currencies.currencies.add(currencies.currencies.single),
      throwsUnsupportedError,
    );

    final context = RateContext.fromJson({
      'source_rate': {
        'currency': 'EUR',
        'provider_name': 'BNM',
        'effective_at': '2026-10-28T08:00:00Z',
        'freshness_state': 'live',
        'is_fallback': false,
        'is_stale': false,
      },
      'target_rate': {
        'currency': 'BTC',
        'provider_name': 'CoinGecko',
        'effective_at': '2026-10-28T08:30:00Z',
        'freshness_state': 'cached',
        'is_fallback': false,
        'is_stale': true,
      },
      'snapshot_id': 'snapshot-123',
    });
    expect(context.sourceRate.currency, 'EUR');
    expect(context.targetRate.currency, 'BTC');
    expect(context.snapshotId, 'snapshot-123');
  });
}
