import { inject, Injectable, InjectionToken } from '@angular/core';
import { CurrencyType, FreshnessState, RateEntry, RateSnapshot } from '../models/rate.models';

export interface RateSnapshotStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const RATE_SNAPSHOT_STORAGE = new InjectionToken<RateSnapshotStorage>(
  'RATE_SNAPSHOT_STORAGE',
  {
    providedIn: 'root',
    factory: () => {
      if (typeof localStorage === 'undefined') {
        throw new RateSnapshotStoreError('Browser storage is unavailable.');
      }
      return localStorage;
    },
  },
);

export class RateSnapshotStoreError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RateSnapshotStoreError';
  }
}

const STORAGE_KEY = 'currencyhub:last-successful-rate-snapshot:v1';
const CRYPTO_CURRENT_WINDOW_MS = 15 * 60 * 1000;
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
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const DATETIME_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const POSITIVE_DECIMAL_PATTERN = /^(?:\d+(?:\.\d*)?|\.\d+)$/;

@Injectable({ providedIn: 'root' })
export class RateSnapshotStoreService {
  private readonly storage = inject(RATE_SNAPSHOT_STORAGE);

  load(now = new Date()): RateSnapshot | null {
    if (!Number.isFinite(now.getTime())) {
      throw new RangeError('The snapshot rehydration time must be valid.');
    }

    const serialized = this.storage.getItem(STORAGE_KEY);
    if (serialized === null) {
      return null;
    }

    let decoded: unknown;
    try {
      decoded = JSON.parse(serialized);
    } catch {
      throw new RateSnapshotStoreError('The stored rate snapshot is unreadable.');
    }
    if (!isRateSnapshot(decoded)) {
      throw new RateSnapshotStoreError('The stored rate snapshot is invalid or incomplete.');
    }

    return rehydrateAsCached(decoded, now);
  }

  save(snapshot: RateSnapshot): void {
    if (!isRateSnapshot(snapshot)) {
      throw new RateSnapshotStoreError('Only a complete valid rate snapshot can be stored.');
    }
    this.storage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  }

  clear(): void {
    this.storage.removeItem(STORAGE_KEY);
  }
}

function isRateSnapshot(value: unknown): value is RateSnapshot {
  if (!isRecord(value)) {
    return false;
  }
  const snapshotId = value['snapshot_id'];
  const capturedAt = value['captured_at'];
  const rates = value['rates'];
  if (
    typeof snapshotId !== 'string' ||
    !UUID_PATTERN.test(snapshotId) ||
    !isDateTime(capturedAt) ||
    !Array.isArray(rates) ||
    rates.length !== Object.keys(CURRENCY_TYPES).length
  ) {
    return false;
  }

  const seen = new Set<string>();
  for (const rate of rates) {
    if (!isRateEntry(rate) || seen.has(rate.currency)) {
      return false;
    }
    seen.add(rate.currency);
  }
  return seen.size === Object.keys(CURRENCY_TYPES).length;
}

function isRateEntry(value: unknown): value is RateEntry {
  if (!isRecord(value)) {
    return false;
  }
  const currency = value['currency'];
  if (typeof currency !== 'string' || !Object.hasOwn(CURRENCY_TYPES, currency)) {
    return false;
  }

  const rateValue = value['normalized_rate_to_mdl'];
  const nominalUnit = value['nominal_unit'];
  const providerName = value['provider_name'];
  const providerType = value['provider_type'];
  const effectiveAt = value['effective_at'];
  const freshnessState = value['freshness_state'];
  const isFallback = value['is_fallback'];
  const isStale = value['is_stale'];
  return (
    typeof rateValue === 'string' &&
    POSITIVE_DECIMAL_PATTERN.test(rateValue) &&
    /[1-9]/.test(rateValue.replace('.', '')) &&
    typeof nominalUnit === 'number' &&
    Number.isSafeInteger(nominalUnit) &&
    nominalUnit > 0 &&
    typeof providerName === 'string' &&
    providerName.trim().length > 0 &&
    providerType === CURRENCY_TYPES[currency] &&
    isDateTime(effectiveAt) &&
    isFreshnessState(freshnessState) &&
    typeof isFallback === 'boolean' &&
    typeof isStale === 'boolean'
  );
}

function isFreshnessState(value: unknown): value is FreshnessState {
  return value === 'live' || value === 'fallback' || value === 'cached';
}

function isDateTime(value: unknown): value is string {
  return (
    typeof value === 'string' && DATETIME_PATTERN.test(value) && Number.isFinite(Date.parse(value))
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function rehydrateAsCached(snapshot: RateSnapshot, now: Date): RateSnapshot {
  const capturedAt = Date.parse(snapshot.captured_at);
  const currentDate = moldovaDate(now);
  const capturedDate = moldovaDate(new Date(capturedAt));
  const publicationExpected = isBnmPublicationWeekday(currentDate);

  return {
    ...snapshot,
    rates: snapshot.rates.map((rate) => {
      const effectiveDate = moldovaDate(new Date(rate.effective_at));
      const olderFiatRate =
        rate.provider_type === 'fiat' &&
        rate.currency !== 'MDL' &&
        capturedDate < currentDate &&
        effectiveDate < currentDate;
      const staleCrypto =
        rate.provider_type === 'crypto' && now.getTime() - capturedAt > CRYPTO_CURRENT_WINDOW_MS;

      return {
        ...rate,
        freshness_state: 'cached',
        is_stale: rate.is_stale || staleCrypto || (olderFiatRate && publicationExpected),
      };
    }),
  };
}

function moldovaDate(value: Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Chisinau',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(value);
  const dateParts = new Map(parts.map((part) => [part.type, part.value]));
  const year = dateParts.get('year');
  const month = dateParts.get('month');
  const day = dateParts.get('day');
  if (!year || !month || !day) {
    throw new RateSnapshotStoreError('Could not determine the Moldova calendar date.');
  }
  return `${year}-${month}-${day}`;
}

function isBnmPublicationWeekday(date: string): boolean {
  const weekday = new Date(`${date}T12:00:00Z`).getUTCDay();
  return weekday >= 1 && weekday <= 5;
}
