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

export type AnalyticsPeriod = '7d' | '30d';

export interface HistoryPoint {
  readonly date: string;
  readonly value: string;
  readonly rate_context: RateContext;
}

export interface HistoryResponse {
  readonly base_currency: string;
  readonly quote_currency: string;
  readonly period: AnalyticsPeriod;
  readonly points: readonly HistoryPoint[];
  readonly empty: boolean;
  readonly message?: string;
}

export interface AnalyticsPoint {
  readonly date: string;
  readonly value: string;
}

export interface RateEntryFreshnessCounts {
  readonly live: number;
  readonly fallback: number;
  readonly cached: number;
}

export interface ProvenanceSummary {
  readonly point_count: number;
  readonly source_providers: readonly string[];
  readonly target_providers: readonly string[];
  readonly rate_entry_freshness_counts: RateEntryFreshnessCounts;
  readonly stale_entry_count: number;
  readonly fallback_entry_count: number;
}

export type AnalyticsTrend = 'GROWTH' | 'DECLINE' | 'UNCHANGED';

export interface AnalyticsResponse {
  readonly base_currency: string;
  readonly quote_currency: string;
  readonly period: AnalyticsPeriod;
  readonly points: readonly AnalyticsPoint[];
  readonly minimum?: string;
  readonly maximum?: string;
  readonly average?: string;
  readonly absolute_change?: string;
  readonly percentage_change?: string;
  readonly trend?: AnalyticsTrend;
  readonly provenance_summary: ProvenanceSummary;
  readonly empty: boolean;
  readonly message?: string;
}
