import 'package:flutter_test/flutter_test.dart';

import 'package:currencyhub_mobile/main.dart';

void main() {
  testWidgets('builds the CurrencyHub app and shows its title', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const CurrencyHubApp());

    expect(find.byType(CurrencyHubApp), findsOneWidget);
    expect(find.text('CurrencyHub'), findsOneWidget);
  });
}
