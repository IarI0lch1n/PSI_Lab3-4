enum CurrencyType {
  fiat,
  crypto;

  static CurrencyType fromJson(String value) => switch (value) {
    'fiat' => CurrencyType.fiat,
    'crypto' => CurrencyType.crypto,
    _ => throw FormatException('Unknown currency type: "$value".'),
  };
}

enum FreshnessState {
  live,
  fallback,
  cached;

  static FreshnessState fromJson(String value) => switch (value) {
    'live' => FreshnessState.live,
    'fallback' => FreshnessState.fallback,
    'cached' => FreshnessState.cached,
    _ => throw FormatException('Unknown freshness state: "$value".'),
  };
}

class CurrencyModel {
  const CurrencyModel({
    required this.code,
    required this.name,
    required this.type,
    required this.isSupported,
  });

  final String code;
  final String name;
  final CurrencyType type;
  final bool isSupported;

  factory CurrencyModel.fromJson(Map<String, dynamic> json) {
    return CurrencyModel(
      code: _requiredString(json, 'code'),
      name: _requiredString(json, 'name'),
      type: CurrencyType.fromJson(_requiredString(json, 'type')),
      isSupported: _requiredBool(json, 'is_supported'),
    );
  }
}

class CurrenciesResponse {
  CurrenciesResponse({required List<CurrencyModel> currencies})
    : currencies = List.unmodifiable(currencies);

  final List<CurrencyModel> currencies;

  factory CurrenciesResponse.fromJson(Map<String, dynamic> json) {
    final currencies = _requiredList(json, 'currencies').map((value) {
      return CurrencyModel.fromJson(_requiredObject(value, 'currencies item'));
    });

    return CurrenciesResponse(currencies: currencies.toList(growable: false));
  }
}

class RateProvenance {
  const RateProvenance({
    required this.currency,
    required this.providerName,
    required this.effectiveAt,
    required this.freshnessState,
    required this.isFallback,
    required this.isStale,
  });

  final String currency;
  final String providerName;
  final String effectiveAt;
  final FreshnessState freshnessState;
  final bool isFallback;
  final bool isStale;

  factory RateProvenance.fromJson(Map<String, dynamic> json) {
    return RateProvenance(
      currency: _requiredString(json, 'currency'),
      providerName: _requiredString(json, 'provider_name'),
      effectiveAt: _requiredString(json, 'effective_at'),
      freshnessState: FreshnessState.fromJson(
        _requiredString(json, 'freshness_state'),
      ),
      isFallback: _requiredBool(json, 'is_fallback'),
      isStale: _requiredBool(json, 'is_stale'),
    );
  }
}

class RateEntry extends RateProvenance {
  const RateEntry({
    required super.currency,
    required super.providerName,
    required super.effectiveAt,
    required super.freshnessState,
    required super.isFallback,
    required super.isStale,
    required this.normalizedRateToMdl,
    required this.nominalUnit,
    required this.providerType,
  });

  final String normalizedRateToMdl;
  final int nominalUnit;
  final CurrencyType providerType;

  factory RateEntry.fromJson(Map<String, dynamic> json) {
    final provenance = RateProvenance.fromJson(json);

    return RateEntry(
      currency: provenance.currency,
      providerName: provenance.providerName,
      effectiveAt: provenance.effectiveAt,
      freshnessState: provenance.freshnessState,
      isFallback: provenance.isFallback,
      isStale: provenance.isStale,
      normalizedRateToMdl: _requiredString(json, 'normalized_rate_to_mdl'),
      nominalUnit: _requiredInt(json, 'nominal_unit'),
      providerType: CurrencyType.fromJson(
        _requiredString(json, 'provider_type'),
      ),
    );
  }
}

class RateSnapshot {
  RateSnapshot({
    required this.snapshotId,
    required this.capturedAt,
    required List<RateEntry> rates,
  }) : rates = List.unmodifiable(rates);

  final String snapshotId;
  final String capturedAt;
  final List<RateEntry> rates;

  factory RateSnapshot.fromJson(Map<String, dynamic> json) {
    final rates = _requiredList(json, 'rates').map((value) {
      return RateEntry.fromJson(_requiredObject(value, 'rates item'));
    });

    return RateSnapshot(
      snapshotId: _requiredString(json, 'snapshot_id'),
      capturedAt: _requiredString(json, 'captured_at'),
      rates: rates.toList(growable: false),
    );
  }
}

class RateContext {
  const RateContext({
    required this.sourceRate,
    required this.targetRate,
    required this.snapshotId,
  });

  final RateProvenance sourceRate;
  final RateProvenance targetRate;
  final String snapshotId;

  factory RateContext.fromJson(Map<String, dynamic> json) {
    return RateContext(
      sourceRate: RateProvenance.fromJson(
        _requiredObject(json['source_rate'], 'source_rate'),
      ),
      targetRate: RateProvenance.fromJson(
        _requiredObject(json['target_rate'], 'target_rate'),
      ),
      snapshotId: _requiredString(json, 'snapshot_id'),
    );
  }
}

String _requiredString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is String) {
    return value;
  }
  throw FormatException('Expected "$key" to be a string.');
}

bool _requiredBool(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is bool) {
    return value;
  }
  throw FormatException('Expected "$key" to be a boolean.');
}

int _requiredInt(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is int) {
    return value;
  }
  throw FormatException('Expected "$key" to be an integer.');
}

List<dynamic> _requiredList(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is List<dynamic>) {
    return value;
  }
  throw FormatException('Expected "$key" to be a list.');
}

Map<String, dynamic> _requiredObject(Object? value, String fieldName) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  throw FormatException('Expected "$fieldName" to be a JSON object.');
}
