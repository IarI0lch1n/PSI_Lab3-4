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

  test('parses exact analytics strings and independent provenance counts', () {
    final response = AnalyticsResponse.fromJson({
      'base_currency': 'EUR',
      'quote_currency': 'BTC',
      'period': '7d',
      'points': [
        {'date': '2026-10-28', 'value': '0.000032100000000000001'},
      ],
      'minimum': '0.000032100000000000001',
      'maximum': '0.000032100000000000001',
      'average': '0.000032100000000000001',
      'absolute_change': '0',
      'percentage_change': '0',
      'trend': 'UNCHANGED',
      'provenance_summary': {
        'point_count': 1,
        'source_providers': ['BNM'],
        'target_providers': ['CoinGecko'],
        'rate_entry_freshness_counts': {'live': 0, 'fallback': 1, 'cached': 1},
        'stale_entry_count': 1,
        'fallback_entry_count': 1,
      },
      'empty': false,
    });

    expect(response.period, AnalyticsPeriod.sevenDays);
    expect(response.points.single.value, '0.000032100000000000001');
    expect(response.points.single.value, isA<String>());
    expect(response.trend, AnalyticsTrend.unchanged);
    expect(response.provenanceSummary.sourceProviders, ['BNM']);
    expect(response.provenanceSummary.rateEntryFreshnessCounts.fallback, 1);
    expect(response.provenanceSummary.staleEntryCount, 1);
    expect(response.provenanceSummary.fallbackEntryCount, 1);
    expect(
      () => response.points.add(response.points.single),
      throwsUnsupportedError,
    );
  });
}
