import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';

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
  });
}
