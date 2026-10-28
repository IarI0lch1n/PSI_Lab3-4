import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  CurrenciesResponse,
  ConversionRequest,
  ConversionResponse,
  CurrencyModel,
  FreshnessState,
} from '../../core/models/rate.models';
import { RatesApiService } from '../../core/api/rates-api.service';

type CurrencyLoadState = 'loading' | 'ready' | 'error';

type ConversionState =
  | { readonly status: 'idle' }
  | { readonly status: 'converting' }
  | { readonly status: 'success'; readonly result: ConversionResponse }
  | { readonly status: 'error'; readonly message: string };

@Component({
  selector: 'app-converter',
  standalone: false,
  styleUrl: './converter.component.scss',
  templateUrl: './converter.component.html',
})
export class ConverterComponent implements OnInit {
  protected readonly currencyState = signal<CurrencyLoadState>('loading');
  protected readonly currencies = signal<readonly CurrencyModel[]>([]);
  protected readonly amount = signal('');
  protected readonly sourceCurrency = signal('');
  protected readonly targetCurrency = signal('');
  protected readonly conversionState = signal<ConversionState>({ status: 'idle' });
  protected readonly amountError = computed(() => validateAmount(this.amount()));
  protected readonly canConvert = computed(
    () =>
      this.currencyState() === 'ready' &&
      this.amountError() === null &&
      this.isSelectableCurrency(this.sourceCurrency()) &&
      this.isSelectableCurrency(this.targetCurrency()) &&
      this.conversionState().status !== 'converting',
  );

  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.loadCurrencies();
  }

  protected loadCurrencies(): void {
    this.currencyState.set('loading');
    this.currencies.set([]);
    this.sourceCurrency.set('');
    this.targetCurrency.set('');
    this.conversionState.set({ status: 'idle' });

    this.api
      .getCurrencies()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: CurrenciesResponse) => {
          const supported = response.currencies.filter((currency) => currency.is_supported);
          this.currencies.set(supported);
          this.currencyState.set('ready');
        },
        error: () => this.currencyState.set('error'),
      });
  }

  protected setAmount(event: Event): void {
    const input = event.target;
    if (input instanceof HTMLInputElement) {
      this.amount.set(input.value);
      this.clearPreviousResult();
    }
  }

  protected setSourceCurrency(event: Event): void {
    const select = event.target;
    if (select instanceof HTMLSelectElement) {
      this.sourceCurrency.set(select.value);
      this.clearPreviousResult();
    }
  }

  protected setTargetCurrency(event: Event): void {
    const select = event.target;
    if (select instanceof HTMLSelectElement) {
      this.targetCurrency.set(select.value);
      this.clearPreviousResult();
    }
  }

  protected convert(event: SubmitEvent): void {
    event.preventDefault();
    if (!this.canConvert()) {
      return;
    }

    const request: ConversionRequest = {
      amount: this.amount().trim(),
      source_currency: this.sourceCurrency(),
      target_currency: this.targetCurrency(),
    };
    this.conversionState.set({ status: 'converting' });

    this.api
      .convert(request)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => this.conversionState.set({ status: 'success', result }),
        error: (error: unknown) =>
          this.conversionState.set({
            status: 'error',
            message: conversionErrorMessage(error),
          }),
      });
  }

  protected freshnessLabel(state: FreshnessState): string {
    switch (state) {
      case 'live':
        return 'Live';
      case 'fallback':
        return 'Fallback';
      case 'cached':
        return 'Cached';
    }
  }

  protected currencyLabel(currency: CurrencyModel): string {
    return `${currency.code} — ${currency.name}`;
  }

  private isSelectableCurrency(code: string): boolean {
    return this.currencies().some((currency) => currency.code === code);
  }

  private clearPreviousResult(): void {
    if (this.conversionState().status !== 'converting') {
      this.conversionState.set({ status: 'idle' });
    }
  }
}

function validateAmount(value: string): string | null {
  const amount = value.trim();
  if (!amount) {
    return 'Enter an amount.';
  }

  if (amount.startsWith('-')) {
    return 'Amount must be greater than zero.';
  }

  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(amount)) {
    return 'Enter a valid positive number.';
  }

  if (!/[1-9]/.test(amount.replace('.', ''))) {
    return 'Amount must be greater than zero.';
  }

  return null;
}

function conversionErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    const envelope = error.error;
    if (isErrorEnvelope(envelope)) {
      if (envelope.error.code === 'rate_unavailable') {
        return envelope.error.message;
      }
      if (envelope.error.code === 'invalid_conversion_input') {
        return 'Enter a valid amount and select supported currencies.';
      }
      if (envelope.error.code === 'conversion_unavailable') {
        return 'Conversion is currently unavailable. Try again later.';
      }
    }
  }

  return 'Conversion could not be completed. Please try again.';
}

function isErrorEnvelope(
  value: unknown,
): value is { readonly error: { readonly code: string; readonly message: string } } {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false;
  }

  const envelope = value.error;
  return (
    typeof envelope === 'object' &&
    envelope !== null &&
    'code' in envelope &&
    typeof envelope.code === 'string' &&
    'message' in envelope &&
    typeof envelope.message === 'string'
  );
}
