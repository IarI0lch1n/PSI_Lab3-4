export type CurrencyType = 'fiat' | 'crypto';

export type FreshnessState = 'live' | 'fallback' | 'cached';

export interface CurrencyModel {
  readonly code: string;
  readonly name: string;
  readonly type: CurrencyType;
  readonly is_supported: boolean;
}

export interface CurrenciesResponse {
  readonly currencies: readonly CurrencyModel[];
}

export interface RateProvenance {
  readonly currency: string;
  readonly provider_name: string;
  readonly effective_at: string;
  readonly freshness_state: FreshnessState;
  readonly is_fallback: boolean;
  readonly is_stale: boolean;
}

export interface RateEntry extends RateProvenance {
  readonly normalized_rate_to_mdl: string;
  readonly nominal_unit: number;
  readonly provider_type: CurrencyType;
}

export interface RateSnapshot {
  readonly snapshot_id: string;
  readonly captured_at: string;
  readonly rates: readonly RateEntry[];
}

export interface RateContext {
  readonly source_rate: RateProvenance;
  readonly target_rate: RateProvenance;
  readonly snapshot_id: string;
}

export interface ConversionRequest {
  readonly amount: string;
  readonly source_currency: string;
  readonly target_currency: string;
}

export interface ConversionResponse {
  readonly source_amount: string;
  readonly converted_amount: string;
  readonly source_currency: string;
  readonly target_currency: string;
  readonly rate_value: string;
  readonly rate_context: RateContext;
}
