import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/features/rates/presentation/current_rates_screen.dart';

void main() {
  testWidgets('builds the current-rates screen and shows its heading', (
    WidgetTester tester,
  ) async {
    final apiClient = RatesApiClient(
      client: MockClient((request) async {
        if (request.url.path.endsWith('/currencies')) {
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
        }
        return http.Response(
          jsonEncode({
            'snapshot_id': 'snapshot-1',
            'captured_at': '2026-10-28T12:00:00Z',
            'rates': [
              {
                'currency': 'USD',
                'normalized_rate_to_mdl': '17.400000000000000001',
                'nominal_unit': 1,
                'provider_name': 'BNM',
                'provider_type': 'fiat',
                'effective_at': '2026-10-28T09:00:00Z',
                'freshness_state': 'live',
                'is_fallback': false,
                'is_stale': false,
              },
            ],
          }),
          200,
        );
      }),
    );
    addTearDown(apiClient.client.close);

    await tester.pumpWidget(
      MaterialApp(home: CurrentRatesScreen(apiClient: apiClient)),
    );
    await tester.pumpAndSettle();

    expect(find.text('CurrencyHub'), findsOneWidget);
    expect(find.text('Current Rates'), findsOneWidget);
    expect(find.text('US Dollar'), findsOneWidget);
  });
}
