import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin } from 'rxjs';
import { RatesApiService } from '../../core/api/rates-api.service';
import { CurrenciesResponse, CurrencyModel, RateSnapshot } from '../../core/models/rate.models';
import { AllCurrenciesService, CalculatedCurrencyValue } from './all-currencies.service';

type ComparisonState =
  | { readonly status: 'loading' }
  | { readonly status: 'error' }
  | {
      readonly status: 'ready';
      readonly currencies: readonly CurrencyModel[];
      readonly snapshot: RateSnapshot;
    };

interface ComparisonRow extends CalculatedCurrencyValue {
  readonly name: string;
}

@Component({
  selector: 'app-all-currencies',
  standalone: false,
  styleUrl: './all-currencies.component.scss',
  templateUrl: './all-currencies.component.html',
})
export class AllCurrenciesComponent implements OnInit {
  protected readonly state = signal<ComparisonState>({ status: 'loading' });
  protected readonly amount = signal('1');
  protected readonly sourceCurrency = signal('');
  protected readonly amountError = computed(() => this.validateAmount(this.amount()));
  protected readonly rows = computed<readonly ComparisonRow[]>(() => {
    const viewState = this.state();
    if (viewState.status !== 'ready' || this.amountError()) {
      return [];
    }

    try {
      return this.calculator
        .calculate(this.amount(), this.sourceCurrency(), viewState.snapshot.rates)
        .map((value) => ({
          ...value,
          name:
            viewState.currencies.find((currency) => currency.code === value.currency.currency)
              ?.name ?? value.currency.currency,
        }));
    } catch {
      return [];
    }
  });

  private readonly api = inject(RatesApiService);
  private readonly calculator = inject(AllCurrenciesService);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.loadSnapshot();
  }

  protected loadSnapshot(): void {
    this.state.set({ status: 'loading' });
    forkJoin({ currencies: this.api.getCurrencies(), snapshot: this.api.getLatestRates() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ currencies, snapshot }) => this.setReadyState(currencies, snapshot),
        error: () => this.state.set({ status: 'error' }),
      });
  }

  protected setAmount(event: Event): void {
    const input = event.target;
    if (input instanceof HTMLInputElement) {
      this.amount.set(input.value);
    }
  }

  protected setSourceCurrency(event: Event): void {
    const select = event.target;
    if (select instanceof HTMLSelectElement) {
      this.sourceCurrency.set(select.value);
    }
  }

  private setReadyState(currenciesResponse: CurrenciesResponse, snapshot: RateSnapshot): void {
    try {
      const currencies = currenciesResponse.currencies.filter((currency) => currency.is_supported);
      const supportedCodes = new Set(currencies.map((currency) => currency.code));
      const rateCodes = new Set(snapshot.rates.map((rate) => rate.currency));
      if (
        currencies.length === 0 ||
        supportedCodes.size !== currencies.length ||
        !snapshot.snapshot_id?.trim() ||
        !this.validTimestamp(snapshot.captured_at) ||
        rateCodes.size !== snapshot.rates.length ||
        rateCodes.size !== supportedCodes.size ||
        currencies.some((currency) => !currency.name?.trim() || !rateCodes.has(currency.code)) ||
        snapshot.rates.some(
          (rate) =>
            !supportedCodes.has(rate.currency) ||
            !rate.provider_name?.trim() ||
            !this.validTimestamp(rate.effective_at) ||
            !['live', 'fallback', 'cached'].includes(rate.freshness_state) ||
            typeof rate.is_fallback !== 'boolean' ||
            typeof rate.is_stale !== 'boolean' ||
            typeof rate.normalized_rate_to_mdl !== 'string' ||
            rate.provider_type !==
              currencies.find((currency) => currency.code === rate.currency)?.type,
        )
      ) {
        throw new Error('Incomplete or invalid snapshot.');
      }
      this.calculator.calculate('1', snapshot.rates[0].currency, snapshot.rates);
      this.sourceCurrency.set(snapshot.rates[0].currency);
      this.state.set({ status: 'ready', currencies, snapshot });
    } catch {
      this.state.set({ status: 'error' });
    }
  }

  private validTimestamp(value: string): boolean {
    return typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Date.parse(value));
  }

  private validateAmount(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) {
      return 'Enter a positive decimal amount.';
    }
    if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(trimmed)) {
      return 'Enter a valid positive decimal amount.';
    }
    if (!/[1-9]/.test(trimmed)) {
      return 'Amount must be greater than zero.';
    }
    return null;
  }
}
