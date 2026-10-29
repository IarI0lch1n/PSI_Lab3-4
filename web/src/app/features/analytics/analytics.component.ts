import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin } from 'rxjs';
import { RatesApiService } from '../../core/api/rates-api.service';
import {
  AnalyticsPeriod,
  AnalyticsResponse,
  CurrencyModel,
  HistoryPoint,
  HistoryResponse,
  RateProvenance,
} from '../../core/models/rate.models';

type AnalyticsViewState =
  | { readonly status: 'loading' }
  | { readonly status: 'error' }
  | {
      readonly status: 'ready';
      readonly history: HistoryResponse;
      readonly analytics: AnalyticsResponse;
    };

@Component({
  selector: 'app-analytics',
  standalone: false,
  styleUrl: './analytics.component.scss',
  templateUrl: './analytics.component.html',
})
export class AnalyticsComponent implements OnInit {
  protected readonly currencies = signal<readonly CurrencyModel[]>([]);
  protected readonly baseCurrency = signal('');
  protected readonly quoteCurrency = signal('');
  protected readonly period = signal<AnalyticsPeriod>('7d');
  protected readonly state = signal<AnalyticsViewState>({ status: 'loading' });

  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private requestSequence = 0;

  ngOnInit(): void {
    this.loadCurrencies();
  }

  protected retry(): void {
    if (this.currencies().length === 0) {
      this.loadCurrencies();
    } else {
      this.loadAnalytics();
    }
  }

  protected setBaseCurrency(event: Event): void {
    const select = event.target;
    if (select instanceof HTMLSelectElement && select.value !== this.baseCurrency()) {
      this.baseCurrency.set(select.value);
      this.loadAnalytics();
    }
  }

  protected setQuoteCurrency(event: Event): void {
    const select = event.target;
    if (select instanceof HTMLSelectElement && select.value !== this.quoteCurrency()) {
      this.quoteCurrency.set(select.value);
      this.loadAnalytics();
    }
  }

  protected setPeriod(value: AnalyticsPeriod): void {
    if (value !== this.period()) {
      this.period.set(value);
      this.loadAnalytics();
    }
  }

  private loadCurrencies(): void {
    this.state.set({ status: 'loading' });
    this.api
      .getCurrencies()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          const currencies = response.currencies.filter(
            (currency) =>
              currency.is_supported &&
              Boolean(currency.code?.trim()) &&
              Boolean(currency.name?.trim()),
          );
          if (
            currencies.length < 2 ||
            new Set(currencies.map(({ code }) => code)).size !== currencies.length
          ) {
            this.state.set({ status: 'error' });
            return;
          }
          this.currencies.set(currencies);
          this.baseCurrency.set(
            currencies.find(({ code }) => code === 'EUR')?.code ?? currencies[0].code,
          );
          this.quoteCurrency.set(
            currencies.find(({ code }) => code === 'BTC')?.code ?? currencies[1].code,
          );
          this.loadAnalytics();
        },
        error: () => this.state.set({ status: 'error' }),
      });
  }

  private loadAnalytics(): void {
    const base = this.baseCurrency();
    const quote = this.quoteCurrency();
    const period = this.period();
    if (!base || !quote) {
      this.state.set({ status: 'error' });
      return;
    }
    const requestSequence = ++this.requestSequence;
    this.state.set({ status: 'loading' });
    forkJoin({
      history: this.api.getHistory(base, quote, period),
      analytics: this.api.getAnalytics(base, quote, period),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ history, analytics }) => {
          if (requestSequence !== this.requestSequence) {
            return;
          }
          if (this.validResponses(history, analytics, base, quote, period)) {
            this.state.set({ status: 'ready', history, analytics });
          } else {
            this.state.set({ status: 'error' });
          }
        },
        error: () => {
          if (requestSequence === this.requestSequence) {
            this.state.set({ status: 'error' });
          }
        },
      });
  }

  private validResponses(
    history: HistoryResponse,
    analytics: AnalyticsResponse,
    base: string,
    quote: string,
    period: AnalyticsPeriod,
  ): boolean {
    if (
      history.base_currency !== base ||
      history.quote_currency !== quote ||
      history.period !== period ||
      analytics.base_currency !== base ||
      analytics.quote_currency !== quote ||
      analytics.period !== period ||
      history.empty !== analytics.empty ||
      !Array.isArray(history.points) ||
      !Array.isArray(analytics.points) ||
      history.points.length !== analytics.points.length ||
      history.points.some(
        (point, index) => !this.validPoint(point, base, quote, analytics.points[index]),
      )
    ) {
      return false;
    }
    const summary = analytics.provenance_summary;
    if (
      !summary ||
      !Array.isArray(summary.source_providers) ||
      !Array.isArray(summary.target_providers) ||
      !summary.rate_entry_freshness_counts ||
      summary.point_count !== history.points.length ||
      !this.validCount(summary.rate_entry_freshness_counts.live) ||
      !this.validCount(summary.rate_entry_freshness_counts.fallback) ||
      !this.validCount(summary.rate_entry_freshness_counts.cached) ||
      !this.validCount(summary.stale_entry_count) ||
      !this.validCount(summary.fallback_entry_count) ||
      summary.stale_entry_count > history.points.length * 2 ||
      summary.fallback_entry_count > history.points.length * 2 ||
      summary.rate_entry_freshness_counts.live +
        summary.rate_entry_freshness_counts.fallback +
        summary.rate_entry_freshness_counts.cached !==
        history.points.length * 2 ||
      summary.source_providers.some((provider) => !provider?.trim()) ||
      summary.target_providers.some((provider) => !provider?.trim())
    ) {
      return false;
    }
    if (history.empty) {
      return history.points.length === 0;
    }
    return (
      [
        analytics.minimum,
        analytics.maximum,
        analytics.average,
        analytics.absolute_change,
        analytics.percentage_change,
      ].every((value) => typeof value === 'string' && this.validDecimal(value)) &&
      ['GROWTH', 'DECLINE', 'UNCHANGED'].includes(analytics.trend ?? '')
    );
  }

  private validPoint(
    point: HistoryPoint,
    base: string,
    quote: string,
    analyticsPoint: { readonly date: string; readonly value: string } | undefined,
  ): boolean {
    return (
      this.validDate(point.date) &&
      this.validDecimal(point.value) &&
      analyticsPoint?.date === point.date &&
      analyticsPoint.value === point.value &&
      Boolean(point.rate_context.snapshot_id?.trim()) &&
      this.validLeg(point.rate_context.source_rate, base) &&
      this.validLeg(point.rate_context.target_rate, quote)
    );
  }

  private validLeg(leg: RateProvenance, code: string): boolean {
    return (
      leg.currency === code &&
      Boolean(leg.provider_name?.trim()) &&
      this.validTimestamp(leg.effective_at) &&
      ['live', 'fallback', 'cached'].includes(leg.freshness_state) &&
      typeof leg.is_fallback === 'boolean' &&
      typeof leg.is_stale === 'boolean'
    );
  }

  private validDecimal(value: string): boolean {
    return /^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value);
  }

  private validDate(value: string): boolean {
    return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`));
  }

  private validTimestamp(value: string): boolean {
    return typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Date.parse(value));
  }

  private validCount(value: number): boolean {
    return Number.isInteger(value) && value >= 0;
  }
}
