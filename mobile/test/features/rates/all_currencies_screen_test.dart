import 'dart:async';
import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/features/rates/presentation/all_currencies_screen.dart';
import 'package:currencyhub_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const capturedAt = '2026-10-28T12:00:00Z';
const fiatTime = '2026-10-28T09:00:00Z';
const fallbackTime = '2026-10-27T09:00:00Z';
const cryptoTime = '2026-10-28T11:45:00Z';

void main() {
  testWidgets('waits for both currency metadata and the snapshot', (
    tester,
  ) async {
    final response = Completer<http.Response>();
    await pumpScreen(tester, latest: () => response.future, settle: false);
    await tester.pump();
    expect(find.text('Loading currency comparison…'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    response.complete(jsonResponse(snapshot()));
    await tester.pumpAndSettle();
    expect(find.text(capturedAt), findsOneWidget);
    expect(find.byKey(const Key('comparison-EUR')), findsNothing);
    expect(amount(tester, 'USD'), '0.50');
    expect(amount(tester, 'BTC'), '0.25');
  });

  testWidgets(
    'searches supported entry currencies and switches without refetch',
    (tester) async {
      final requests = <String>[];
      await pumpScreen(tester, requests: requests);
      await tester.tap(find.byKey(const Key('currency-picker-entry-currency')));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(ListTile, 'EUR'), findsOneWidget);
      expect(find.widgetWithText(ListTile, 'USD'), findsOneWidget);
      expect(find.widgetWithText(ListTile, 'BTC'), findsOneWidget);
      expect(find.widgetWithText(ListTile, 'MDL'), findsOneWidget);
      expect(find.widgetWithText(ListTile, 'XXX'), findsNothing);
      await tester.tap(find.widgetWithText(ListTile, 'USD'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('comparison-EUR')), findsOneWidget);
      expect(find.byKey(const Key('comparison-USD')), findsNothing);
      expect(amount(tester, 'EUR'), '2.00');
      expect(amount(tester, 'BTC'), '0.50');
      expect(amount(tester, 'MDL'), '4.00');
      await tester.enterText(
        find.byKey(const Key('comparison-amount')),
        '0.100000000000000001',
      );
      await tester.pumpAndSettle();
      expect(amount(tester, 'EUR'), '0.20');
      expect(find.byKey(const Key('comparison-USD')), findsNothing);
      expect(amount(tester, 'BTC'), '0.05');
      expect(find.text(capturedAt), findsOneWidget);
      expect(
        requests.where((path) => path.endsWith('/rates/latest')).length,
        1,
      );
      expect(requests.where((path) => path.endsWith('/currencies')).length, 1);
    },
  );

  testWidgets('keeps rate details collapsed until requested', (tester) async {
    await pumpScreen(tester);
    expect(find.byKey(const Key('comparison-EUR')), findsNothing);
    expectIn('USD', 'BNM', absent: true);
    expectIn('USD', fallbackTime, absent: true);
    expectIn('USD', 'Fallback');
    expectIn('USD', 'Fallback used');
    expectIn('USD', 'Stale', absent: true);
    expectIn('BTC', 'CoinGecko', absent: true);
    expectIn('BTC', cryptoTime, absent: true);
    expectIn('BTC', 'Cached');
    expectIn('BTC', 'Stale');
    expectIn('BTC', 'Fallback used', absent: true);

    final usdCard = find.byKey(const Key('comparison-USD'));
    await tester.tap(
      find.descendant(of: usdCard, matching: find.text('Show more')),
    );
    await tester.pumpAndSettle();
    expectIn('USD', 'BNM');
    expectIn('USD', fallbackTime);
    expectIn('USD', 'Show less');
    expect(find.text(capturedAt), findsOneWidget);
  });

  testWidgets('cached alone implies neither fallback-used nor stale', (
    tester,
  ) async {
    final data = snapshot();
    for (final entry in data['rates'] as List<Map<String, dynamic>>) {
      entry['freshness_state'] = 'cached';
      entry['is_fallback'] = false;
      entry['is_stale'] = false;
    }
    await pumpScreen(tester, latest: () async => jsonResponse(data));
    expect(find.text('Cached'), findsNWidgets(3));
    expect(find.text('Fallback used'), findsNothing);
    expect(find.text('Stale'), findsNothing);
  });

  for (final invalid in ['', '0', '0.00', '-1', 'text', 'NaN', 'Infinity']) {
    testWidgets('invalid amount "$invalid" clears every result', (
      tester,
    ) async {
      await pumpScreen(tester);
      await tester.enterText(
        find.byKey(const Key('comparison-amount')),
        invalid,
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('comparison-USD')), findsNothing);
      expect(find.byKey(const Key('comparison-BTC')), findsNothing);
      expect(
        find.textContaining(
          invalid.contains('0') ? 'greater than zero' : 'valid positive',
        ),
        findsOneWidget,
      );
      expect(find.text(capturedAt), findsOneWidget);
      await tester.enterText(find.byKey(const Key('comparison-amount')), '2');
      await tester.pumpAndSettle();
      expect(amount(tester, 'USD'), '1.00');
    });
  }

  for (final path in ['/currencies', '/rates/latest']) {
    testWidgets('safe load failure and Retry after $path fails', (
      tester,
    ) async {
      var fail = true;
      final client = MockClient((request) async {
        if (fail && request.url.path.endsWith(path)) {
          return http.Response('secret diagnostic', 503);
        }
        return jsonResponse(
          request.url.path.endsWith('/currencies') ? currencies() : snapshot(),
        );
      });
      await pumpScreen(tester, client: client);
      expect(find.textContaining('Comparison is unavailable'), findsOneWidget);
      expect(find.textContaining('secret diagnostic'), findsNothing);
      expect(find.byType(Card), findsNothing);
      fail = false;
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(amount(tester, 'BTC'), '0.25');
    });
  }

  for (final defect in [
    'missing',
    'duplicate',
    'provider',
    'time',
    'rate',
    'snapshot',
  ]) {
    testWidgets('rejects $defect snapshot defect', (tester) async {
      final data = snapshot();
      final rates = data['rates'] as List<Map<String, dynamic>>;
      switch (defect) {
        case 'missing':
          rates.removeLast();
        case 'duplicate':
          rates[1] = rates[0];
        case 'provider':
          rates[0]['provider_name'] = '';
        case 'time':
          rates[0]['effective_at'] = 'invalid';
        case 'rate':
          rates[0]['normalized_rate_to_mdl'] = '0';
        case 'snapshot':
          data['captured_at'] = 'invalid';
      }
      await pumpScreen(tester, latest: () async => jsonResponse(data));
      expect(find.textContaining('Comparison is unavailable'), findsOneWidget);
      expect(find.byType(Card), findsNothing);
    });
  }

  testWidgets('remains usable on a phone-sized display', (tester) async {
    await pumpScreen(tester, size: const Size(390, 844));
    await tester.enterText(
      find.byKey(const Key('comparison-amount')),
      '123.456789012345678901',
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('value-BTC')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(amount(tester, 'BTC'), '30.86');
    expect(tester.takeException(), isNull);
  });

  testWidgets('source currency can be excluded while type filter is applied', (
    tester,
  ) async {
    await pumpScreen(tester);
    expect(find.byKey(const Key('comparison-EUR')), findsNothing);
    expect(find.byKey(const Key('comparison-USD')), findsOneWidget);
    expect(find.byKey(const Key('comparison-BTC')), findsOneWidget);

    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('currency-type-filter')),
        matching: find.text('Crypto'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('comparison-BTC')), findsOneWidget);
    expect(find.byKey(const Key('comparison-USD')), findsNothing);

    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('currency-type-filter')),
        matching: find.text('Fiat'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('comparison-USD')), findsOneWidget);
    expect(find.byKey(const Key('comparison-BTC')), findsNothing);
    expectIn('USD', 'Show more');
  });

  testWidgets('ignores a pending response after disposal', (tester) async {
    final response = Completer<http.Response>();
    await pumpScreen(tester, latest: () => response.future, settle: false);
    await tester.pumpWidget(const SizedBox());
    response.complete(jsonResponse(snapshot()));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}

Future<void> pumpScreen(
  WidgetTester tester, {
  Future<http.Response> Function()? latest,
  List<String>? requests,
  http.Client? client,
  bool settle = true,
  Size size = const Size(1000, 3000),
}) async {
  final fake =
      client ??
      MockClient((request) async {
        requests?.add(request.url.path);
        expect(request.method, 'GET');
        if (request.url.path.endsWith('/currencies')) {
          return jsonResponse(currencies());
        }
        if (request.url.path.endsWith('/rates/latest')) {
          return latest == null ? jsonResponse(snapshot()) : latest();
        }
        fail('Unexpected request ${request.url}');
      });
  addTearDown(fake.close);
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: AllCurrenciesScreen(apiClient: RatesApiClient(client: fake)),
    ),
  );
  if (settle) await tester.pumpAndSettle();
}

String amount(WidgetTester tester, String code) =>
    tester.widget<SelectableText>(find.byKey(Key('value-$code'))).data!;
void expectIn(String code, String label, {bool absent = false}) => expect(
  find.descendant(
    of: find.byKey(Key('comparison-$code')),
    matching: find.text(label),
  ),
  absent ? findsNothing : findsOneWidget,
);
http.Response jsonResponse(Map<String, dynamic> value) =>
    http.Response(jsonEncode(value), 200);
Map<String, dynamic> currencies() => {
  'currencies': [
    for (final entry in [
      ('EUR', 'Euro', 'fiat'),
      ('USD', 'US Dollar', 'fiat'),
      ('BTC', 'Bitcoin', 'crypto'),
      ('MDL', 'Moldovan Leu', 'fiat'),
      ('XXX', 'Unsupported', 'fiat'),
    ])
      {
        'code': entry.$1,
        'name': entry.$2,
        'type': entry.$3,
        'is_supported': entry.$1 != 'XXX',
      },
  ],
};
Map<String, dynamic> snapshot() => {
  'snapshot_id': 'comparison-snapshot',
  'captured_at': capturedAt,
  'rates': <Map<String, dynamic>>[
    for (final entry in [
      ('EUR', '2', 'live', fiatTime),
      ('USD', '4', 'fallback', fallbackTime),
      ('BTC', '8', 'cached', cryptoTime),
      ('MDL', '1', 'live', fiatTime),
    ])
      {
        'currency': entry.$1,
        'normalized_rate_to_mdl': entry.$2,
        'nominal_unit': 1,
        'provider_name': entry.$1 == 'BTC' ? 'CoinGecko' : 'BNM',
        'provider_type': entry.$1 == 'BTC' ? 'crypto' : 'fiat',
        'effective_at': entry.$4,
        'freshness_state': entry.$3,
        'is_fallback': entry.$1 == 'USD',
        'is_stale': entry.$1 == 'BTC',
      },
  ],
};
