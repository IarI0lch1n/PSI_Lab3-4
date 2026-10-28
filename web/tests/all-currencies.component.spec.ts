import '@angular/compiler';
import { CommonModule } from '@angular/common';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import { RatesApiService } from '../src/app/core/api/rates-api.service';
import { AllCurrenciesComponent } from '../src/app/features/rates/all-currencies.component';
import { CurrenciesResponse, RateSnapshot } from '../src/app/core/models/rate.models';

describe('AllCurrenciesComponent', () => {
  let fixture: ComponentFixture<AllCurrenciesComponent>;
  let api: {
    getCurrencies: ReturnType<typeof vi.fn>;
    getLatestRates: ReturnType<typeof vi.fn>;
  };

  const currencies: CurrenciesResponse = {
    currencies: [
      { code: 'EUR', name: 'Euro', type: 'fiat', is_supported: true },
      { code: 'USD', name: 'US Dollar', type: 'fiat', is_supported: true },
      { code: 'BTC', name: 'Bitcoin', type: 'crypto', is_supported: true },
    ],
  };

  const snapshot: RateSnapshot = {
    snapshot_id: 'snapshot-1',
    captured_at: '2026-10-28T12:00:00Z',
    rates: [
      rate('EUR', '19.1234567890123456789', 'BNM', 'live', false, false),
      rate('USD', '17.400000000000000001', 'BNM', 'fallback', true, false),
      rate('BTC', '542240.10', 'CoinGecko', 'cached', false, true),
    ],
  };

  beforeEach(async () => {
    api = {
      getCurrencies: vi.fn(() => of(currencies)),
      getLatestRates: vi.fn(() => of(snapshot)),
    };
    await TestBed.configureTestingModule({
      declarations: [AllCurrenciesComponent],
      imports: [CommonModule],
      providers: [{ provide: RatesApiService, useValue: api }],
    }).compileComponents();
  });

  function render(): void {
    fixture = TestBed.createComponent(AllCurrenciesComponent);
    fixture.detectChanges();
  }

  it('recalculates every currency when the source amount changes', () => {
    render();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    input.value = '2';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(text()).toContain('2');
    expect(text()).toContain(
      '2.1980984814956719169886150297990993151155968373678678554531266185420765600314295',
    );
    expect(text()).toContain(
      '0.000070535014983260535983598409634403652551701727703281258615878833011427963368994658',
    );
  });

  it('switches the source currency while keeping one snapshot timestamp', () => {
    render();
    const select = fixture.nativeElement.querySelector('select') as HTMLSelectElement;
    select.value = 'USD';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(text()).toContain('1');
    expect(text()).toContain('Snapshot collected');
    expect(text()).toContain('2026-10-28T12:00:00Z');
    expect(api.getLatestRates).toHaveBeenCalledTimes(1);
  });

  it('shows independent provider, effective time, and freshness metadata', () => {
    render();

    expect(text()).toContain('Provider');
    expect(text()).toContain('BNM');
    expect(text()).toContain('CoinGecko');
    expect(text()).toContain('2026-10-28T09:00:00Z');
    expect(text()).toContain('2026-10-28T11:45:00Z');
    expect(text()).toContain('Live');
    expect(text()).toContain('Fallback');
    expect(text()).toContain('Fallback used');
    expect(text()).toContain('Cached');
    expect(text()).toContain('Stale');
  });

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }
});

function rate(
  currency: string,
  normalizedRate: string,
  provider: string,
  freshnessState: 'live' | 'fallback' | 'cached',
  isFallback: boolean,
  isStale: boolean,
) {
  return {
    currency,
    normalized_rate_to_mdl: normalizedRate,
    nominal_unit: 1,
    provider_name: provider,
    provider_type: provider === 'CoinGecko' ? ('crypto' as const) : ('fiat' as const),
    effective_at: provider === 'CoinGecko' ? '2026-10-28T11:45:00Z' : '2026-10-28T09:00:00Z',
    freshness_state: freshnessState,
    is_fallback: isFallback,
    is_stale: isStale,
  };
}
