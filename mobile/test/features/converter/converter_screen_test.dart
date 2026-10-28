import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/features/converter/presentation/converter_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('blocks invalid amounts before making a conversion request', (
    tester,
  ) async {
    var conversionRequests = 0;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/currencies')) {
        return _jsonResponse(_currenciesJson());
      }
      conversionRequests += 1;
      return _jsonResponse(_conversionJson());
    });
    addTearDown(client.close);

    await _pumpScreen(tester, client);

    expect(find.text('Enter a positive decimal amount.'), findsOneWidget);
    expect(find.text('Convert'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Convert'))
          .onPressed,
      isNull,
    );

    await _selectCurrency(tester, 0, 'USD');
    await _selectCurrency(tester, 1, 'BTC');
    for (final invalid in ['', '0', '0.000', '-1', 'abc', 'NaN', 'Infinity']) {
      await tester.enterText(find.byType(TextField), invalid);
      await tester.pump();
      expect(
        tester
            .widget<FilledButton>(find.widgetWithText(FilledButton, 'Convert'))
            .onPressed,
        isNull,
      );
    }
    expect(conversionRequests, 0);
  });

  testWidgets('converts the same currency and shows one applicable context', (
    tester,
  ) async {
    Map<String, dynamic>? requestBody;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/currencies')) {
        return _jsonResponse(_currenciesJson());
      }
      requestBody = jsonDecode(request.body) as Map<String, dynamic>;
      return _jsonResponse(
        _conversionJson(
          sourceCurrency: 'USD',
          targetCurrency: 'USD',
          convertedAmount: '25.00',
          rateValue: '1',
        ),
      );
    });
    addTearDown(client.close);

    await _pumpScreen(tester, client);
    await tester.enterText(find.byType(TextField), '25');
    await _selectCurrency(tester, 0, 'USD');
    await _selectCurrency(tester, 1, 'USD');
    await tester.tap(find.widgetWithText(FilledButton, 'Convert'));
    await tester.pumpAndSettle();

    expect(requestBody, {
      'amount': '25',
      'source_currency': 'USD',
      'target_currency': 'USD',
    });
    expect(find.text('25.00 USD'), findsOneWidget);
    expect(find.text('1 USD = 1 USD'), findsOneWidget);
    expect(find.text('Source rate context — USD'), findsOneWidget);
    expect(find.text('Target rate context — USD'), findsOneWidget);
  });

  testWidgets(
    'identifies an unavailable required rate without showing a result',
    (tester) async {
      final client = MockClient((request) async {
        if (request.url.path.endsWith('/currencies')) {
          return _jsonResponse(_currenciesJson());
        }
        return http.Response(
          jsonEncode({
            'error': {
              'code': 'rate_unavailable',
              'message': 'Rate for BTC is unavailable.',
            },
          }),
          404,
        );
      });
      addTearDown(client.close);

      await _pumpScreen(tester, client);
      await tester.enterText(find.byType(TextField), '25');
      await _selectCurrency(tester, 0, 'USD');
      await _selectCurrency(tester, 1, 'BTC');
      await tester.tap(find.widgetWithText(FilledButton, 'Convert'));
      await tester.pumpAndSettle();

      expect(find.text('Rate for BTC is unavailable.'), findsOneWidget);
      expect(find.text('Conversion result'), findsNothing);
    },
  );

  testWidgets('shows independent source and target provenance labels', (
    tester,
  ) async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/currencies')) {
        return _jsonResponse(_currenciesJson());
      }
      return _jsonResponse(_conversionJson());
    });
    addTearDown(client.close);

    await _pumpScreen(tester, client);
    await tester.enterText(find.byType(TextField), '25');
    await _selectCurrency(tester, 0, 'USD');
    await _selectCurrency(tester, 1, 'BTC');
    await tester.tap(find.widgetWithText(FilledButton, 'Convert'));
    await tester.pumpAndSettle();

    expect(find.text('Source rate context — USD'), findsOneWidget);
    expect(find.text('Target rate context — BTC'), findsOneWidget);
    final sourceCard = find
        .ancestor(
          of: find.text('Source rate context — USD'),
          matching: find.byType(Card),
        )
        .first;
    final targetCard = find
        .ancestor(
          of: find.text('Target rate context — BTC'),
          matching: find.byType(Card),
        )
        .first;
    expect(
      find.descendant(of: sourceCard, matching: find.text('BNM')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: targetCard, matching: find.text('CoinGecko')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: sourceCard, matching: find.text('Stale')),
      findsNothing,
    );
    expect(
      find.descendant(of: sourceCard, matching: find.text('Fallback used')),
      findsNothing,
    );
    expect(find.text('2026-10-28T09:00:00Z'), findsOneWidget);
    expect(find.text('2026-10-28T11:45:00Z'), findsOneWidget);
    expect(find.text('Live'), findsOneWidget);
    expect(find.text('Cached'), findsOneWidget);
    expect(find.text('Stale'), findsOneWidget);
    expect(find.text('Fallback used'), findsOneWidget);
  });
}

Future<void> _pumpScreen(WidgetTester tester, http.Client client) async {
  tester.view.physicalSize = const Size(1000, 3000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      home: ConverterScreen(apiClient: RatesApiClient(client: client)),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _selectCurrency(
  WidgetTester tester,
  int selectorIndex,
  String currency,
) async {
  await tester.tap(
    find.byType(DropdownButtonFormField<String>).at(selectorIndex),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.textContaining('$currency — ').last);
  await tester.pumpAndSettle();
}

http.Response _jsonResponse(Map<String, dynamic> body) {
  return http.Response(jsonEncode(body), 200);
}

Map<String, dynamic> _currenciesJson() {
  return {
    'currencies': [
      {
        'code': 'USD',
        'name': 'US Dollar',
        'type': 'fiat',
        'is_supported': true,
      },
      {
        'code': 'BTC',
        'name': 'Bitcoin',
        'type': 'crypto',
        'is_supported': true,
      },
    ],
  };
}

Map<String, dynamic> _conversionJson({
  String sourceCurrency = 'USD',
  String targetCurrency = 'BTC',
  String convertedAmount = '0.0004',
  String rateValue = '0.000016',
}) {
  return {
    'source_amount': '25',
    'converted_amount': convertedAmount,
    'source_currency': sourceCurrency,
    'target_currency': targetCurrency,
    'rate_value': rateValue,
    'rate_context': {
      'snapshot_id': 'snapshot-2026-10-28',
      'source_rate': {
        'currency': 'USD',
        'provider_name': 'BNM',
        'effective_at': '2026-10-28T09:00:00Z',
        'freshness_state': 'live',
        'is_fallback': false,
        'is_stale': false,
      },
      'target_rate': {
        'currency': targetCurrency,
        'provider_name': targetCurrency == 'USD' ? 'BNM' : 'CoinGecko',
        'effective_at': targetCurrency == 'USD'
            ? '2026-10-28T09:00:00Z'
            : '2026-10-28T11:45:00Z',
        'freshness_state': targetCurrency == 'USD' ? 'live' : 'cached',
        'is_fallback': targetCurrency != 'USD',
        'is_stale': targetCurrency != 'USD',
      },
    },
  };
}
