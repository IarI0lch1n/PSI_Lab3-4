import 'dart:async';
import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/features/analytics/presentation/analytics_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('shows loading until history and analytics both complete', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    await pumpScreen(
      tester,
      historyResponse: (_) => pending.future,
      settle: false,
    );
    await tester.pump();
    expect(find.text('Loading historical analytics...'), findsOneWidget);
    expect(find.byKey(const Key('analytics-metrics')), findsNothing);
    pending.complete(jsonResponse(historyPayload()));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('analytics-metrics')), findsOneWidget);
  });

  testWidgets('renders exact metrics and aggregate provenance counts', (
    tester,
  ) async {
    await pumpScreen(tester);

    expect(find.text('0.0000318'), findsWidgets);
    expect(find.text('0.0000330'), findsWidgets);
    expect(find.text('0.0000324'), findsOneWidget);
    expect(find.text('0.0000012'), findsOneWidget);
    expect(find.text('1.26%'), findsOneWidget);
    expect(find.text('Growth'), findsOneWidget);
    expect(find.text('Base providers: BNM, Backup BNM'), findsOneWidget);
    expect(find.text('Quote providers: CoinGecko'), findsOneWidget);
    expect(find.text('Live entries: 2'), findsOneWidget);
    expect(find.text('Fallback entries: 1'), findsOneWidget);
    expect(find.text('Cached entries: 1'), findsOneWidget);
    expect(find.text('Stale entries: 1'), findsOneWidget);
    expect(find.text('Fallback used: 1'), findsOneWidget);
  });

  testWidgets(
    'keeps live fallback cached stale and flags independent per leg',
    (tester) async {
      await pumpScreen(tester);

      expectInLeg('Base', 'EUR', 'BNM');
      expectInLeg('Base', 'EUR', 'Live');
      expectInLeg('Base', 'EUR', 'Fallback used', absent: true);
      expectInLeg('Base', 'EUR', 'Stale', absent: true);
      expectInLeg('Quote', 'BTC', 'CoinGecko');
      expectInLeg('Quote', 'BTC', 'Cached');
      expectInLeg('Quote', 'BTC', 'Stale');
      expectInLeg('Quote', 'BTC', 'Fallback used', absent: true);

      await tester.scrollUntilVisible(
        find.text('Backup BNM'),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      final fallbackLeg = find
          .ancestor(of: find.text('Backup BNM'), matching: find.byType(Column))
          .first;
      expect(
        find.descendant(of: fallbackLeg, matching: find.text('Fallback')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: fallbackLeg, matching: find.text('Fallback used')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: fallbackLeg, matching: find.text('Stale')),
        findsNothing,
      );
    },
  );

  testWidgets('switches from 7-day to 30-day API requests', (tester) async {
    final requests = <Uri>[];
    await pumpScreen(tester, requests: requests);
    await tester.tap(find.text('30 days'));
    await tester.pumpAndSettle();

    final historyRequests = requests
        .where((uri) => uri.path.endsWith('/history'))
        .toList();
    final analyticsRequests = requests
        .where((uri) => uri.path.endsWith('/analytics'))
        .toList();
    expect(historyRequests.map((uri) => uri.queryParameters['period']), [
      '7d',
      '30d',
    ]);
    expect(analyticsRequests.map((uri) => uri.queryParameters['period']), [
      '7d',
      '30d',
    ]);
    expect(find.text('30 days'), findsOneWidget);
    expect(find.byKey(const Key('analytics-metrics')), findsOneWidget);
  });

  testWidgets('shows an explicit empty state without metrics or point cards', (
    tester,
  ) async {
    await pumpScreen(tester, empty: true);

    expect(
      find.text(
        'No historical data available for this pair in the selected period.',
      ),
      findsOneWidget,
    );
    expect(find.byKey(const Key('analytics-empty')), findsOneWidget);
    expect(find.byKey(const Key('analytics-metrics')), findsNothing);
    expect(find.byType(Card), findsNothing);
  });

  for (final failingPath in ['/currencies', '/history', '/analytics']) {
    testWidgets('shows a safe error and retries after $failingPath fails', (
      tester,
    ) async {
      var fail = true;
      await pumpScreen(
        tester,
        client: MockClient((request) async {
          if (fail && request.url.path.endsWith(failingPath)) {
            return http.Response('private provider detail', 503);
          }
          return responseFor(request.url);
        }),
      );
      expect(find.text('Analytics are unavailable.'), findsOneWidget);
      expect(find.textContaining('private provider detail'), findsNothing);
      fail = false;
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('analytics-metrics')), findsOneWidget);
    });
  }

  testWidgets('rejects mismatched aggregate counts as unavailable', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      analyticsResponse: (period) async {
        final payload = analyticsPayload(period: period);
        final summary = payload['provenance_summary'] as Map<String, dynamic>;
        summary['rate_entry_freshness_counts'] = {
          'live': 99,
          'fallback': 1,
          'cached': 1,
        };
        return jsonResponse(payload);
      },
    );

    expect(find.text('Analytics are unavailable.'), findsOneWidget);
    expect(find.byType(Card), findsNothing);
  });

  testWidgets('remains scrollable on a phone-sized display', (tester) async {
    await pumpScreen(tester, size: const Size(390, 844));
    await tester.scrollUntilVisible(
      find.text('Snapshot snapshot-28'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Snapshot snapshot-28'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('ignores pending responses after disposal', (tester) async {
    final pending = Completer<http.Response>();
    await pumpScreen(
      tester,
      historyResponse: (_) => pending.future,
      settle: false,
    );
    await tester.pumpWidget(const SizedBox());
    pending.complete(jsonResponse(historyPayload()));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}

Future<void> pumpScreen(
  WidgetTester tester, {
  List<Uri>? requests,
  http.Client? client,
  Future<http.Response> Function(String period)? historyResponse,
  Future<http.Response> Function(String period)? analyticsResponse,
  bool empty = false,
  bool settle = true,
  Size size = const Size(1000, 3000),
}) async {
  final fake =
      client ??
      MockClient((request) async {
        requests?.add(request.url);
        final period = request.url.queryParameters['period'] ?? '7d';
        if (request.url.path.endsWith('/history') && historyResponse != null) {
          return historyResponse(period);
        }
        if (request.url.path.endsWith('/analytics') &&
            analyticsResponse != null) {
          return analyticsResponse(period);
        }
        return responseFor(request.url, empty: empty);
      });
  addTearDown(fake.close);
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      home: AnalyticsScreen(apiClient: RatesApiClient(client: fake)),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  }
}

http.Response responseFor(Uri uri, {bool empty = false}) {
  final period = uri.queryParameters['period'] ?? '7d';
  if (uri.path.endsWith('/currencies')) {
    return jsonResponse(currenciesPayload());
  }
  if (uri.path.endsWith('/history')) {
    return jsonResponse(historyPayload(period: period, empty: empty));
  }
  if (uri.path.endsWith('/analytics')) {
    return jsonResponse(analyticsPayload(period: period, empty: empty));
  }
  return http.Response('unexpected', 404);
}

http.Response jsonResponse(Map<String, dynamic> payload) =>
    http.Response(jsonEncode(payload), 200);

Map<String, dynamic> currenciesPayload() => {
  'currencies': [
    {'code': 'EUR', 'name': 'Euro', 'type': 'fiat', 'is_supported': true},
    {'code': 'USD', 'name': 'US Dollar', 'type': 'fiat', 'is_supported': true},
    {'code': 'BTC', 'name': 'Bitcoin', 'type': 'crypto', 'is_supported': true},
    {
      'code': 'XXX',
      'name': 'Unsupported',
      'type': 'fiat',
      'is_supported': false,
    },
  ],
};

Map<String, dynamic> historyPayload({
  String period = '7d',
  bool empty = false,
}) => {
  'base_currency': 'EUR',
  'quote_currency': 'BTC',
  'period': period,
  'points': empty
      ? <dynamic>[]
      : [
          historyPoint(
            date: '2026-10-27',
            value: '0.0000318',
            snapshot: 'snapshot-27',
            sourceProvider: 'BNM',
            sourceFreshness: 'live',
            targetFreshness: 'cached',
            targetStale: true,
          ),
          historyPoint(
            date: '2026-10-28',
            value: '0.0000330',
            snapshot: 'snapshot-28',
            sourceProvider: 'Backup BNM',
            sourceFreshness: 'fallback',
            sourceFallback: true,
            targetFreshness: 'live',
          ),
        ],
  'empty': empty,
  if (empty)
    'message':
        'No historical data available for this pair in the selected period.',
};

Map<String, dynamic> analyticsPayload({
  String period = '7d',
  bool empty = false,
}) => {
  'base_currency': 'EUR',
  'quote_currency': 'BTC',
  'period': period,
  'points': empty
      ? <dynamic>[]
      : [
          {'date': '2026-10-27', 'value': '0.0000318'},
          {'date': '2026-10-28', 'value': '0.0000330'},
        ],
  if (!empty) ...{
    'minimum': '0.0000318',
    'maximum': '0.0000330',
    'average': '0.0000324',
    'absolute_change': '0.0000012',
    'percentage_change': '1.26',
    'trend': 'GROWTH',
  },
  'provenance_summary': {
    'point_count': empty ? 0 : 2,
    'source_providers': empty ? <dynamic>[] : ['BNM', 'Backup BNM'],
    'target_providers': empty ? <dynamic>[] : ['CoinGecko'],
    'rate_entry_freshness_counts': {
      'live': empty ? 0 : 2,
      'fallback': empty ? 0 : 1,
      'cached': empty ? 0 : 1,
    },
    'stale_entry_count': empty ? 0 : 1,
    'fallback_entry_count': empty ? 0 : 1,
  },
  'empty': empty,
  if (empty)
    'message':
        'No historical data available for this pair in the selected period.',
};

Map<String, dynamic> historyPoint({
  required String date,
  required String value,
  required String snapshot,
  required String sourceProvider,
  required String sourceFreshness,
  required String targetFreshness,
  bool sourceFallback = false,
  bool targetStale = false,
}) => {
  'date': date,
  'value': value,
  'rate_context': {
    'source_rate': {
      'currency': 'EUR',
      'provider_name': sourceProvider,
      'effective_at': '2026-10-25T09:00:00Z',
      'freshness_state': sourceFreshness,
      'is_fallback': sourceFallback,
      'is_stale': false,
    },
    'target_rate': {
      'currency': 'BTC',
      'provider_name': 'CoinGecko',
      'effective_at': '${date}T11:45:00Z',
      'freshness_state': targetFreshness,
      'is_fallback': false,
      'is_stale': targetStale,
    },
    'snapshot_id': snapshot,
  },
};

void expectInLeg(
  String label,
  String currency,
  String text, {
  bool absent = false,
}) {
  final leg = find.byKey(ValueKey('analytics-leg-$label-$currency')).first;
  expect(
    find.descendant(of: leg, matching: find.text(text)),
    absent ? findsNothing : findsOneWidget,
  );
}
