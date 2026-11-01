import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:currencyhub_mobile/core/cache/rate_snapshot_store.dart';
import 'package:currencyhub_mobile/core/models/rate_models.dart';

const _snapshotId = '00000000-0000-4000-8000-000000000055';
const _replacementSnapshotId = '00000000-0000-4000-8000-000000000056';
const _capturedAt = '2026-10-28T12:00:00Z';
const _storageKey = 'currencyhub:last-successful-rate-snapshot:v1';

const _currencyTypes = <String, CurrencyType>{
  'MDL': CurrencyType.fiat,
  'USD': CurrencyType.fiat,
  'EUR': CurrencyType.fiat,
  'RUB': CurrencyType.fiat,
  'CNY': CurrencyType.fiat,
  'GBP': CurrencyType.fiat,
  'RON': CurrencyType.fiat,
  'UAH': CurrencyType.fiat,
  'CHF': CurrencyType.fiat,
  'JPY': CurrencyType.fiat,
  'BTC': CurrencyType.crypto,
  'ETH': CurrencyType.crypto,
  'SOL': CurrencyType.crypto,
  'BNB': CurrencyType.crypto,
  'XRP': CurrencyType.crypto,
  'ADA': CurrencyType.crypto,
  'DOGE': CurrencyType.crypto,
  'USDT': CurrencyType.crypto,
};

void main() {
  group('RateSnapshotStore', () {
    late MemoryRateSnapshotStorage storage;
    late RateSnapshotStore store;

    setUp(() {
      storage = MemoryRateSnapshotStorage();
      store = RateSnapshotStore(storage: storage);
    });

    test('returns unavailable when there is no persisted snapshot', () async {
      expect(await store.load(), isNull);
      expect(storage.removeCalls, 0);
    });

    test(
      'persists and rehydrates the complete snapshot without age deletion',
      () async {
        final snapshot = _createSnapshot();
        await store.save(snapshot);

        final restartedStore = RateSnapshotStore(storage: storage);
        final rehydrated = await restartedStore.load(
          now: DateTime.parse('2036-10-28T12:00:00Z'),
        );

        expect(rehydrated, isNotNull);
        expect(rehydrated!.snapshotId, snapshot.snapshotId);
        expect(rehydrated.capturedAt, snapshot.capturedAt);
        expect(rehydrated.rates, hasLength(_currencyTypes.length));
        expect(
          rehydrated.rates.every(
            (rate) => rate.freshnessState == FreshnessState.cached,
          ),
          isTrue,
        );
        expect(storage.value, isNotNull);
        expect(storage.removeCalls, 0);
      },
    );

    test(
      'reports unreadable JSON and structurally invalid snapshots',
      () async {
        storage.value = '{not json';
        await expectLater(
          store.load(),
          throwsA(isA<RateSnapshotCacheException>()),
        );

        final incomplete = _createSnapshot();
        storage.value = jsonEncode({
          'snapshot_id': incomplete.snapshotId,
          'captured_at': incomplete.capturedAt,
          'rates': incomplete.rates
              .skip(1)
              .map(
                (rate) => {
                  'currency': rate.currency,
                  'normalized_rate_to_mdl': rate.normalizedRateToMdl,
                  'nominal_unit': rate.nominalUnit,
                  'provider_name': rate.providerName,
                  'provider_type': rate.providerType.name,
                  'effective_at': rate.effectiveAt,
                  'freshness_state': rate.freshnessState.name,
                  'is_fallback': rate.isFallback,
                  'is_stale': rate.isStale,
                },
              )
              .toList(),
        });
        await expectLater(
          store.load(),
          throwsA(
            isA<RateSnapshotCacheException>()
                .having(
                  (error) => error.unavailableCurrencies,
                  'unavailable currencies',
                  ['MDL'],
                )
                .having(
                  (error) => error.message,
                  'message',
                  contains('Unavailable required currencies: MDL.'),
                ),
          ),
        );
      },
    );

    test('rejects incomplete or unusable snapshots before writing', () async {
      final snapshot = _createSnapshot();
      final incomplete = RateSnapshot(
        snapshotId: snapshot.snapshotId,
        capturedAt: snapshot.capturedAt,
        rates: snapshot.rates.skip(1).toList(),
      );

      await expectLater(
        store.save(incomplete),
        throwsA(isA<RateSnapshotCacheException>()),
      );
      expect(storage.writeCalls, 0);
      expect(storage.value, isNull);

      final invalidRates = [...snapshot.rates];
      invalidRates[0] = _copyRate(invalidRates[0], normalizedRateToMdl: '0');
      final invalid = RateSnapshot(
        snapshotId: snapshot.snapshotId,
        capturedAt: snapshot.capturedAt,
        rates: invalidRates,
      );

      await expectLater(
        store.save(invalid),
        throwsA(isA<RateSnapshotCacheException>()),
      );
      expect(storage.writeCalls, 0);
    });

    test('rejects structurally invalid cached rates instead of returning partial data', () async {
      final mutations = <void Function(Map<String, dynamic>)>[
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          snapshot['rates'] = rates.skip(1).toList();
        },
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          final first = rates.first as Map<String, dynamic>;
          final last = rates.last as Map<String, dynamic>;
          last['currency'] = first['currency'];
        },
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          (rates.first as Map<String, dynamic>)['normalized_rate_to_mdl'] =
              '1e3';
        },
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          (rates.first as Map<String, dynamic>)['provider_name'] = ' ';
        },
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          (rates.first as Map<String, dynamic>)['provider_type'] = 'crypto';
        },
        (snapshot) {
          final rates = snapshot['rates'] as List<dynamic>;
          (rates.first as Map<String, dynamic>)['effective_at'] = 'not-a-time';
        },
      ];

      for (final mutate in mutations) {
        await store.save(_createSnapshot());
        final decoded = jsonDecode(storage.value!) as Map<String, dynamic>;
        mutate(decoded);
        storage.value = jsonEncode(decoded);

        await expectLater(
          store.load(),
          throwsA(isA<RateSnapshotCacheException>()),
        );
      }
    });

    test(
      'rehydrates cached state and preserves provenance and original times',
      () async {
        final snapshot = _createSnapshot();
        await store.save(snapshot);
        final serializedBeforeLoad = storage.value;

        final rehydrated = await store.load(now: DateTime.parse(_capturedAt));

        expect(rehydrated, isNotNull);
        expect(rehydrated!.capturedAt, snapshot.capturedAt);
        expect(
          rehydrated.rates.map((rate) => rate.effectiveAt),
          snapshot.rates.map((rate) => rate.effectiveAt),
        );
        expect(
          rehydrated.rates.every(
            (rate) => rate.freshnessState == FreshnessState.cached,
          ),
          isTrue,
        );
        final fallbackRate = rehydrated.rates.singleWhere(
          (rate) => rate.currency == 'USD',
        );
        expect(fallbackRate.providerName, 'BNM');
        expect(fallbackRate.effectiveAt, '2026-10-27T00:00:00+02:00');
        expect(fallbackRate.isFallback, isTrue);
        expect(fallbackRate.isStale, isFalse);
        expect(storage.value, serializedBeforeLoad);
      },
    );

    test('resolves cached required rates with original provider and effective time', () async {
      final snapshot = _createSnapshot();
      await store.save(snapshot);
      final cached = await store.load(now: DateTime.parse(_capturedAt));

      final resolution = store.resolveRequiredRates(cached, ['BTC', 'EUR']);

      expect(resolution.isAvailable, isTrue);
      expect(resolution.rates.map((rate) => rate.currency), ['BTC', 'EUR']);
      expect(resolution.rates[0].providerName, 'CoinGecko');
      expect(resolution.rates[0].effectiveAt, '2026-10-28T11:45:00Z');
      expect(resolution.rates[0].freshnessState, FreshnessState.cached);
      expect(resolution.rates[0].isFallback, isFalse);
      expect(resolution.rates[1].providerName, 'BNM');
      expect(resolution.rates[1].effectiveAt, '2026-10-28T09:00:00Z');
      expect(resolution.rates[1].freshnessState, FreshnessState.cached);
      expect(resolution.rates[1].isFallback, isFalse);
    });

    test('identifies unavailable required currencies without exposing a partial pair', () {
      final snapshot = _createSnapshot();
      final partial = RateSnapshot(
        snapshotId: snapshot.snapshotId,
        capturedAt: snapshot.capturedAt,
        rates: snapshot.rates.where((rate) => rate.currency != 'BTC').toList(),
      );

      final resolution = store.resolveRequiredRates(partial, ['EUR', 'BTC']);

      expect(resolution.isAvailable, isFalse);
      expect(resolution.rates, isEmpty);
      expect(resolution.unavailableCurrencies, ['BTC']);
      expect(
        resolution.message,
        'Required currency rates are unavailable: BTC.',
      );
    });

    test(
      'reports required currencies unavailable when there is no snapshot',
      () {
        final resolution = store.resolveRequiredRates(null, ['EUR', 'BTC']);

        expect(resolution.isAvailable, isFalse);
        expect(resolution.rates, isEmpty);
        expect(resolution.unavailableCurrencies, ['EUR', 'BTC']);
        expect(
          resolution.message,
          'Required currency rates are unavailable: EUR, BTC.',
        );
      },
    );

    test('preserves canonical freshness and provenance semantics through outage and restart', () async {
      final snapshot = _createCrossClientSnapshot();
      await store.save(snapshot);
      final storedSnapshot = storage.value;

      final persisted = jsonDecode(storedSnapshot!) as Map<String, dynamic>;
      final persistedRates = {
        for (final rate in persisted['rates'] as List<dynamic>)
          (rate as Map<String, dynamic>)['currency'] as String: rate,
      };
      expect(persistedRates['MDL'], containsPair('freshness_state', 'live'));
      expect(persistedRates['MDL'], containsPair('is_fallback', false));
      expect(persistedRates['MDL'], containsPair('is_stale', false));
      expect(
        persistedRates['USD'],
        containsPair('freshness_state', 'fallback'),
      );
      expect(persistedRates['USD'], containsPair('is_fallback', true));
      expect(persistedRates['USD'], containsPair('is_stale', false));
      expect(persistedRates['USD'], containsPair('provider_name', 'BNM'));
      expect(
        persistedRates['USD'],
        containsPair('effective_at', '2026-10-30T09:00:00Z'),
      );
      expect(persistedRates['EUR'], containsPair('freshness_state', 'cached'));
      expect(persistedRates['EUR'], containsPair('is_fallback', false));
      expect(persistedRates['EUR'], containsPair('is_stale', false));
      expect(persistedRates['BTC'], containsPair('freshness_state', 'cached'));
      expect(persistedRates['BTC'], containsPair('is_fallback', false));
      expect(persistedRates['BTC'], containsPair('is_stale', true));

      storage.failWrites = true;
      final replacement = _createSnapshot(
        snapshotId: _replacementSnapshotId,
        capturedAt: '2026-10-28T13:00:00Z',
      );
      await expectLater(store.save(replacement), throwsA(isA<StateError>()));
      expect(storage.value, storedSnapshot);

      final restartedStore = RateSnapshotStore(storage: storage);
      final offline = await restartedStore.load(
        now: DateTime.parse(snapshot.capturedAt),
      );
      final rates = {for (final rate in offline!.rates) rate.currency: rate};

      expect(rates['MDL']!.freshnessState, FreshnessState.cached);
      expect(rates['MDL']!.isFallback, isFalse);
      expect(rates['MDL']!.isStale, isFalse);
      expect(rates['MDL']!.providerName, 'BNM');
      expect(rates['MDL']!.effectiveAt, '2026-10-28T09:00:00Z');
      expect(rates['USD']!.freshnessState, FreshnessState.cached);
      expect(rates['USD']!.isFallback, isTrue);
      expect(rates['USD']!.isStale, isFalse);
      expect(rates['USD']!.providerName, 'BNM');
      expect(rates['USD']!.effectiveAt, '2026-10-30T09:00:00Z');
      expect(rates['EUR']!.freshnessState, FreshnessState.cached);
      expect(rates['EUR']!.isFallback, isFalse);
      expect(rates['EUR']!.isStale, isFalse);
      expect(rates['EUR']!.providerName, 'BNM');
      expect(rates['EUR']!.effectiveAt, '2026-10-28T09:00:00Z');
      expect(rates['BTC']!.freshnessState, FreshnessState.cached);
      expect(rates['BTC']!.isFallback, isFalse);
      expect(rates['BTC']!.isStale, isTrue);
      expect(rates['BTC']!.providerName, 'CoinGecko');
      expect(rates['BTC']!.effectiveAt, '2026-10-28T11:45:00Z');

      final laterWeekday = await restartedStore.load(
        now: DateTime.parse('2026-11-02T12:00:00Z'),
      );
      final weekdayEur = laterWeekday!.rates.singleWhere(
        (rate) => rate.currency == 'EUR',
      );
      expect(weekdayEur.freshnessState, FreshnessState.cached);
      expect(weekdayEur.isFallback, isFalse);
      expect(weekdayEur.isStale, isTrue);
      expect(weekdayEur.providerName, 'BNM');
      expect(weekdayEur.effectiveAt, '2026-10-28T09:00:00Z');

      final incomplete = RateSnapshot(
        snapshotId: offline.snapshotId,
        capturedAt: offline.capturedAt,
        rates: offline.rates.where((rate) => rate.currency != 'BTC').toList(),
      );
      final pair = restartedStore.resolveRequiredRates(incomplete, [
        'EUR',
        'BTC',
      ]);
      expect(pair.isAvailable, isFalse);
      expect(pair.unavailableCurrencies, ['BTC']);
      expect(pair.rates, isEmpty);
    });

    test(
      'keeps cached status independent from fallback and stale flags',
      () async {
        final snapshot = _createSnapshot(
          rates: [
            for (final rate in _createSnapshot().rates)
              if (rate.currency == 'BTC')
                _copyRate(
                  rate,
                  freshnessState: FreshnessState.cached,
                  isFallback: false,
                  isStale: false,
                )
              else
                rate,
          ],
        );
        await store.save(snapshot);

        final rehydrated = await store.load(now: DateTime.parse(_capturedAt));
        final bitcoin = rehydrated!.rates.singleWhere(
          (rate) => rate.currency == 'BTC',
        );

        expect(bitcoin.freshnessState, FreshnessState.cached);
        expect(bitcoin.isFallback, isFalse);
        expect(bitcoin.isStale, isFalse);
      },
    );

    test(
      'recalculates crypto staleness at and beyond the 15-minute boundary',
      () async {
        await store.save(_createSnapshot());

        final atBoundary = await store.load(
          now: DateTime.parse('2026-10-28T12:15:00.000Z'),
        );
        final afterBoundary = await store.load(
          now: DateTime.parse('2026-10-28T12:15:00.001Z'),
        );
        final boundaryBitcoin = atBoundary!.rates.singleWhere(
          (rate) => rate.currency == 'BTC',
        );
        final staleBitcoin = afterBoundary!.rates.singleWhere(
          (rate) => rate.currency == 'BTC',
        );

        expect(boundaryBitcoin.isStale, isFalse);
        expect(staleBitcoin.isStale, isTrue);
        expect(staleBitcoin.effectiveAt, '2026-10-28T11:45:00Z');
        expect(staleBitcoin.isFallback, isFalse);
        expect(afterBoundary.capturedAt, _capturedAt);
      },
    );

    test(
      'marks older fiat stale on a publication weekday but not a weekend',
      () async {
        await store.save(_createSnapshot());

        final weekday = await store.load(
          now: DateTime.parse('2026-10-29T12:00:00Z'),
        );
        final weekend = await store.load(
          now: DateTime.parse('2026-10-31T12:00:00Z'),
        );

        expect(
          weekday!.rates.singleWhere((rate) => rate.currency == 'EUR').isStale,
          isTrue,
        );
        expect(
          weekend!.rates.singleWhere((rate) => rate.currency == 'EUR').isStale,
          isFalse,
        );
      },
    );

    test(
      'replaces valid snapshots and preserves the previous value on failure',
      () async {
        final original = _createSnapshot();
        await store.save(original);
        final originalValue = storage.value;
        final replacement = _createSnapshot(
          snapshotId: _replacementSnapshotId,
          capturedAt: '2026-10-28T13:00:00Z',
        );

        storage.failWrites = true;
        await expectLater(store.save(replacement), throwsA(isA<StateError>()));
        expect(storage.value, originalValue);

        storage.failWrites = false;
        await store.save(replacement);
        expect(storage.writeCalls, 3);
        expect(
          (await store.load(now: DateTime.parse(replacement.capturedAt)))!
              .snapshotId,
          replacement.snapshotId,
        );

        final replacementValue = storage.value;
        final incomplete = RateSnapshot(
          snapshotId: replacement.snapshotId,
          capturedAt: replacement.capturedAt,
          rates: replacement.rates.skip(1).toList(),
        );
        await expectLater(
          store.save(incomplete),
          throwsA(isA<RateSnapshotCacheException>()),
        );
        expect(storage.value, replacementValue);
        expect(storage.writeCalls, 3);
      },
    );

    test('clears only when explicitly requested', () async {
      await store.save(_createSnapshot());
      await store.clear();

      expect(await store.load(), isNull);
      expect(storage.removeCalls, 1);
      expect(storage.removedKeys, [_storageKey]);
    });
  });
}

class MemoryRateSnapshotStorage implements RateSnapshotStorage {
  String? value;
  bool failWrites = false;
  int writeCalls = 0;
  int removeCalls = 0;
  final removedKeys = <String>[];

  @override
  Future<String?> read(String key) async => key == _storageKey ? value : null;

  @override
  Future<void> write(String key, String value) async {
    writeCalls++;
    if (failWrites) {
      throw StateError('Storage write failed.');
    }
    if (key == _storageKey) {
      this.value = value;
    }
  }

  @override
  Future<void> remove(String key) async {
    removeCalls++;
    removedKeys.add(key);
    if (key == _storageKey) {
      value = null;
    }
  }
}

RateSnapshot _createSnapshot({
  String snapshotId = _snapshotId,
  String capturedAt = _capturedAt,
  List<RateEntry>? rates,
}) {
  final entries =
      rates ??
      _currencyTypes.entries.indexed
          .map((indexedEntry) {
            final index = indexedEntry.$1;
            final entry = indexedEntry.$2;
            final isFallback = entry.key == 'USD';
            final effectiveAt = switch (entry.key) {
              'USD' => '2026-10-27T00:00:00+02:00',
              'BTC' => '2026-10-28T11:45:00Z',
              _ => '2026-10-28T09:00:00Z',
            };
            return RateEntry(
              currency: entry.key,
              normalizedRateToMdl: '${index + 1}',
              nominalUnit: 1,
              providerName: entry.value == CurrencyType.crypto
                  ? 'CoinGecko'
                  : 'BNM',
              providerType: entry.value,
              effectiveAt: effectiveAt,
              freshnessState: isFallback
                  ? FreshnessState.fallback
                  : FreshnessState.live,
              isFallback: isFallback,
              isStale: false,
            );
          })
          .toList(growable: false);

  return RateSnapshot(
    snapshotId: snapshotId,
    capturedAt: capturedAt,
    rates: entries,
  );
}

RateSnapshot _createCrossClientSnapshot() {
  final snapshot = _createSnapshot();
  return RateSnapshot(
    snapshotId: snapshot.snapshotId,
    capturedAt: '2026-10-31T12:00:00Z',
    rates: snapshot.rates
        .map((rate) {
          switch (rate.currency) {
            case 'MDL':
              return _copyRate(
                rate,
                freshnessState: FreshnessState.live,
                isFallback: false,
                isStale: false,
              );
            case 'USD':
              return RateEntry(
                currency: rate.currency,
                normalizedRateToMdl: rate.normalizedRateToMdl,
                nominalUnit: rate.nominalUnit,
                providerName: rate.providerName,
                providerType: rate.providerType,
                effectiveAt: '2026-10-30T09:00:00Z',
                freshnessState: FreshnessState.fallback,
                isFallback: true,
                isStale: false,
              );
            case 'EUR':
              return _copyRate(
                rate,
                freshnessState: FreshnessState.cached,
                isFallback: false,
                isStale: false,
              );
            case 'BTC':
              return _copyRate(
                rate,
                freshnessState: FreshnessState.cached,
                isFallback: false,
                isStale: true,
              );
            default:
              return rate;
          }
        })
        .toList(growable: false),
  );
}

RateEntry _copyRate(
  RateEntry rate, {
  FreshnessState? freshnessState,
  String? normalizedRateToMdl,
  bool? isFallback,
  bool? isStale,
}) => RateEntry(
  currency: rate.currency,
  normalizedRateToMdl: normalizedRateToMdl ?? rate.normalizedRateToMdl,
  nominalUnit: rate.nominalUnit,
  providerName: rate.providerName,
  providerType: rate.providerType,
  effectiveAt: rate.effectiveAt,
  freshnessState: freshnessState ?? rate.freshnessState,
  isFallback: isFallback ?? rate.isFallback,
  isStale: isStale ?? rate.isStale,
);
