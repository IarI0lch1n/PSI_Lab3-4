import Decimal from 'decimal.js';
import { Injectable } from '@angular/core';
import { RateEntry } from '../../core/models/rate.models';

const ComparisonDecimal = Decimal.clone({ precision: 80 });

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
    const codes = new Set<string>();
    for (const rate of rates) {
      const value = new ComparisonDecimal(rate.normalized_rate_to_mdl);
      if (!value.isFinite() || !value.isPositive() || value.isZero() || codes.has(rate.currency)) {
        throw new Error(`Rate for ${rate.currency} is invalid.`);
      }
      codes.add(rate.currency);
    }

    return rates.map((rate) => ({
      currency: rate,
      amount:
        rate.currency === sourceCurrency
          ? amount.trim()
          : sourceAmount
              .times(sourceRate.normalized_rate_to_mdl)
              .div(rate.normalized_rate_to_mdl)
              .toString(),
    }));
  }

  private parsePositiveAmount(value: string): Decimal {
    try {
      const amount = new ComparisonDecimal(value.trim());
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
