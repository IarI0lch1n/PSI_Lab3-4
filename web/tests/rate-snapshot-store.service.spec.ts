import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  RATE_SNAPSHOT_STORAGE,
  RateSnapshotStorage,
  RateSnapshotStoreError,
  RateSnapshotStoreService,
} from '../src/app/core/storage/rate-snapshot-store.service';
import { CurrencyType, RateSnapshot } from '../src/app/core/models/rate.models';

const SNAPSHOT_ID = '00000000-0000-4000-8000-000000000055';
const CURRENCY_TYPES: Readonly<Record<string, CurrencyType>> = {
  MDL: 'fiat',
  USD: 'fiat',
  EUR: 'fiat',
  RUB: 'fiat',
  CNY: 'fiat',
  GBP: 'fiat',
  RON: 'fiat',
  UAH: 'fiat',
  CHF: 'fiat',
  JPY: 'fiat',
  BTC: 'crypto',
  ETH: 'crypto',
  SOL: 'crypto',
  BNB: 'crypto',
  XRP: 'crypto',
  ADA: 'crypto',
  DOGE: 'crypto',
  USDT: 'crypto',
};
const STORAGE_KEY = 'currencyhub:last-successful-rate-snapshot:v1';

describe('RateSnapshotStoreService', () => {
  let storage: MemoryRateSnapshotStorage;
  let service: RateSnapshotStoreService;

  beforeEach(() => {
    storage = new MemoryRateSnapshotStorage();
    TestBed.configureTestingModule({
      providers: [RateSnapshotStoreService, { provide: RATE_SNAPSHOT_STORAGE, useValue: storage }],
    });
    service = TestBed.inject(RateSnapshotStoreService);
  });

  it('returns no snapshot when the persistent store is empty', () => {
    expect(service.load()).toBeNull();
  });

  it('persists and rehydrates the full snapshot without age-based deletion', () => {
    const snapshot = createSnapshot();
    service.save(snapshot);

    const rehydrated = service.load(new Date('2036-10-28T12:00:00Z'));

    expect(rehydrated).not.toBeNull();
    expect(rehydrated?.snapshot_id).toBe(snapshot.snapshot_id);
    expect(rehydrated?.captured_at).toBe(snapshot.captured_at);
    expect(rehydrated?.rates).toHaveLength(18);
    expect(storage.values.has(STORAGE_KEY)).toBe(true);
    expect(storage.removeItem).not.toHaveBeenCalled();
  });

  it('reports unreadable JSON and structurally invalid snapshots as cache errors', () => {
    storage.values.set(STORAGE_KEY, '{not json');
    expect(() => service.load()).toThrow(RateSnapshotStoreError);

    const incomplete = { ...createSnapshot(), rates: createSnapshot().rates.slice(1) };
    storage.values.set(STORAGE_KEY, JSON.stringify(incomplete));
    try {
      service.load();
      throw new Error('Expected the incomplete cache to be rejected.');
    } catch (error) {
      expect(error).toBeInstanceOf(RateSnapshotStoreError);
      expect((error as RateSnapshotStoreError).unavailableCurrencies).toEqual(['MDL']);
      expect((error as Error).message).toContain('Unavailable required currencies: MDL.');
    }
  });

  it.each([
    [
      'missing currency',
      (snapshot: RateSnapshot) => ({ ...snapshot, rates: snapshot.rates.slice(1) }),
    ],
    [
      'duplicate currency',
      (snapshot: RateSnapshot) => ({
        ...snapshot,
        rates: [snapshot.rates[0], ...snapshot.rates.slice(1, -1), snapshot.rates[0]],
      }),
    ],
    [
      'zero rate',
      (snapshot: RateSnapshot) => ({
        ...snapshot,
        rates: [{ ...snapshot.rates[0], normalized_rate_to_mdl: '0' }, ...snapshot.rates.slice(1)],
      }),
    ],
    [
      'non-decimal rate',
      (snapshot: RateSnapshot) => ({
        ...snapshot,
        rates: [
          { ...snapshot.rates[0], normalized_rate_to_mdl: '1e3' },
          ...snapshot.rates.slice(1),
        ],
      }),
    ],
    [
      'missing provider',
      (snapshot: RateSnapshot) => ({
        ...snapshot,
        rates: [{ ...snapshot.rates[0], provider_name: ' ' }, ...snapshot.rates.slice(1)],
      }),
    ],
    [
      'invalid effective time',
      (snapshot: RateSnapshot) => ({
        ...snapshot,
        rates: [{ ...snapshot.rates[0], effective_at: 'not-a-time' }, ...snapshot.rates.slice(1)],
      }),
    ],
  ])('rejects snapshots with %s', (_case, mutate) => {
    expect(() => service.save(mutate(createSnapshot()))).toThrow(RateSnapshotStoreError);
    expect(storage.setItem).not.toHaveBeenCalled();
  });

  it('rehydrates cached state without changing the original snapshot or rate times', () => {
    const snapshot = createSnapshot();
    service.save(snapshot);

    const rehydrated = service.load(new Date(snapshot.captured_at));

    expect(rehydrated).not.toBeNull();
    expect(rehydrated?.captured_at).toBe(snapshot.captured_at);
    expect(rehydrated?.rates.map((rate) => rate.effective_at)).toEqual(
      snapshot.rates.map((rate) => rate.effective_at),
    );
    expect(rehydrated?.rates.every((rate) => rate.freshness_state === 'cached')).toBe(true);
    expect(rehydrated?.rates[1].freshness_state).toBe('cached');
    expect(rehydrated?.rates[1].is_fallback).toBe(true);
    expect(rehydrated?.rates[1].is_stale).toBe(false);
    expect(storage.read(STORAGE_KEY)).toBe(JSON.stringify(snapshot));
  });

  it('resolves cached required rates with original provider and effective time', () => {
    const snapshot = createSnapshot();
    service.save(snapshot);

    const cached = service.load(new Date(snapshot.captured_at));
    const resolution = service.resolveRequiredRates(cached, ['BTC', 'EUR']);

    expect(resolution.status).toBe('available');
    if (resolution.status !== 'available') {
      throw new Error('Expected all required rates to be available.');
    }
    expect(resolution.rates.map((rate) => rate.currency)).toEqual(['BTC', 'EUR']);
    expect(resolution.rates[0]).toMatchObject({
      provider_name: 'CoinGecko',
      effective_at: '2026-10-28T11:45:00Z',
      freshness_state: 'cached',
      is_fallback: false,
    });
    expect(resolution.rates[1]).toMatchObject({
      provider_name: 'BNM',
      effective_at: '2026-10-28T09:00:00Z',
      freshness_state: 'cached',
      is_fallback: false,
    });
  });

  it('identifies unavailable required currencies without exposing a partial pair', () => {
    const snapshot = createSnapshot();
    const partial = {
      ...snapshot,
      rates: snapshot.rates.filter((rate) => rate.currency !== 'BTC'),
    };

    const resolution = service.resolveRequiredRates(partial, ['EUR', 'BTC']);

    expect(resolution).toEqual({
      status: 'unavailable',
      unavailableCurrencies: ['BTC'],
      message: 'Required currency rates are unavailable: BTC.',
    });
    expect('rates' in resolution).toBe(false);
  });

  it('reports all required currencies unavailable when no cached snapshot exists', () => {
    expect(service.resolveRequiredRates(null, ['EUR', 'BTC'])).toEqual({
      status: 'unavailable',
      unavailableCurrencies: ['EUR', 'BTC'],
      message: 'Required currency rates are unavailable: EUR, BTC.',
    });
  });

  it('preserves canonical freshness and provenance semantics through outage and restart', () => {
    const snapshot = createCrossClientSnapshot();
    service.save(snapshot);

    const persisted = JSON.parse(storage.read(STORAGE_KEY) ?? 'null') as RateSnapshot;
    expect(persisted.rates.find((rate) => rate.currency === 'MDL')).toMatchObject({
      freshness_state: 'live',
      is_fallback: false,
      is_stale: false,
    });
    expect(persisted.rates.find((rate) => rate.currency === 'USD')).toMatchObject({
      freshness_state: 'fallback',
      is_fallback: true,
      is_stale: false,
      provider_name: 'BNM',
      effective_at: '2026-10-30T09:00:00Z',
    });
    expect(persisted.rates.find((rate) => rate.currency === 'EUR')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: false,
    });
    expect(persisted.rates.find((rate) => rate.currency === 'BTC')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: true,
    });

    storage.setItem.mockImplementationOnce(() => {
      throw new Error('Simulated refresh outage.');
    });
    expect(() => service.save(createSnapshot('00000000-0000-4000-8000-000000000057'))).toThrow(
      'Simulated refresh outage.',
    );
    expect(storage.read(STORAGE_KEY)).toBe(JSON.stringify(snapshot));

    const restartedService = TestBed.runInInjectionContext(() => new RateSnapshotStoreService());
    const offline = restartedService.load(new Date(snapshot.captured_at));
    const rates = new Map(offline?.rates.map((rate) => [rate.currency, rate]));

    expect(rates.get('MDL')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: false,
      provider_name: 'BNM',
      effective_at: '2026-10-28T09:00:00Z',
    });
    expect(rates.get('USD')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: true,
      is_stale: false,
      provider_name: 'BNM',
      effective_at: '2026-10-30T09:00:00Z',
    });
    expect(rates.get('EUR')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: false,
      provider_name: 'BNM',
      effective_at: '2026-10-28T09:00:00Z',
    });
    expect(rates.get('BTC')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: true,
      provider_name: 'CoinGecko',
      effective_at: '2026-10-28T11:45:00Z',
    });

    const laterWeekday = restartedService.load(new Date('2026-11-02T12:00:00Z'));
    const weekdayRates = new Map(laterWeekday?.rates.map((rate) => [rate.currency, rate]));
    expect(weekdayRates.get('EUR')).toMatchObject({
      freshness_state: 'cached',
      is_fallback: false,
      is_stale: true,
      provider_name: 'BNM',
      effective_at: '2026-10-28T09:00:00Z',
    });

    const incomplete = {
      ...offline!,
      rates: offline!.rates.filter((rate) => rate.currency !== 'BTC'),
    };
    const pair = restartedService.resolveRequiredRates(incomplete, ['EUR', 'BTC']);
    expect(pair).toEqual({
      status: 'unavailable',
      unavailableCurrencies: ['BTC'],
      message: 'Required currency rates are unavailable: BTC.',
    });
    expect('rates' in pair).toBe(false);
  });

  it('recalculates crypto staleness at and just beyond the 15-minute boundary', () => {
    const snapshot = createSnapshot();
    service.save(snapshot);

    const atBoundary = service.load(new Date('2026-10-28T12:15:00.000Z'));
    const afterBoundary = service.load(new Date('2026-10-28T12:15:00.001Z'));

    expect(atBoundary?.rates.find((rate) => rate.currency === 'BTC')?.is_stale).toBe(false);
    expect(afterBoundary?.rates.find((rate) => rate.currency === 'BTC')?.is_stale).toBe(true);
    expect(afterBoundary?.rates.find((rate) => rate.currency === 'BTC')?.effective_at).toBe(
      '2026-10-28T11:45:00Z',
    );
    expect(afterBoundary?.rates.find((rate) => rate.currency === 'BTC')?.is_fallback).toBe(false);
  });

  it('marks an older BNM rate stale on a later publication weekday but not on a weekend', () => {
    const snapshot = createSnapshot();
    service.save(snapshot);

    const weekday = service.load(new Date('2026-10-29T12:00:00Z'));
    const weekend = service.load(new Date('2026-10-31T12:00:00Z'));

    expect(weekday?.rates.find((rate) => rate.currency === 'USD')?.is_stale).toBe(true);
    expect(weekend?.rates.find((rate) => rate.currency === 'USD')?.is_stale).toBe(false);
  });

  it('replaces a snapshot in one write and leaves the previous value on invalid replacement', () => {
    const original = createSnapshot();
    service.save(original);
    const replacement = {
      ...createSnapshot('00000000-0000-4000-8000-000000000056'),
      captured_at: '2026-10-28T13:00:00Z',
    };

    service.save(replacement);
    expect(storage.setItem).toHaveBeenCalledTimes(2);
    expect(service.load(new Date(replacement.captured_at))?.snapshot_id).toBe(
      replacement.snapshot_id,
    );

    const storedBeforeInvalidReplacement = storage.read(STORAGE_KEY);
    const incomplete = { ...replacement, rates: replacement.rates.slice(1) };
    expect(() => service.save(incomplete)).toThrow(RateSnapshotStoreError);
    expect(storage.read(STORAGE_KEY)).toBe(storedBeforeInvalidReplacement);
    expect(storage.setItem).toHaveBeenCalledTimes(2);
  });

  it('clears only when explicitly requested', () => {
    service.save(createSnapshot());
    service.clear();

    expect(service.load()).toBeNull();
    expect(storage.removeItem).toHaveBeenCalledTimes(1);
    expect(storage.removeItem).toHaveBeenCalledWith(STORAGE_KEY);
  });
});

class MemoryRateSnapshotStorage implements RateSnapshotStorage {
  readonly values = new Map<string, string>();
  readonly getItem = vi.fn((key: string) => this.values.get(key) ?? null);
  readonly setItem = vi.fn((key: string, value: string) => {
    this.values.set(key, value);
  });
  readonly removeItem = vi.fn((key: string) => {
    this.values.delete(key);
  });

  read(key: string): string | null {
    return this.values.get(key) ?? null;
  }
}

function createSnapshot(snapshotId = SNAPSHOT_ID): RateSnapshot {
  const rates = Object.entries(CURRENCY_TYPES).map(([currency, providerType], index) => ({
    currency,
    normalized_rate_to_mdl: String(index + 1),
    nominal_unit: 1,
    provider_name: providerType === 'crypto' ? 'CoinGecko' : 'BNM',
    provider_type: providerType,
    effective_at: providerType === 'crypto' ? '2026-10-28T11:45:00Z' : '2026-10-28T09:00:00Z',
    freshness_state: currency === 'USD' ? ('fallback' as const) : ('live' as const),
    is_fallback: currency === 'USD',
    is_stale: false,
  }));
  return {
    snapshot_id: snapshotId,
    captured_at: '2026-10-28T12:00:00Z',
    rates,
  };
}

function createCrossClientSnapshot(): RateSnapshot {
  const snapshot = createSnapshot();
  return {
    ...snapshot,
    captured_at: '2026-10-31T12:00:00Z',
    rates: snapshot.rates.map((rate) => {
      switch (rate.currency) {
        case 'MDL':
          return {
            ...rate,
            freshness_state: 'live' as const,
            is_fallback: false,
            is_stale: false,
          };
        case 'USD':
          return {
            ...rate,
            effective_at: '2026-10-30T09:00:00Z',
            freshness_state: 'fallback' as const,
            is_fallback: true,
            is_stale: false,
          };
        case 'EUR':
          return {
            ...rate,
            freshness_state: 'cached' as const,
            is_fallback: false,
            is_stale: false,
          };
        case 'BTC':
          return {
            ...rate,
            freshness_state: 'cached' as const,
            is_fallback: false,
            is_stale: true,
          };
        default:
          return rate;
      }
    }),
  };
}
