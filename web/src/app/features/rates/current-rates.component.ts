import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin, map } from 'rxjs';
import { RatesApiService } from '../../core/api/rates-api.service';
import {
  CurrenciesResponse,
  CurrencyType,
  FreshnessState,
  RateSnapshot,
} from '../../core/models/rate.models';

interface CurrentRateRow {
  readonly code: string;
  readonly name: string;
  readonly type: CurrencyType;
  readonly normalizedRateToMdl: string;
  readonly nominalUnit: number;
  readonly providerName: string;
  readonly providerType: CurrencyType;
  readonly effectiveAt: string;
  readonly freshnessState: FreshnessState;
  readonly isFallback: boolean;
  readonly isStale: boolean;
}

type CurrentRatesState =
  | { readonly status: 'loading' }
  | { readonly status: 'error' }
  | {
      readonly status: 'loaded';
      readonly snapshot: RateSnapshot;
      readonly rows: readonly CurrentRateRow[];
    };

@Component({
  selector: 'app-current-rates',
  standalone: false,
  styleUrl: './current-rates.component.scss',
  templateUrl: './current-rates.component.html',
})
export class CurrentRatesComponent implements OnInit {
  protected readonly state = signal<CurrentRatesState>({ status: 'loading' });

  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.loadRates();
  }

  protected loadRates(): void {
    this.state.set({ status: 'loading' });

    forkJoin({
      currencies: this.api.getCurrencies(),
      snapshot: this.api.getLatestRates(),
    })
      .pipe(
        map(({ currencies, snapshot }) => this.createLoadedState(currencies, snapshot)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (loadedState) => this.state.set(loadedState),
        error: () => this.state.set({ status: 'error' }),
      });
  }

  private createLoadedState(
    currenciesResponse: CurrenciesResponse,
    snapshot: RateSnapshot,
  ): CurrentRatesState {
    if (snapshot.rates.length === 0) {
      throw new Error('The latest rate snapshot contains no rate entries.');
    }

    const currenciesByCode = new Map(
      currenciesResponse.currencies
        .filter((currency) => currency.is_supported)
        .map((currency) => [currency.code, currency]),
    );

    const rows = snapshot.rates.map((rate): CurrentRateRow => {
      const currency = currenciesByCode.get(rate.currency);

      if (!currency) {
        throw new Error(`Missing supported currency metadata for ${rate.currency}.`);
      }

      return {
        code: currency.code,
        name: currency.name,
        type: currency.type,
        normalizedRateToMdl: rate.normalized_rate_to_mdl,
        nominalUnit: rate.nominal_unit,
        providerName: rate.provider_name,
        providerType: rate.provider_type,
        effectiveAt: rate.effective_at,
        freshnessState: rate.freshness_state,
        isFallback: rate.is_fallback,
        isStale: rate.is_stale,
      };
    });

    return { status: 'loaded', snapshot, rows };
  }
}
