import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  CURRENCYHUB_API_BASE_URL,
  RatesApiService,
} from './rates-api.service';
import { CurrenciesResponse, RateSnapshot } from '../models/rate.models';

describe('RatesApiService', () => {
  let httpTestingController: HttpTestingController;
  let service: RatesApiService;
  const customBaseUrl = 'https://currencyhub.example/api/v1///';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: CURRENCYHUB_API_BASE_URL, useValue: customBaseUrl },
      ],
    });

    httpTestingController = TestBed.inject(HttpTestingController);
    service = TestBed.inject(RatesApiService);
  });

  afterEach(() => {
    httpTestingController.verify();
  });

  it('can be injected', () => {
    expect(service).toBeTruthy();
  });

  it('gets currencies from the configured API base URL', () => {
    const response: CurrenciesResponse = {
      currencies: [
        {
          code: 'USD',
          name: 'US Dollar',
          type: 'fiat',
          is_supported: true,
        },
      ],
    };

    service.getCurrencies().subscribe((result) => {
      expect(result).toEqual(response);
    });

    const request = httpTestingController.expectOne(
      'https://currencyhub.example/api/v1/currencies',
    );
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });

  it('gets latest rates and preserves independent metadata and decimal strings', () => {
    const response: RateSnapshot = {
      snapshot_id: 'snapshot-123',
      captured_at: '2026-10-28T09:00:00Z',
      rates: [
        {
          currency: 'RON',
          normalized_rate_to_mdl: '17.400000000000000001',
          nominal_unit: 1,
          provider_name: 'BNM',
          provider_type: 'fiat',
          effective_at: '2026-10-28T08:00:00Z',
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
          effective_at: '2026-10-28T08:30:00Z',
          freshness_state: 'cached',
          is_fallback: false,
          is_stale: true,
        },
      ],
    };

    service.getLatestRates().subscribe((result) => {
      expect(result).toEqual(response);
      expect(typeof result.rates[0].normalized_rate_to_mdl).toBe('string');
      expect(result.rates[0].normalized_rate_to_mdl).toBe(
        '17.400000000000000001',
      );
      expect(result.rates[0].freshness_state).toBe('fallback');
      expect(result.rates[0].is_fallback).toBe(true);
      expect(result.rates[0].is_stale).toBe(false);
      expect(result.rates[1].freshness_state).toBe('cached');
      expect(result.rates[1].is_fallback).toBe(false);
      expect(result.rates[1].is_stale).toBe(true);
    });

    const request = httpTestingController.expectOne(
      'https://currencyhub.example/api/v1/rates/latest',
    );
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });
});
