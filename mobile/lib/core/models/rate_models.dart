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

class ConversionRequest {
  const ConversionRequest({
    required this.amount,
    required this.sourceCurrency,
    required this.targetCurrency,
  });

  final String amount;
  final String sourceCurrency;
  final String targetCurrency;

  Map<String, String> toJson() => {
    'amount': amount,
    'source_currency': sourceCurrency,
    'target_currency': targetCurrency,
  };
}

class ConversionResponse {
  const ConversionResponse({
    required this.sourceAmount,
    required this.convertedAmount,
    required this.sourceCurrency,
    required this.targetCurrency,
    required this.rateValue,
    required this.rateContext,
  });

  final String sourceAmount;
  final String convertedAmount;
  final String sourceCurrency;
  final String targetCurrency;
  final String rateValue;
  final RateContext rateContext;

  factory ConversionResponse.fromJson(Map<String, dynamic> json) {
    return ConversionResponse(
      sourceAmount: _requiredString(json, 'source_amount'),
      convertedAmount: _requiredString(json, 'converted_amount'),
      sourceCurrency: _requiredString(json, 'source_currency'),
      targetCurrency: _requiredString(json, 'target_currency'),
      rateValue: _requiredString(json, 'rate_value'),
      rateContext: RateContext.fromJson(
        _requiredObject(json['rate_context'], 'rate_context'),
      ),
    );
  }
}

enum AnalyticsPeriod {
  sevenDays('7d'),
  thirtyDays('30d');

  const AnalyticsPeriod(this.wireValue);
  final String wireValue;

  static AnalyticsPeriod fromJson(String value) => switch (value) {
    '7d' => AnalyticsPeriod.sevenDays,
    '30d' => AnalyticsPeriod.thirtyDays,
    _ => throw FormatException('Unknown analytics period: "$value".'),
  };
}

class HistoryPoint {
  const HistoryPoint({
    required this.date,
    required this.value,
    required this.rateContext,
  });

  final String date;
  final String value;
  final RateContext rateContext;

  factory HistoryPoint.fromJson(Map<String, dynamic> json) => HistoryPoint(
    date: _requiredString(json, 'date'),
    value: _requiredString(json, 'value'),
    rateContext: RateContext.fromJson(
      _requiredObject(json['rate_context'], 'rate_context'),
    ),
  );
}

class HistoryResponse {
  HistoryResponse({
    required this.baseCurrency,
    required this.quoteCurrency,
    required this.period,
    required List<HistoryPoint> points,
    required this.empty,
    this.message,
  }) : points = List.unmodifiable(points);

  final String baseCurrency;
  final String quoteCurrency;
  final AnalyticsPeriod period;
  final List<HistoryPoint> points;
  final bool empty;
  final String? message;

  factory HistoryResponse.fromJson(Map<String, dynamic> json) =>
      HistoryResponse(
        baseCurrency: _requiredString(json, 'base_currency'),
        quoteCurrency: _requiredString(json, 'quote_currency'),
        period: AnalyticsPeriod.fromJson(_requiredString(json, 'period')),
        points: _requiredList(json, 'points')
            .map(
              (value) =>
                  HistoryPoint.fromJson(_requiredObject(value, 'points item')),
            )
            .toList(growable: false),
        empty: _requiredBool(json, 'empty'),
        message: _optionalString(json, 'message'),
      );
}

class AnalyticsPoint {
  const AnalyticsPoint({required this.date, required this.value});
  final String date;
  final String value;

  factory AnalyticsPoint.fromJson(Map<String, dynamic> json) => AnalyticsPoint(
    date: _requiredString(json, 'date'),
    value: _requiredString(json, 'value'),
  );
}

class RateEntryFreshnessCounts {
  const RateEntryFreshnessCounts({
    required this.live,
    required this.fallback,
    required this.cached,
  });
  final int live;
  final int fallback;
  final int cached;

  factory RateEntryFreshnessCounts.fromJson(Map<String, dynamic> json) =>
      RateEntryFreshnessCounts(
        live: _requiredInt(json, 'live'),
        fallback: _requiredInt(json, 'fallback'),
        cached: _requiredInt(json, 'cached'),
      );
}

class ProvenanceSummary {
  ProvenanceSummary({
    required this.pointCount,
    required List<String> sourceProviders,
    required List<String> targetProviders,
    required this.rateEntryFreshnessCounts,
    required this.staleEntryCount,
    required this.fallbackEntryCount,
  }) : sourceProviders = List.unmodifiable(sourceProviders),
       targetProviders = List.unmodifiable(targetProviders);

  final int pointCount;
  final List<String> sourceProviders;
  final List<String> targetProviders;
  final RateEntryFreshnessCounts rateEntryFreshnessCounts;
  final int staleEntryCount;
  final int fallbackEntryCount;

  factory ProvenanceSummary.fromJson(Map<String, dynamic> json) =>
      ProvenanceSummary(
        pointCount: _requiredInt(json, 'point_count'),
        sourceProviders: _requiredStringList(json, 'source_providers'),
        targetProviders: _requiredStringList(json, 'target_providers'),
        rateEntryFreshnessCounts: RateEntryFreshnessCounts.fromJson(
          _requiredObject(
            json['rate_entry_freshness_counts'],
            'rate_entry_freshness_counts',
          ),
        ),
        staleEntryCount: _requiredInt(json, 'stale_entry_count'),
        fallbackEntryCount: _requiredInt(json, 'fallback_entry_count'),
      );
}

enum AnalyticsTrend {
  growth,
  decline,
  unchanged;

  static AnalyticsTrend fromJson(String value) => switch (value) {
    'GROWTH' => AnalyticsTrend.growth,
    'DECLINE' => AnalyticsTrend.decline,
    'UNCHANGED' => AnalyticsTrend.unchanged,
    _ => throw FormatException('Unknown analytics trend: "$value".'),
  };
}

class AnalyticsResponse {
  AnalyticsResponse({
    required this.baseCurrency,
    required this.quoteCurrency,
    required this.period,
    required List<AnalyticsPoint> points,
    required this.provenanceSummary,
    required this.empty,
    this.minimum,
    this.maximum,
    this.average,
    this.absoluteChange,
    this.percentageChange,
    this.trend,
    this.message,
  }) : points = List.unmodifiable(points);

  final String baseCurrency;
  final String quoteCurrency;
  final AnalyticsPeriod period;
  final List<AnalyticsPoint> points;
  final String? minimum;
  final String? maximum;
  final String? average;
  final String? absoluteChange;
  final String? percentageChange;
  final AnalyticsTrend? trend;
  final ProvenanceSummary provenanceSummary;
  final bool empty;
  final String? message;

  factory AnalyticsResponse.fromJson(Map<String, dynamic> json) =>
      AnalyticsResponse(
        baseCurrency: _requiredString(json, 'base_currency'),
        quoteCurrency: _requiredString(json, 'quote_currency'),
        period: AnalyticsPeriod.fromJson(_requiredString(json, 'period')),
        points: _requiredList(json, 'points')
            .map(
              (value) => AnalyticsPoint.fromJson(
                _requiredObject(value, 'points item'),
              ),
            )
            .toList(growable: false),
        minimum: _optionalString(json, 'minimum'),
        maximum: _optionalString(json, 'maximum'),
        average: _optionalString(json, 'average'),
        absoluteChange: _optionalString(json, 'absolute_change'),
        percentageChange: _optionalString(json, 'percentage_change'),
        trend: json['trend'] == null
            ? null
            : AnalyticsTrend.fromJson(_requiredString(json, 'trend')),
        provenanceSummary: ProvenanceSummary.fromJson(
          _requiredObject(json['provenance_summary'], 'provenance_summary'),
        ),
        empty: _requiredBool(json, 'empty'),
        message: _optionalString(json, 'message'),
      );
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

String? _optionalString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value == null || value is String) return value as String?;
  throw FormatException('Expected "$key" to be a string or null.');
}

List<String> _requiredStringList(Map<String, dynamic> json, String key) =>
    _requiredList(json, key)
        .map((value) {
          if (value is String) return value;
          throw FormatException('Expected "$key" items to be strings.');
        })
        .toList(growable: false);
