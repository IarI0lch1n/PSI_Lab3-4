import 'dart:async';
import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/features/rates/presentation/current_rates_screen.dart';
import 'package:currencyhub_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _capturedAt = '2026-10-28T12:00:00Z';
const _usdEffectiveAt = '2026-10-28T09:00:00Z';
const _ronEffectiveAt = '2026-10-27T00:00:00+02:00';
const _btcEffectiveAt = '2026-10-28T11:45:00Z';

void main() {
  testWidgets('shows loading until both requests complete', (tester) async {
    final currenciesResponse = Completer<http.Response>();
    final ratesResponse = Completer<http.Response>();
    final client = MockClient((request) {
      return request.url.path.endsWith('/currencies')
          ? currenciesResponse.future
          : ratesResponse.future;
    });
    final apiClient = RatesApiClient(client: client);
    addTearDown(client.close);
    await _setLargeTestSurface(tester);

    await tester.pumpWidget(_screen(apiClient));

    expect(find.text('Loading current rates…'), findsOneWidget);
    expect(find.text('17.40'), findsNothing);
    expect(find.byType(Card), findsNothing);

    currenciesResponse.complete(_jsonResponse(_currenciesJson()));
    ratesResponse.complete(_jsonResponse(_snapshotJson()));
    await tester.pumpAndSettle();

    expect(find.text('Loading current rates…'), findsNothing);
    expect(find.text('17.40'), findsOneWidget);
  });

  testWidgets('keeps rate metadata collapsed and freshness visible', (
    tester,
  ) async {
    await _pumpScreen(tester);

    final usdCard = _cardFor(tester, 'USD');
    expect(_textIn(usdCard), contains('US Dollar'));
    expect(_textIn(usdCard), contains('Fiat'));
    expect(_textIn(usdCard), contains('17.40'));
    expect(_textIn(usdCard), isNot(contains('BNM')));
    expect(_textIn(usdCard), isNot(contains(_usdEffectiveAt)));
    expect(_textIn(usdCard), contains('Live'));
    expect(_textIn(usdCard), contains('Show more'));

    final ronCard = _cardFor(tester, 'RON');
    expect(_textIn(ronCard), contains('Romanian Leu'));
    expect(_textIn(ronCard), contains('Fiat'));
    expect(_textIn(ronCard), contains('Fallback'));
    expect(_textIn(ronCard), contains('Fallback used'));

    final btcCard = _cardFor(tester, 'BTC');
    expect(_textIn(btcCard), contains('Bitcoin'));
    expect(_textIn(btcCard), contains('Crypto'));
    expect(_textIn(btcCard), contains('Cached'));
    expect(_textIn(btcCard), contains('Stale'));

    await tester.tap(
      find.descendant(of: usdCard, matching: find.text('Show more')),
    );
    await tester.pumpAndSettle();
    expect(_textIn(usdCard), contains('BNM'));
    expect(_textIn(usdCard), contains(_usdEffectiveAt));
    expect(_textIn(usdCard), contains('Show less'));
  });

  testWidgets('excludes MDL while keeping other current rates visible', (
    tester,
  ) async {
    await _pumpScreen(tester);

    expect(find.byKey(const Key('rate-MDL')), findsNothing);
    expect(find.byKey(const Key('rate-USD')), findsOneWidget);
    expect(find.byKey(const Key('rate-RON')), findsOneWidget);
    expect(find.byKey(const Key('rate-BTC')), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('current-rates-search')),
      'mdl',
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-MDL')), findsNothing);
    expect(find.text('No currencies match your search.'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('current-rates-search')), '');
    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('currency-type-filter')),
        matching: find.text('Fiat'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-MDL')), findsNothing);
    expect(find.byKey(const Key('rate-USD')), findsOneWidget);
    expect(find.byKey(const Key('rate-RON')), findsOneWidget);
    expect(find.byKey(const Key('rate-BTC')), findsNothing);
  });

  testWidgets('shows snapshot collection separately from original rate times', (
    tester,
  ) async {
    await _pumpScreen(tester);

    expect(find.text('Snapshot collected'), findsOneWidget);
    expect(find.text(_capturedAt), findsOneWidget);
    for (final code in ['USD', 'RON', 'BTC']) {
      final card = _cardFor(tester, code);
      expect(
        find.descendant(of: card, matching: find.text(_capturedAt)),
        findsNothing,
      );
      expect(
        find.descendant(of: card, matching: find.textContaining('effective')),
        findsNothing,
      );
    }
  });

  testWidgets('shows fallback and stale flags independently per rate card', (
    tester,
  ) async {
    await _pumpScreen(tester);

    final usdCard = _cardFor(tester, 'USD');
    expect(_textIn(usdCard), contains('Live'));
    expect(_textIn(usdCard), isNot(contains('Fallback used')));
    expect(_textIn(usdCard), isNot(contains('Stale')));

    final ronCard = _cardFor(tester, 'RON');
    expect(_textIn(ronCard), contains('Fallback'));
    expect(_textIn(ronCard), contains('Fallback used'));
    expect(_textIn(ronCard), isNot(contains('Stale')));

    final btcCard = _cardFor(tester, 'BTC');
    expect(_textIn(btcCard), contains('Cached'));
    expect(_textIn(btcCard), contains('Stale'));
    expect(_textIn(btcCard), isNot(contains('Fallback used')));
  });

  testWidgets('does not infer booleans from cached freshness state', (
    tester,
  ) async {
    final snapshot = _snapshotJson()
      ..['rates'] = [
        _rateJson(
          currency: 'BTC',
          providerName: 'CoinGecko',
          providerType: 'crypto',
          effectiveAt: _btcEffectiveAt,
          freshnessState: 'cached',
          isFallback: false,
          isStale: false,
          normalizedRate: '542240.10',
        ),
      ];
    await _pumpScreen(tester, snapshot: snapshot);

    final btcCard = _cardFor(tester, 'BTC');
    expect(_textIn(btcCard), contains('Cached'));
    expect(_textIn(btcCard), isNot(contains('Fallback used')));
    expect(_textIn(btcCard), isNot(contains('Stale')));
  });

  testWidgets('shows a safe error and retries both GET endpoints', (
    tester,
  ) async {
    final requestCounts = <String, int>{};
    final client = MockClient((request) async {
      final endpoint = request.url.path.split('/').last;
      final count = (requestCounts[endpoint] ?? 0) + 1;
      requestCounts[endpoint] = count;

      if (endpoint == 'currencies' && count == 1) {
        return http.Response('internal server details', 503);
      }
      return endpoint == 'currencies'
          ? _jsonResponse(_currenciesJson())
          : _jsonResponse(_snapshotJson());
    });
    final apiClient = RatesApiClient(client: client);
    addTearDown(client.close);
    await _setLargeTestSurface(tester);

    await tester.pumpWidget(_screen(apiClient));
    await tester.pumpAndSettle();

    expect(find.text('Current rates are unavailable.'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
    expect(find.textContaining('internal server details'), findsNothing);
    expect(find.textContaining('10.0.2.2'), findsNothing);

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(requestCounts['currencies'], 2);
    expect(requestCounts['latest'], 2);
    expect(find.text('17.40'), findsOneWidget);
    expect(find.text('Current rates are unavailable.'), findsNothing);
  });

  testWidgets('rejects a rate without supported currency metadata', (
    tester,
  ) async {
    final snapshot = _snapshotJson()
      ..['rates'] = [
        ...(_snapshotJson()['rates'] as List<dynamic>),
        _rateJson(
          currency: 'ETH',
          providerName: 'CoinGecko',
          providerType: 'crypto',
          effectiveAt: _btcEffectiveAt,
          freshnessState: 'live',
          isFallback: false,
          isStale: false,
          normalizedRate: '90000',
        ),
      ];
    await _pumpScreen(tester, snapshot: snapshot);

    expect(find.text('Current rates are unavailable.'), findsOneWidget);
    expect(find.byType(Card), findsNothing);
    expect(find.text('US Dollar'), findsNothing);
  });

  testWidgets('shows unavailable state for an empty snapshot', (tester) async {
    final snapshot = _snapshotJson()..['rates'] = <dynamic>[];
    await _pumpScreen(tester, snapshot: snapshot);

    expect(find.text('Current rates are unavailable.'), findsOneWidget);
    expect(find.byType(Card), findsNothing);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('search matches currency code and name locally', (tester) async {
    final requests = <String>[];
    await _pumpScreen(tester, requests: requests);

    await tester.enterText(
      find.byKey(const Key('current-rates-search')),
      'eur',
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-USD')), findsNothing);
    expect(find.byKey(const Key('rate-RON')), findsNothing);
    expect(find.byKey(const Key('rate-BTC')), findsNothing);
    expect(find.text('No currencies match your search.'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('current-rates-search')),
      'btc',
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-BTC')), findsOneWidget);
    expect(find.byKey(const Key('rate-USD')), findsNothing);
    await tester.enterText(
      find.byKey(const Key('current-rates-search')),
      '  bitcoin  ',
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-BTC')), findsOneWidget);
    expect(find.byKey(const Key('rate-RON')), findsNothing);
    expect(requests, hasLength(2));
  });

  testWidgets('filters by type and combines type with search', (tester) async {
    await _pumpScreen(tester);

    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('currency-type-filter')),
        matching: find.text('Crypto'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-BTC')), findsOneWidget);
    expect(find.byKey(const Key('rate-USD')), findsNothing);
    expect(find.byKey(const Key('rate-RON')), findsNothing);

    await tester.enterText(find.byKey(const Key('current-rates-search')), 'a');
    await tester.pumpAndSettle();
    expect(find.text('No currencies match your search.'), findsOneWidget);
    expect(find.byKey(const Key('rate-BTC')), findsNothing);

    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('currency-type-filter')),
        matching: find.text('Fiat'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('rate-RON')), findsOneWidget);
    expect(find.byKey(const Key('rate-USD')), findsOneWidget);
    expect(find.byKey(const Key('rate-BTC')), findsNothing);
  });
}

Widget _screen(RatesApiClient apiClient) {
  return MaterialApp(
    locale: const Locale('en'),
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: CurrentRatesScreen(apiClient: apiClient),
  );
}

Future<void> _pumpScreen(
  WidgetTester tester, {
  Map<String, dynamic>? snapshot,
  List<String>? requests,
}) async {
  final client = MockClient((request) async {
    requests?.add(request.url.path);
    if (request.url.path.endsWith('/currencies')) {
      return _jsonResponse(_currenciesJson());
    }
    return _jsonResponse(snapshot ?? _snapshotJson());
  });
  addTearDown(client.close);
  await _setLargeTestSurface(tester);

  await tester.pumpWidget(_screen(RatesApiClient(client: client)));
  await tester.pumpAndSettle();
}

Future<void> _setLargeTestSurface(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1000, 3000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Finder _cardFor(WidgetTester tester, String currency) {
  return find
      .ancestor(of: find.text(currency), matching: find.byType(Card))
      .first;
}

String _textIn(Finder subtree) {
  final textWidgets = find
      .descendant(
        of: subtree,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Text || widget is SelectableText || widget is RichText,
        ),
      )
      .evaluate();
  return textWidgets
      .map((element) {
        final widget = element.widget;
        if (widget is Text) {
          return widget.data ?? '';
        }
        if (widget is SelectableText) {
          return widget.data ?? '';
        }
        if (widget is RichText) {
          return widget.text.toPlainText();
        }
        return '';
      })
      .join(' ');
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
        'code': 'MDL',
        'name': 'Moldovan Leu',
        'type': 'fiat',
        'is_supported': true,
      },
      {
        'code': 'RON',
        'name': 'Romanian Leu',
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

Map<String, dynamic> _snapshotJson() {
  return {
    'snapshot_id': 'snapshot-2026-10-28',
    'captured_at': _capturedAt,
    'rates': [
      _rateJson(
        currency: 'USD',
        providerName: 'BNM',
        providerType: 'fiat',
        effectiveAt: _usdEffectiveAt,
        freshnessState: 'live',
        isFallback: false,
        isStale: false,
        normalizedRate: '17.400000000000000001',
      ),
      _rateJson(
        currency: 'MDL',
        providerName: 'BNM',
        providerType: 'fiat',
        effectiveAt: _usdEffectiveAt,
        freshnessState: 'live',
        isFallback: false,
        isStale: false,
        normalizedRate: '1',
      ),
      _rateJson(
        currency: 'RON',
        providerName: 'BNM',
        providerType: 'fiat',
        effectiveAt: _ronEffectiveAt,
        freshnessState: 'fallback',
        isFallback: true,
        isStale: false,
        normalizedRate: '3.912345678901234567',
        nominalUnit: 100,
      ),
      _rateJson(
        currency: 'BTC',
        providerName: 'CoinGecko',
        providerType: 'crypto',
        effectiveAt: _btcEffectiveAt,
        freshnessState: 'cached',
        isFallback: false,
        isStale: true,
        normalizedRate: '542240.10',
      ),
    ],
  };
}

Map<String, dynamic> _rateJson({
  required String currency,
  required String providerName,
  required String providerType,
  required String effectiveAt,
  required String freshnessState,
  required bool isFallback,
  required bool isStale,
  required String normalizedRate,
  int nominalUnit = 1,
}) {
  return {
    'currency': currency,
    'normalized_rate_to_mdl': normalizedRate,
    'nominal_unit': nominalUnit,
    'provider_name': providerName,
    'provider_type': providerType,
    'effective_at': effectiveAt,
    'freshness_state': freshnessState,
    'is_fallback': isFallback,
    'is_stale': isStale,
  };
}
