import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/core/models/rate_models.dart';

void main() {
  group('RatesApiClient', () {
    test('gets currencies from the default API base URL', () async {
      final client = RatesApiClient(
        client: MockClient((request) async {
          expect(request.method, 'GET');
          expect(
            request.url.toString(),
            'http://10.0.2.2:8000/api/v1/currencies',
          );
          return http.Response(
            jsonEncode({
              'currencies': [
                {
                  'code': 'USD',
                  'name': 'US Dollar',
                  'type': 'fiat',
                  'is_supported': true,
                },
              ],
            }),
            200,
          );
        }),
      );

      final result = await client.getCurrencies();
      expect(result.currencies.single.code, 'USD');
    });

    test('honors a custom base URL and removes trailing slashes', () async {
      final client = RatesApiClient(
        baseUrl: 'https://example.test/api/v1///',
        client: MockClient((request) async {
          expect(request.method, 'GET');
          expect(
            request.url.toString(),
            'https://example.test/api/v1/rates/latest',
          );
          return http.Response(
            jsonEncode({
              'snapshot_id': 'snapshot-123',
              'captured_at': '2026-10-28T09:00:00Z',
              'rates': [],
            }),
            200,
          );
        }),
      );

      final result = await client.getLatestRates();
      expect(result.snapshotId, 'snapshot-123');
    });

    test('throws a clear exception for unsuccessful HTTP responses', () async {
      final client = RatesApiClient(
        baseUrl: 'https://example.test/api/v1',
        client: MockClient((_) async => http.Response('Unavailable', 503)),
      );

      await expectLater(
        client.getCurrencies(),
        throwsA(
          isA<RatesApiException>()
              .having((error) => error.statusCode, 'statusCode', 503)
              .having(
                (error) => error.toString(),
                'message',
                contains('HTTP 503'),
              ),
        ),
      );
    });

    test(
      'requests history and analytics with the selected pair and period',
      () async {
        final paths = <String>[];
        final client = RatesApiClient(
          baseUrl: 'https://example.test/api/v1',
          client: MockClient((request) async {
            paths.add(request.url.path);
            expect(request.url.queryParameters, {
              'base_currency': 'EUR',
              'quote_currency': 'BTC',
              'period': '30d',
            });
            if (request.url.path.endsWith('/history')) {
              return http.Response(
                jsonEncode({
                  'base_currency': 'EUR',
                  'quote_currency': 'BTC',
                  'period': '30d',
                  'points': [],
                  'empty': true,
                }),
                200,
              );
            }
            return http.Response(
              jsonEncode({
                'base_currency': 'EUR',
                'quote_currency': 'BTC',
                'period': '30d',
                'points': [],
                'provenance_summary': {
                  'point_count': 0,
                  'source_providers': [],
                  'target_providers': [],
                  'rate_entry_freshness_counts': {
                    'live': 0,
                    'fallback': 0,
                    'cached': 0,
                  },
                  'stale_entry_count': 0,
                  'fallback_entry_count': 0,
                },
                'empty': true,
              }),
              200,
            );
          }),
        );

        final history = await client.getHistory(
          'EUR',
          'BTC',
          AnalyticsPeriod.thirtyDays,
        );
        final analytics = await client.getAnalytics(
          'EUR',
          'BTC',
          AnalyticsPeriod.thirtyDays,
        );

        expect(paths, ['/api/v1/history', '/api/v1/analytics']);
        expect(history.empty, isTrue);
        expect(analytics.empty, isTrue);
      },
    );
  });
}
