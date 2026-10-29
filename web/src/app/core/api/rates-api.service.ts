import { HttpClient } from '@angular/common/http';
import { inject, Injectable, InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import {
  CurrenciesResponse,
  AnalyticsPeriod,
  AnalyticsResponse,
  ConversionRequest,
  ConversionResponse,
  HistoryResponse,
  RateSnapshot,
} from '../models/rate.models';

export const CURRENCYHUB_API_BASE_URL = new InjectionToken<string>('CURRENCYHUB_API_BASE_URL', {
  providedIn: 'root',
  factory: () => 'http://localhost:8000/api/v1',
});

@Injectable({ providedIn: 'root' })
export class RatesApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(CURRENCYHUB_API_BASE_URL).replace(/\/+$/, '');

  getCurrencies(): Observable<CurrenciesResponse> {
    return this.http.get<CurrenciesResponse>(`${this.baseUrl}/currencies`);
  }

  getLatestRates(): Observable<RateSnapshot> {
    return this.http.get<RateSnapshot>(`${this.baseUrl}/rates/latest`);
  }

  convert(request: ConversionRequest): Observable<ConversionResponse> {
    return this.http.post<ConversionResponse>(`${this.baseUrl}/convert`, request);
  }

  getHistory(
    baseCurrency: string,
    quoteCurrency: string,
    period: AnalyticsPeriod,
  ): Observable<HistoryResponse> {
    return this.http.get<HistoryResponse>(`${this.baseUrl}/history`, {
      params: {
        base_currency: baseCurrency,
        quote_currency: quoteCurrency,
        period,
      },
    });
  }

  getAnalytics(
    baseCurrency: string,
    quoteCurrency: string,
    period: AnalyticsPeriod,
  ): Observable<AnalyticsResponse> {
    return this.http.get<AnalyticsResponse>(`${this.baseUrl}/analytics`, {
      params: {
        base_currency: baseCurrency,
        quote_currency: quoteCurrency,
        period,
      },
    });
  }
}
