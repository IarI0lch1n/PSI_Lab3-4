import '@angular/compiler';
import { CommonModule } from '@angular/common';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, Subject, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RatesApiService } from '../src/app/core/api/rates-api.service';
import {
  AnalyticsPeriod,
  AnalyticsResponse,
  CurrenciesResponse,
  HistoryResponse,
  RateProvenance,
} from '../src/app/core/models/rate.models';
import { AnalyticsComponent } from '../src/app/features/analytics/analytics.component';

describe('AnalyticsComponent', () => {
  let fixture: ComponentFixture<AnalyticsComponent>;
  let api: {
    getCurrencies: ReturnType<typeof vi.fn<() => Observable<CurrenciesResponse>>>;
    getHistory: ReturnType<
      typeof vi.fn<
        (base: string, quote: string, period: AnalyticsPeriod) => Observable<HistoryResponse>
      >
    >;
    getAnalytics: ReturnType<
      typeof vi.fn<
        (base: string, quote: string, period: AnalyticsPeriod) => Observable<AnalyticsResponse>
      >
    >;
  };

  const currencies: CurrenciesResponse = {
    currencies: [
      { code: 'EUR', name: 'Euro', type: 'fiat', is_supported: true },
      { code: 'USD', name: 'US Dollar', type: 'fiat', is_supported: true },
      { code: 'BTC', name: 'Bitcoin', type: 'crypto', is_supported: true },
      { code: 'XXX', name: 'Unsupported', type: 'fiat', is_supported: false },
    ],
  };

  beforeEach(async () => {
    api = {
      getCurrencies: vi.fn<() => Observable<CurrenciesResponse>>(),
      getHistory:
        vi.fn<
          (base: string, quote: string, period: AnalyticsPeriod) => Observable<HistoryResponse>
        >(),
      getAnalytics:
        vi.fn<
          (base: string, quote: string, period: AnalyticsPeriod) => Observable<AnalyticsResponse>
        >(),
    };
    await TestBed.configureTestingModule({
      declarations: [AnalyticsComponent],
      imports: [CommonModule],
      providers: [{ provide: RatesApiService, useValue: api }],
    }).compileComponents();
  });

  function configureSuccess(): void {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getHistory.mockImplementation((base, quote, period) => of(history(period, base, quote)));
    api.getAnalytics.mockImplementation((base, quote, period) =>
      of(analytics(period, base, quote)),
    );
  }

  function render(): void {
    fixture = TestBed.createComponent(AnalyticsComponent);
    fixture.detectChanges();
  }

  function page(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function text(): string {
    return page().textContent ?? '';
  }

  it('shows loading until currencies and both analytics responses arrive', () => {
    const currenciesResponse = new Subject<CurrenciesResponse>();
    const historyResponse = new Subject<HistoryResponse>();
    const analyticsResponse = new Subject<AnalyticsResponse>();
    api.getCurrencies.mockReturnValue(currenciesResponse);
    api.getHistory.mockReturnValue(historyResponse);
    api.getAnalytics.mockReturnValue(analyticsResponse);
    render();

    expect(text()).toContain('Loading historical analytics');
    expect(api.getHistory).not.toHaveBeenCalled();

    currenciesResponse.next(currencies);
    fixture.detectChanges();
    expect(api.getHistory).toHaveBeenCalledWith('EUR', 'BTC', '7d');
    expect(text()).toContain('Loading historical analytics');

    historyResponse.next(history());
    historyResponse.complete();
    analyticsResponse.next(analytics());
    analyticsResponse.complete();
    fixture.detectChanges();
    expect(page().querySelectorAll('.point-card')).toHaveLength(2);
  });

  it('renders exact metrics, mixed providers, and aggregate freshness counts', () => {
    configureSuccess();
    render();

    expect(text()).toContain('0.0000318');
    expect(text()).toContain('0.0000330');
    expect(text()).toContain('0.0000324');
    expect(text()).toContain('1.26%');
    expect(text()).toContain('Growth');
    const summary = page().querySelector('.provenance-summary') as HTMLElement;
    expect(summary.textContent).toContain('BNM, Backup BNM');
    expect(summary.textContent).toContain('CoinGecko');
    expect(summary.textContent).toContain('Live entries2');
    expect(summary.textContent).toContain('Fallback entries1');
    expect(summary.textContent).toContain('Cached entries1');
    expect(summary.textContent).toContain('Stale entries1');
    expect(summary.textContent).toContain('Fallback used1');
  });

  it('shows independent live, fallback, cached, and stale state per leg', () => {
    configureSuccess();
    render();

    const cards = Array.from(page().querySelectorAll('.point-card')) as HTMLElement[];
    const firstLegs = Array.from(cards[0].querySelectorAll('.leg-grid section')) as HTMLElement[];
    expect(firstLegs[0].textContent).toContain('BNM');
    expect(firstLegs[0].textContent).toContain('Live');
    expect(firstLegs[0].textContent).not.toContain('Fallback used');
    expect(firstLegs[0].textContent).not.toContain('Stale');
    expect(firstLegs[1].textContent).toContain('CoinGecko');
    expect(firstLegs[1].textContent).toContain('Cached');
    expect(firstLegs[1].textContent).toContain('Stale');
    expect(firstLegs[1].textContent).not.toContain('Fallback used');

    const secondSource = cards[1].querySelector('.leg-grid section') as HTMLElement;
    expect(secondSource.textContent).toContain('Backup BNM');
    expect(secondSource.textContent).toContain('Fallback');
    expect(secondSource.textContent).toContain('Fallback used');
    expect(secondSource.textContent).not.toContain('Stale');
  });

  it('requests and renders the selected 30-day period', () => {
    configureSuccess();
    render();
    const button = Array.from(page().querySelectorAll('button')).find((candidate) =>
      candidate.textContent?.includes('30 days'),
    );
    button?.click();
    fixture.detectChanges();

    expect(api.getHistory).toHaveBeenLastCalledWith('EUR', 'BTC', '30d');
    expect(api.getAnalytics).toHaveBeenLastCalledWith('EUR', 'BTC', '30d');
    expect(button?.classList.contains('active')).toBe(true);
    expect(page().querySelectorAll('.point-card')).toHaveLength(2);
  });

  it('requests a new pair when a currency selection changes', () => {
    configureSuccess();
    render();
    const baseSelect = page().querySelectorAll('select')[0] as HTMLSelectElement;
    expect(Array.from(baseSelect.options).map(({ value }) => value)).toEqual(['EUR', 'USD', 'BTC']);
    baseSelect.value = 'USD';
    baseSelect.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(api.getHistory).toHaveBeenLastCalledWith('USD', 'BTC', '7d');
    expect(text()).toContain('Base: USD');
  });

  it('shows the explicit empty state without misleading metrics or points', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getHistory.mockImplementation((base, quote, period) =>
      of({
        base_currency: base,
        quote_currency: quote,
        period,
        points: [],
        empty: true,
        message: 'No historical data available for this pair in the selected period.',
      }),
    );
    api.getAnalytics.mockImplementation((base, quote, period) =>
      of(emptyAnalytics(period, base, quote)),
    );
    render();

    expect(text()).toContain('No historical data');
    expect(text()).toContain('No historical data available for this pair');
    expect(page().querySelector('.metrics')).toBeNull();
    expect(page().querySelector('.point-card')).toBeNull();
  });

  it('shows a safe error and retries history and analytics together', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getHistory
      .mockReturnValueOnce(throwError(() => new Error('private history detail')))
      .mockImplementation((base, quote, period) => of(history(period, base, quote)));
    api.getAnalytics.mockImplementation((base, quote, period) =>
      of(analytics(period, base, quote)),
    );
    render();

    expect(text()).toContain('Analytics are unavailable');
    expect(text()).not.toContain('private history detail');
    const retry = Array.from(page().querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Retry',
    );
    retry?.click();
    fixture.detectChanges();

    expect(api.getHistory).toHaveBeenCalledTimes(2);
    expect(api.getAnalytics).toHaveBeenCalledTimes(2);
    expect(page().querySelectorAll('.point-card')).toHaveLength(2);
  });

  it.each([
    (response: AnalyticsResponse) => ({ ...response, base_currency: 'USD' }),
    (response: AnalyticsResponse) => ({ ...response, points: response.points.slice(1) }),
    (response: AnalyticsResponse) => ({
      ...response,
      provenance_summary: {
        ...response.provenance_summary,
        rate_entry_freshness_counts: { live: 99, fallback: 1, cached: 1 },
      },
    }),
  ])('rejects mismatched or misleading analytics responses', (mutate) => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getHistory.mockReturnValue(of(history()));
    api.getAnalytics.mockReturnValue(of(mutate(analytics())));
    render();

    expect(text()).toContain('Analytics are unavailable');
    expect(page().querySelector('.point-card')).toBeNull();
  });

  it('ignores an older response after a newer period request completes', () => {
    const oldHistory = new Subject<HistoryResponse>();
    const oldAnalytics = new Subject<AnalyticsResponse>();
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getHistory
      .mockReturnValueOnce(oldHistory)
      .mockImplementation((base, quote, period) => of(history(period, base, quote)));
    api.getAnalytics
      .mockReturnValueOnce(oldAnalytics)
      .mockImplementation((base, quote, period) => of(analytics(period, base, quote)));
    render();

    const thirtyDays = Array.from(page().querySelectorAll('button')).find((candidate) =>
      candidate.textContent?.includes('30 days'),
    );
    thirtyDays?.click();
    fixture.detectChanges();
    expect(thirtyDays?.classList.contains('active')).toBe(true);

    oldHistory.next(history('7d'));
    oldAnalytics.next(analytics('7d'));
    fixture.detectChanges();

    expect(thirtyDays?.classList.contains('active')).toBe(true);
    expect(api.getHistory).toHaveBeenLastCalledWith('EUR', 'BTC', '30d');
    expect(page().querySelectorAll('.point-card')).toHaveLength(2);
  });
});

const liveEur: RateProvenance = {
  currency: 'EUR',
  provider_name: 'BNM',
  effective_at: '2026-10-26T09:00:00Z',
  freshness_state: 'live',
  is_fallback: false,
  is_stale: false,
};

const cachedBtc: RateProvenance = {
  currency: 'BTC',
  provider_name: 'CoinGecko',
  effective_at: '2026-10-27T11:45:00Z',
  freshness_state: 'cached',
  is_fallback: false,
  is_stale: true,
};

function history(period: AnalyticsPeriod = '7d', base = 'EUR', quote = 'BTC'): HistoryResponse {
  const firstSource = { ...liveEur, currency: base };
  const firstTarget = { ...cachedBtc, currency: quote };
  return {
    base_currency: base,
    quote_currency: quote,
    period,
    empty: false,
    points: [
      {
        date: '2026-10-27',
        value: '0.0000318',
        rate_context: {
          source_rate: firstSource,
          target_rate: firstTarget,
          snapshot_id: 'snapshot-27',
        },
      },
      {
        date: '2026-10-28',
        value: '0.0000330',
        rate_context: {
          source_rate: {
            ...firstSource,
            provider_name: 'Backup BNM',
            effective_at: '2026-10-25T09:00:00Z',
            freshness_state: 'fallback',
            is_fallback: true,
          },
          target_rate: {
            ...firstTarget,
            effective_at: '2026-10-28T11:45:00Z',
            freshness_state: 'live',
            is_stale: false,
          },
          snapshot_id: 'snapshot-28',
        },
      },
    ],
  };
}

function analytics(period: AnalyticsPeriod = '7d', base = 'EUR', quote = 'BTC'): AnalyticsResponse {
  return {
    base_currency: base,
    quote_currency: quote,
    period,
    points: history(period, base, quote).points.map(({ date, value }) => ({ date, value })),
    minimum: '0.0000318',
    maximum: '0.0000330',
    average: '0.0000324',
    absolute_change: '0.0000012',
    percentage_change: '1.26',
    trend: 'GROWTH',
    provenance_summary: {
      point_count: 2,
      source_providers: ['BNM', 'Backup BNM'],
      target_providers: ['CoinGecko'],
      rate_entry_freshness_counts: { live: 2, fallback: 1, cached: 1 },
      stale_entry_count: 1,
      fallback_entry_count: 1,
    },
    empty: false,
  };
}

function emptyAnalytics(period: AnalyticsPeriod, base: string, quote: string): AnalyticsResponse {
  return {
    base_currency: base,
    quote_currency: quote,
    period,
    points: [],
    provenance_summary: {
      point_count: 0,
      source_providers: [],
      target_providers: [],
      rate_entry_freshness_counts: { live: 0, fallback: 0, cached: 0 },
      stale_entry_count: 0,
      fallback_entry_count: 0,
    },
    empty: true,
    message: 'No historical data available for this pair in the selected period.',
  };
}
