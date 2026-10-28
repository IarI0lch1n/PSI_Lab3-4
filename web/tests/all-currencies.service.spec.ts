import { describe, expect, it } from 'vitest';
import { RateEntry } from '../src/app/core/models/rate.models';
import { AllCurrenciesService } from '../src/app/features/rates/all-currencies.service';

const rates: readonly RateEntry[] = [
  {
    currency: 'EUR',
    normalized_rate_to_mdl: '19.1234567890123456789',
    nominal_unit: 1,
    provider_name: 'BNM',
    provider_type: 'fiat',
    effective_at: '2026-10-28T09:00:00Z',
    freshness_state: 'live',
    is_fallback: false,
    is_stale: false,
  },
  {
    currency: 'USD',
    normalized_rate_to_mdl: '17.400000000000000001',
    nominal_unit: 1,
    provider_name: 'BNM',
    provider_type: 'fiat',
    effective_at: '2026-10-28T09:00:00Z',
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
];

describe('AllCurrenciesService', () => {
  it('calculates every value with Decimal arithmetic from the selected source rate', () => {
    const values = new AllCurrenciesService().calculate('123.456789012345678901', 'EUR', rates);

    expect(values.map((value) => [value.currency.currency, value.amount])).toEqual([
      ['EUR', '123.456789012345678901'],
      ['USD', '135.68509022918429515710510842226034228343648802170917573083698344702820829133121'],
      [
        'BTC',
        '0.0043540132313855185846072873931244005208926820425121638919733158798104382173136955',
      ],
    ]);
    expect(values[1].currency.freshness_state).toBe('fallback');
    expect(values[2].currency.is_stale).toBe(true);
  });

  it('rejects invalid amounts and missing source rates', () => {
    const service = new AllCurrenciesService();

    expect(() => service.calculate('0', 'EUR', rates)).toThrow('Amount must be greater than zero.');
    expect(() => service.calculate('not-a-number', 'EUR', rates)).toThrow(
      'Amount must be a finite positive decimal.',
    );
    expect(() => service.calculate('1', 'GBP', rates)).toThrow('Rate for GBP is unavailable.');
  });
});
