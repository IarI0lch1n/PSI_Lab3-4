import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/rate_models.dart';

abstract interface class RateSnapshotStorage {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> remove(String key);
}

class SharedPreferencesRateSnapshotStorage implements RateSnapshotStorage {
  SharedPreferencesRateSnapshotStorage({SharedPreferencesAsync? preferences})
    : _preferences = preferences ?? SharedPreferencesAsync();

  final SharedPreferencesAsync _preferences;

  @override
  Future<String?> read(String key) => _preferences.getString(key);

  @override
  Future<void> write(String key, String value) =>
      _preferences.setString(key, value);

  @override
  Future<void> remove(String key) => _preferences.remove(key);
}

class RateSnapshotCacheException implements Exception {
  const RateSnapshotCacheException(this.message);

  final String message;

  @override
  String toString() => 'RateSnapshotCacheException: $message';
}

class RateSnapshotStore {
  RateSnapshotStore({RateSnapshotStorage? storage})
    : _storage = storage ?? SharedPreferencesRateSnapshotStorage();

  static const storageKey = 'currencyhub:last-successful-rate-snapshot:v1';
  static const _cryptoCurrentWindow = Duration(minutes: 15);

  static const Map<String, CurrencyType> _currencyTypes = {
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

  final RateSnapshotStorage _storage;

  Future<RateSnapshot?> load({DateTime? now}) async {
    final currentTime = (now ?? DateTime.now()).toUtc();
    final serialized = await _storage.read(storageKey);
    if (serialized == null) {
      return null;
    }

    Object? decoded;
    try {
      decoded = jsonDecode(serialized);
    } on FormatException {
      throw const RateSnapshotCacheException(
        'The stored rate snapshot is unreadable.',
      );
    }
    if (decoded is! Map<String, dynamic> || !_isUsableSnapshotJson(decoded)) {
      throw const RateSnapshotCacheException(
        'The stored rate snapshot is invalid or incomplete.',
      );
    }

    final snapshot = RateSnapshot.fromJson(decoded);
    return _rehydrateAsCached(snapshot, currentTime);
  }

  Future<void> save(RateSnapshot snapshot) async {
    final serialized = jsonEncode(_snapshotToJson(snapshot));
    final decoded = jsonDecode(serialized);
    if (decoded is! Map<String, dynamic> || !_isUsableSnapshotJson(decoded)) {
      throw const RateSnapshotCacheException(
        'Only a complete valid rate snapshot can be stored.',
      );
    }
    await _storage.write(storageKey, serialized);
  }

  Future<void> clear() => _storage.remove(storageKey);

  RateSnapshot _rehydrateAsCached(RateSnapshot snapshot, DateTime now) {
    final capturedAt = DateTime.parse(snapshot.capturedAt).toUtc();
    final currentDate = _moldovaDate(now);
    final capturedDate = _moldovaDate(capturedAt);
    final publicationExpected = _isBnmPublicationWeekday(currentDate);

    final rates = snapshot.rates
        .map((rate) {
          final effectiveDate = _moldovaDate(DateTime.parse(rate.effectiveAt));
          final olderFiatRate =
              rate.providerType == CurrencyType.fiat &&
              rate.currency != 'MDL' &&
              capturedDate.isBefore(currentDate) &&
              effectiveDate.isBefore(currentDate);
          final staleCrypto =
              rate.providerType == CurrencyType.crypto &&
              now.difference(capturedAt) > _cryptoCurrentWindow;

          return RateEntry(
            currency: rate.currency,
            normalizedRateToMdl: rate.normalizedRateToMdl,
            nominalUnit: rate.nominalUnit,
            providerName: rate.providerName,
            providerType: rate.providerType,
            effectiveAt: rate.effectiveAt,
            freshnessState: FreshnessState.cached,
            isFallback: rate.isFallback,
            isStale:
                rate.isStale ||
                staleCrypto ||
                (olderFiatRate && publicationExpected),
          );
        })
        .toList(growable: false);

    return RateSnapshot(
      snapshotId: snapshot.snapshotId,
      capturedAt: snapshot.capturedAt,
      rates: rates,
    );
  }

  Map<String, Object?> _snapshotToJson(RateSnapshot snapshot) => {
    'snapshot_id': snapshot.snapshotId,
    'captured_at': snapshot.capturedAt,
    'rates': snapshot.rates
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
        .toList(growable: false),
  };

  bool _isUsableSnapshotJson(Map<String, dynamic> json) {
    final snapshotId = json['snapshot_id'];
    final capturedAt = json['captured_at'];
    final rates = json['rates'];
    if (snapshotId is! String ||
        !_isUuid(snapshotId) ||
        !_isDateTime(capturedAt) ||
        rates is! List<dynamic> ||
        rates.length != _currencyTypes.length) {
      return false;
    }

    final seenCurrencies = <String>{};
    for (final value in rates) {
      if (value is! Map<String, dynamic> || !_isUsableRateJson(value)) {
        return false;
      }
      final currency = value['currency'];
      if (currency is! String || !seenCurrencies.add(currency)) {
        return false;
      }
    }
    return seenCurrencies.length == _currencyTypes.length;
  }

  bool _isUsableRateJson(Map<String, dynamic> json) {
    final currency = json['currency'];
    final rate = json['normalized_rate_to_mdl'];
    final nominalUnit = json['nominal_unit'];
    final providerName = json['provider_name'];
    final providerType = json['provider_type'];
    final effectiveAt = json['effective_at'];
    final freshnessState = json['freshness_state'];
    final isFallback = json['is_fallback'];
    final isStale = json['is_stale'];
    if (currency is! String ||
        !_currencyTypes.containsKey(currency) ||
        rate is! String ||
        !_isPositiveDecimal(rate) ||
        nominalUnit is! int ||
        nominalUnit <= 0 ||
        providerName is! String ||
        providerName.trim().isEmpty ||
        providerType != _currencyTypes[currency]!.name ||
        !_isDateTime(effectiveAt) ||
        !{'live', 'fallback', 'cached'}.contains(freshnessState) ||
        isFallback is! bool ||
        isStale is! bool) {
      return false;
    }
    return true;
  }

  bool _isUuid(String value) => RegExp(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    caseSensitive: false,
  ).hasMatch(value);

  bool _isDateTime(Object? value) {
    if (value is! String ||
        !RegExp(
          r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$',
        ).hasMatch(value)) {
      return false;
    }
    try {
      DateTime.parse(value);
      return true;
    } on FormatException {
      return false;
    }
  }

  bool _isPositiveDecimal(String value) =>
      RegExp(r'^(?:\d+(?:\.\d*)?|\.\d+)$').hasMatch(value) &&
      RegExp(r'[1-9]').hasMatch(value.replaceAll('.', ''));

  DateTime _moldovaDate(DateTime value) {
    final utc = value.toUtc();
    final summerTimeStart = _lastSundayOfMonth(utc.year, 3);
    final summerTimeEnd = _lastSundayOfMonth(utc.year, 10);
    final usesSummerTime =
        !utc.isBefore(summerTimeStart) && utc.isBefore(summerTimeEnd);
    return utc.add(Duration(hours: usesSummerTime ? 3 : 2));
  }

  DateTime _lastSundayOfMonth(int year, int month) {
    final lastDay = DateTime.utc(year, month + 1, 0);
    return DateTime.utc(year, month, lastDay.day - lastDay.weekday % 7, 1);
  }

  bool _isBnmPublicationWeekday(DateTime date) =>
      date.weekday >= DateTime.monday && date.weekday <= DateTime.friday;
}
