import 'package:flutter/material.dart';

void main() {
  runApp(const CurrencyHubApp());
}

class CurrencyHubApp extends StatelessWidget {
  const CurrencyHubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CurrencyHub',
      home: Scaffold(
        body: Center(
          child: Text(
            'CurrencyHub',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
        ),
      ),
    );
  }
}
