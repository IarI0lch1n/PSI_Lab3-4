import { CommonModule } from '@angular/common';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, Subject, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RatesApiService } from '../src/app/core/api/rates-api.service';
import { CurrenciesResponse, RateSnapshot } from '../src/app/core/models/rate.models';
import { CurrentRatesComponent } from '../src/app/features/rates/current-rates.component';

describe('CurrentRatesComponent', () => {
  let fixture: ComponentFixture<CurrentRatesComponent>;
  let api: {
    getCurrencies: ReturnType<typeof vi.fn<() => Observable<CurrenciesResponse>>>;
    getLatestRates: ReturnType<typeof vi.fn<() => Observable<RateSnapshot>>>;
  };

  const currencies: CurrenciesResponse = {
    currencies: [
      {
        code: 'USD',
        name: 'US Dollar',
        type: 'fiat',
        is_supported: true,
      },
      {
        code: 'RON',
        name: 'Romanian Leu',
        type: 'fiat',
        is_supported: true,
      },
      {
        code: 'BTC',
        name: 'Bitcoin',
        type: 'crypto',
        is_supported: true,
      },
    ],
  };

  const snapshot: RateSnapshot = {
    snapshot_id: 'snapshot-2026-10-28',
    captured_at: '2026-10-28T12:00:00Z',
    rates: [
      {
        currency: 'USD',
        normalized_rate_to_mdl: '17.400000000000000001',
        nominal_unit: 1,
        provider_name: 'BNM',
        provider_type: 'fiat',
        effective_at: '2026-10-28T09:00:00Z',
        freshness_state: 'live',
        is_fallback: false,
        is_stale: false,
      },
      {
        currency: 'RON',
        normalized_rate_to_mdl: '3.912345678901234567',
        nominal_unit: 100,
        provider_name: 'BNM',
        provider_type: 'fiat',
        effective_at: '2026-10-27T00:00:00+02:00',
        freshness_state: 'fallback',
        is_fallback: true,
        is_stale: false,
      },
      {
        currency: 'BTC',
        normalized_rate_to_mdl: '542240.10',
        nominal_unit: 1,
        provider_name: 'CoinGecko',
        provider_type: 'crypto',
        effective_at: '2026-10-28T11:45:00Z',
        freshness_state: 'cached',
        is_fallback: false,
        is_stale: true,
      },
    ],
  };

  beforeEach(async () => {
    api = {
      getCurrencies: vi.fn<() => Observable<CurrenciesResponse>>(),
      getLatestRates: vi.fn<() => Observable<RateSnapshot>>(),
    };

    await TestBed.configureTestingModule({
      declarations: [CurrentRatesComponent],
      imports: [CommonModule],
      providers: [{ provide: RatesApiService, useValue: api }],
    }).compileComponents();
  });

  function createComponent(): ComponentFixture<CurrentRatesComponent> {
    fixture = TestBed.createComponent(CurrentRatesComponent);
    fixture.detectChanges();
    return fixture;
  }

  function renderSuccessfulResponse(): ComponentFixture<CurrentRatesComponent> {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getLatestRates.mockReturnValue(of(snapshot));
    return createComponent();
  }

  function rateCards(): HTMLElement[] {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('.rate-card'));
  }

  it('shows loading while both API observables have not emitted', () => {
    api.getCurrencies.mockReturnValue(new Subject<CurrenciesResponse>());
    api.getLatestRates.mockReturnValue(new Subject<RateSnapshot>());
    createComponent();

    expect(fixture.nativeElement.textContent).toContain('Loading current rates…');
    expect(fixture.nativeElement.querySelector('.rate-card')).toBeNull();
  });

  it('renders currency identity, exact rate strings, provider, time, and freshness', () => {
    renderSuccessfulResponse();

    const cards = rateCards();
    expect(cards).toHaveLength(3);

    expect(cards[0].textContent).toContain('USD');
    expect(cards[0].textContent).toContain('US Dollar');
    expect(cards[0].textContent).toContain('17.400000000000000001');
    expect(cards[0].textContent).toContain('BNM');
    expect(cards[0].textContent).toContain('2026-10-28T09:00:00Z');
    expect(cards[0].textContent).toContain('Live');

    expect(cards[1].textContent).toContain('RON');
    expect(cards[1].textContent).toContain('Romanian Leu');
    expect(cards[1].textContent).toContain('3.912345678901234567');
    expect(cards[1].textContent).toContain('BNM');
    expect(cards[1].textContent).toContain('2026-10-27T00:00:00+02:00');
    expect(cards[1].textContent).toContain('Fallback');

    expect(cards[2].textContent).toContain('BTC');
    expect(cards[2].textContent).toContain('Bitcoin');
    expect(cards[2].textContent).toContain('542240.10');
    expect(cards[2].textContent).toContain('CoinGecko');
    expect(cards[2].textContent).toContain('2026-10-28T11:45:00Z');
    expect(cards[2].textContent).toContain('Cached');
  });

  it('shows the collection time once and each original effective time on its own row', () => {
    renderSuccessfulResponse();

    const pageText = fixture.nativeElement.textContent as string;
    const snapshotTimes = fixture.nativeElement.querySelectorAll('.snapshot-summary time');

    expect(snapshotTimes).toHaveLength(1);
    expect(snapshotTimes[0].textContent).toContain('2026-10-28T12:00:00Z');
    expect(rateCards()).toHaveLength(snapshot.rates.length);
    snapshot.rates.forEach((rate, index) => {
      expect(rateCards()[index].textContent).toContain(rate.effective_at);
      expect(rateCards()[index].textContent).not.toContain(snapshot.captured_at);
    });
    expect(pageText.match(/2026-10-28T12:00:00Z/g)).toHaveLength(1);
  });

  it('renders the primary freshness state and independent fallback/stale flags', () => {
    renderSuccessfulResponse();

    const [live, fallback, cachedStale] = rateCards();

    expect(live.textContent).toContain('Live');
    expect(live.textContent).not.toContain('Fallback used');
    expect(live.textContent).not.toContain('Stale');

    expect(fallback.textContent).toContain('Fallback');
    expect(fallback.textContent).toContain('Fallback used');
    expect(fallback.textContent).not.toContain('Stale');

    expect(cachedStale.textContent).toContain('Cached');
    expect(cachedStale.textContent).toContain('Stale');
    expect(cachedStale.textContent).not.toContain('Fallback used');
  });

  it('does not infer fallback-used or stale flags from the cached primary state', () => {
    const cachedWithoutFlags: RateSnapshot = {
      ...snapshot,
      rates: [
        {
          ...snapshot.rates[2],
          is_fallback: false,
          is_stale: false,
        },
      ],
    };
    api.getCurrencies.mockReturnValue(of(currencies));
    api.getLatestRates.mockReturnValue(of(cachedWithoutFlags));
    createComponent();

    const card = rateCards()[0];
    expect(card.textContent).toContain('Cached');
    expect(card.textContent).not.toContain('Fallback used');
    expect(card.textContent).not.toContain('Stale');
  });

  it('shows the unavailable error and retries both GET requests', () => {
    api.getCurrencies.mockReturnValue(throwError(() => new Error('Currencies unavailable')));
    api.getLatestRates.mockReturnValue(of(snapshot));
    createComponent();

    expect(fixture.nativeElement.textContent).toContain('Current rates are unavailable.');
    const retryButton = (fixture.nativeElement as HTMLElement).querySelector(
      '.retry-button',
    ) as HTMLButtonElement | null;
    expect(retryButton).not.toBeNull();

    retryButton?.click();
    fixture.detectChanges();

    expect(api.getCurrencies).toHaveBeenCalledTimes(2);
    expect(api.getLatestRates).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.textContent).toContain('Current rates are unavailable.');
  });

  it('shows the error state rather than rendering partial data for missing currency metadata', () => {
    const incompleteCurrencies: CurrenciesResponse = {
      currencies: currencies.currencies.filter((currency) => currency.code !== 'BTC'),
    };
    api.getCurrencies.mockReturnValue(of(incompleteCurrencies));
    api.getLatestRates.mockReturnValue(of(snapshot));
    createComponent();

    expect(fixture.nativeElement.textContent).toContain('Current rates are unavailable.');
    expect(fixture.nativeElement.querySelector('.rate-card')).toBeNull();
  });
});
