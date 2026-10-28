import Decimal from 'decimal.js';
import { Injectable } from '@angular/core';
import { RateEntry } from '../../core/models/rate.models';

Decimal.set({ precision: 80 });

export interface CalculatedCurrencyValue {
  readonly currency: RateEntry;
  readonly amount: string;
}

@Injectable({ providedIn: 'root' })
export class AllCurrenciesService {
  calculate(
    amount: string,
    sourceCurrency: string,
    rates: readonly RateEntry[],
  ): readonly CalculatedCurrencyValue[] {
    const sourceAmount = this.parsePositiveAmount(amount);
    const sourceRate = this.findRate(sourceCurrency, rates);

    return rates.map((rate) => ({
      currency: rate,
      amount: sourceAmount
        .times(sourceRate.normalized_rate_to_mdl)
        .div(rate.normalized_rate_to_mdl)
        .toString(),
    }));
  }

  private parsePositiveAmount(value: string): Decimal {
    try {
      const amount = new Decimal(value.trim());
      if (!amount.isFinite() || amount.isNegative() || amount.isZero()) {
        throw new Error('Amount must be greater than zero.');
      }
      return amount;
    } catch (error) {
      if (error instanceof Error && error.message === 'Amount must be greater than zero.') {
        throw error;
      }
      throw new Error('Amount must be a finite positive decimal.');
    }
  }

  private findRate(currency: string, rates: readonly RateEntry[]): RateEntry {
    const rate = rates.find((entry) => entry.currency === currency);
    if (!rate) {
      throw new Error(`Rate for ${currency} is unavailable.`);
    }
    return rate;
  }
}
