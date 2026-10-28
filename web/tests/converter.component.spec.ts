import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, Subject, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RatesApiService } from '../src/app/core/api/rates-api.service';
import {
  ConversionRequest,
  ConversionResponse,
  CurrenciesResponse,
  RateProvenance,
} from '../src/app/core/models/rate.models';
import { ConverterComponent } from '../src/app/features/converter/converter.component';

describe('ConverterComponent', () => {
  let fixture: ComponentFixture<ConverterComponent>;
  let api: {
    getCurrencies: ReturnType<typeof vi.fn<() => Observable<CurrenciesResponse>>>;
    convert: ReturnType<
      typeof vi.fn<(request: ConversionRequest) => Observable<ConversionResponse>>
    >;
  };

  const currencies: CurrenciesResponse = {
    currencies: [
      { code: 'EUR', name: 'Euro', type: 'fiat', is_supported: true },
      { code: 'USD', name: 'US Dollar', type: 'fiat', is_supported: true },
      { code: 'BTC', name: 'Bitcoin', type: 'crypto', is_supported: true },
      { code: 'XRP', name: 'Unsupported currency', type: 'crypto', is_supported: false },
    ],
  };

  const sourceRate: RateProvenance = {
    currency: 'EUR',
    provider_name: 'BNM',
    effective_at: '2026-10-27T09:00:00Z',
    freshness_state: 'fallback',
    is_fallback: true,
    is_stale: false,
  };

  const targetRate: RateProvenance = {
    currency: 'BTC',
    provider_name: 'CoinGecko',
    effective_at: '2026-10-28T11:45:00Z',
    freshness_state: 'cached',
    is_fallback: false,
    is_stale: true,
  };

  const conversionResult: ConversionResponse = {
    source_amount: '123.456789012345678901',
    converted_amount: '0.001700000000000000001',
    source_currency: 'EUR',
    target_currency: 'BTC',
    rate_value: '0.000013770000000000001',
    rate_context: {
      source_rate: sourceRate,
      target_rate: targetRate,
      snapshot_id: '00000000-0000-4000-8000-000000000033',
    },
  };

  beforeEach(async () => {
    api = {
      getCurrencies: vi.fn<() => Observable<CurrenciesResponse>>(),
      convert: vi.fn<(request: ConversionRequest) => Observable<ConversionResponse>>(),
    };

    await TestBed.configureTestingModule({
      declarations: [ConverterComponent],
      imports: [CommonModule],
      providers: [{ provide: RatesApiService, useValue: api }],
    }).compileComponents();
  });

  function createComponent(): ComponentFixture<ConverterComponent> {
    fixture = TestBed.createComponent(ConverterComponent);
    fixture.detectChanges();
    return fixture;
  }

  function renderReadyComponent(): ComponentFixture<ConverterComponent> {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(of(conversionResult));
    return createComponent();
  }

  function page(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function amountInput(): HTMLInputElement {
    return page().querySelector('#amount') as HTMLInputElement;
  }

  function sourceSelect(): HTMLSelectElement {
    return page().querySelector('#source-currency') as HTMLSelectElement;
  }

  function targetSelect(): HTMLSelectElement {
    return page().querySelector('#target-currency') as HTMLSelectElement;
  }

  function convertButton(): HTMLButtonElement {
    return page().querySelector('.converter-form button[type="submit"]') as HTMLButtonElement;
  }

  function setAmount(value: string): void {
    amountInput().value = value;
    amountInput().dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
  }

  function selectCurrency(select: HTMLSelectElement, code: string): void {
    select.value = code;
    select.dispatchEvent(new Event('change', { bubbles: true }));
    fixture.detectChanges();
  }

  function selectPair(source = 'EUR', target = 'BTC'): void {
    selectCurrency(sourceSelect(), source);
    selectCurrency(targetSelect(), target);
  }

  function submitForm(): void {
    page()
      .querySelector('form')
      ?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  function submitValidConversion(amount = '123.456789012345678901'): void {
    setAmount(amount);
    selectPair();
    convertButton().click();
    fixture.detectChanges();
  }

  function rateContext(label: 'Source rate context' | 'Target rate context'): HTMLElement {
    return page().querySelector(`.context-card[aria-label="${label}"]`) as HTMLElement;
  }

  it('loads currencies and keeps conversion unavailable until the request emits', () => {
    const response = new Subject<CurrenciesResponse>();
    api.getCurrencies.mockReturnValue(response);
    createComponent();

    expect(api.getCurrencies).toHaveBeenCalledTimes(1);
    expect(page().textContent).toContain('Loading supported currencies…');
    expect(page().querySelector('form')).toBeNull();
    expect(api.convert).not.toHaveBeenCalled();

    response.next(currencies);
    fixture.detectChanges();

    expect(sourceSelect()).toBeTruthy();
    expect(targetSelect()).toBeTruthy();
    expect(convertButton().disabled).toBe(true);
  });

  it('lists only supported currencies in both selectors and allows the same choice', () => {
    renderReadyComponent();

    for (const select of [sourceSelect(), targetSelect()]) {
      expect(Array.from(select.options).map((option) => option.value)).toEqual([
        '',
        'EUR',
        'USD',
        'BTC',
      ]);
    }

    setAmount('1');
    selectPair('EUR', 'EUR');
    expect(convertButton().disabled).toBe(false);
  });

  it.each([
    ['blank', ''],
    ['whitespace-only', '   '],
    ['zero', '0'],
    ['decimal zero', '0.000'],
    ['negative', '-1'],
    ['alphabetic', 'abc'],
    ['NaN', 'NaN'],
    ['Infinity', 'Infinity'],
  ])('rejects %s amounts without submitting a conversion', (_label, value) => {
    renderReadyComponent();
    selectPair();
    setAmount(value);

    expect(page().querySelector('.field-error')?.textContent?.trim()).toBeTruthy();
    expect(convertButton().disabled).toBe(true);
    submitForm();
    expect(api.convert).not.toHaveBeenCalled();
  });

  it('enables Convert only when amount, both currencies, and currency loading are valid', () => {
    renderReadyComponent();

    expect(convertButton().disabled).toBe(true);
    setAmount('10.25');
    expect(convertButton().disabled).toBe(true);

    selectCurrency(sourceSelect(), 'EUR');
    expect(convertButton().disabled).toBe(true);

    selectCurrency(targetSelect(), 'BTC');
    expect(convertButton().disabled).toBe(false);

    setAmount('0');
    expect(convertButton().disabled).toBe(true);

    setAmount('10.25');
    expect(convertButton().disabled).toBe(false);
  });

  it('preserves a high-precision amount exactly in the conversion request', () => {
    renderReadyComponent();
    submitValidConversion();

    expect(api.convert).toHaveBeenCalledTimes(1);
    expect(api.convert).toHaveBeenCalledWith({
      amount: '123.456789012345678901',
      source_currency: 'EUR',
      target_currency: 'BTC',
    });
  });

  it('shows converting state, blocks duplicate submissions, and renders the result when settled', () => {
    const response = new Subject<ConversionResponse>();
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(response);
    createComponent();
    setAmount('12.5');
    selectPair();

    convertButton().click();
    fixture.detectChanges();

    expect(page().textContent).toContain('Converting…');
    expect(convertButton().disabled).toBe(true);
    submitForm();
    expect(api.convert).toHaveBeenCalledTimes(1);

    response.next(conversionResult);
    fixture.detectChanges();

    expect(page().querySelector('.result-panel')).not.toBeNull();
    expect(page().querySelector('.message-panel[aria-busy="true"]')).toBeNull();
  });

  it('formats the exact conversion result and keeps source and target provenance separate', () => {
    renderReadyComponent();
    submitValidConversion();

    const result = page().querySelector('.result-panel') as HTMLElement;
    expect(result.textContent).toContain('123.456789012345678901');
    expect(result.textContent).toContain('EUR');
    expect(result.textContent).toContain('0.001700000000000000001');
    expect(result.textContent).toContain('BTC');
    expect(result.textContent).toContain('0.000013770000000000001');
    expect(result.textContent).toContain('00000000-0000-4000-8000-000000000033');
    expect(result.querySelectorAll('.context-card')).toHaveLength(2);
    expect(result.querySelector('.pair-rate')?.textContent).not.toContain('BNM');
    expect(result.querySelector('.pair-rate')?.textContent).not.toContain('CoinGecko');

    const source = rateContext('Source rate context');
    expect(source.textContent).toContain('EUR');
    expect(source.textContent).toContain('BNM');
    expect(source.textContent).toContain('2026-10-27T09:00:00Z');
    expect(source.textContent).toContain('Fallback');
    expect(source.textContent).toContain('Fallback used');
    expect(source.textContent).not.toContain('Stale');

    const target = rateContext('Target rate context');
    expect(target.textContent).toContain('BTC');
    expect(target.textContent).toContain('CoinGecko');
    expect(target.textContent).toContain('2026-10-28T11:45:00Z');
    expect(target.textContent).toContain('Cached');
    expect(target.textContent).toContain('Stale');
    expect(target.textContent).not.toContain('Fallback used');
  });

  it('renders freshness state independently from fallback and stale flags', () => {
    const independentResult: ConversionResponse = {
      ...conversionResult,
      rate_context: {
        ...conversionResult.rate_context,
        source_rate: {
          ...sourceRate,
          freshness_state: 'cached',
          is_fallback: false,
          is_stale: false,
        },
      },
    };
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(of(independentResult));
    createComponent();
    submitValidConversion();

    const source = rateContext('Source rate context');
    expect(source.textContent).toContain('Cached');
    expect(source.textContent).not.toContain('Fallback used');
    expect(source.textContent).not.toContain('Stale');
  });

  it('allows same-currency conversion and preserves the exact amount and both rate contexts', () => {
    const eurRate: RateProvenance = {
      currency: 'EUR',
      provider_name: 'BNM',
      effective_at: '2026-10-27T09:00:00Z',
      freshness_state: 'live',
      is_fallback: false,
      is_stale: false,
    };
    const sameCurrencyResult: ConversionResponse = {
      ...conversionResult,
      source_amount: '123.4500',
      converted_amount: '123.4500',
      source_currency: 'EUR',
      target_currency: 'EUR',
      rate_value: '1',
      rate_context: {
        ...conversionResult.rate_context,
        source_rate: eurRate,
        target_rate: eurRate,
      },
    };
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(of(sameCurrencyResult));
    createComponent();
    setAmount('123.4500');
    selectPair('EUR', 'EUR');

    expect(convertButton().disabled).toBe(false);
    convertButton().click();
    fixture.detectChanges();

    expect(api.convert).toHaveBeenCalledWith({
      amount: '123.4500',
      source_currency: 'EUR',
      target_currency: 'EUR',
    });
    const result = page().querySelector('.result-panel') as HTMLElement;
    expect(result.textContent).toContain('123.4500');
    expect(result.textContent).toContain('Pair rate: 1 EUR = 1 EUR');
    expect(rateContext('Source rate context').textContent).toContain('EUR');
    expect(rateContext('Target rate context').textContent).toContain('EUR');
    expect(rateContext('Source rate context').textContent).toContain('BNM');
    expect(rateContext('Target rate context').textContent).toContain('BNM');
  });

  it('shows a safe rate-unavailable error and removes any prior successful result', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValueOnce(of(conversionResult)).mockReturnValueOnce(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 422,
            error: {
              error: {
                code: 'rate_unavailable',
                message: 'No usable rate is available for BTC.',
              },
            },
          }),
      ),
    );
    createComponent();

    submitValidConversion();
    expect(page().querySelector('.result-panel')).not.toBeNull();

    setAmount('20');
    convertButton().click();
    fixture.detectChanges();

    expect(api.convert).toHaveBeenCalledTimes(2);
    expect(page().textContent).toContain('No usable rate is available for BTC.');
    expect(page().querySelector('.result-panel')).toBeNull();
    expect(page().textContent).not.toContain('HttpErrorResponse');
  });

  it('maps invalid_conversion_input to safe user-facing validation text', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 422,
            error: {
              error: {
                code: 'invalid_conversion_input',
                message: 'internal validation detail',
              },
            },
          }),
      ),
    );
    createComponent();
    submitValidConversion();

    expect(page().textContent).toContain('Enter a valid amount and select supported currencies.');
    expect(page().textContent).not.toContain('internal validation detail');
  });

  it('maps conversion_unavailable to a clear sanitized message', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 503,
            error: {
              error: {
                code: 'conversion_unavailable',
                message: 'internal snapshot detail',
              },
            },
          }),
      ),
    );
    createComponent();
    submitValidConversion();

    expect(page().textContent).toContain('Conversion is currently unavailable. Try again later.');
    expect(page().textContent).not.toContain('internal snapshot detail');
  });

  it('shows generic safe text for unexpected errors without exposing exception details', () => {
    api.getCurrencies.mockReturnValue(of(currencies));
    api.convert.mockReturnValue(throwError(() => new Error('private stack detail')));
    createComponent();
    submitValidConversion();

    expect(page().textContent).toContain('Conversion could not be completed. Please try again.');
    expect(page().textContent).not.toContain('private stack detail');
  });

  it('retries currency loading and keeps conversion unavailable until the retry succeeds', () => {
    api.getCurrencies
      .mockReturnValueOnce(throwError(() => new Error('private currency error')))
      .mockReturnValueOnce(of(currencies));
    api.convert.mockReturnValue(of(conversionResult));
    createComponent();

    expect(page().textContent).toContain('Currencies are unavailable.');
    expect(page().textContent).not.toContain('private currency error');
    expect(page().querySelector('form')).toBeNull();
    expect(api.convert).not.toHaveBeenCalled();

    const retryButton = Array.from(page().querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Retry',
    );
    expect(retryButton).toBeTruthy();
    retryButton?.click();
    fixture.detectChanges();

    expect(api.getCurrencies).toHaveBeenCalledTimes(2);
    expect(Array.from(sourceSelect().options).map((option) => option.value)).toContain('EUR');
    setAmount('1');
    selectPair();
    expect(convertButton().disabled).toBe(false);
  });

  it.each(['amount', 'source', 'target'])(
    'clears a successful result when the %s input changes',
    (changedInput) => {
      renderReadyComponent();
      submitValidConversion();
      expect(page().querySelector('.result-panel')).not.toBeNull();

      if (changedInput === 'amount') {
        setAmount('5');
      } else if (changedInput === 'source') {
        selectCurrency(sourceSelect(), 'USD');
      } else {
        selectCurrency(targetSelect(), 'USD');
      }

      expect(page().querySelector('.result-panel')).toBeNull();
    },
  );
});
