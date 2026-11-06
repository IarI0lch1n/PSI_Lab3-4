import 'package:flutter/material.dart';

import '../models/rate_models.dart';

enum CurrencyHubDestination {
  currentRates('Current Rates', Icons.currency_exchange_outlined),
  allCurrencies('All Currencies', Icons.table_chart_outlined),
  converter('Converter', Icons.calculate_outlined),
  analytics('Analytics', Icons.insights_outlined);

  const CurrencyHubDestination(this.label, this.icon);

  final String label;
  final IconData icon;
}

enum CurrencyFilter { all, fiat, crypto }

class CurrencyHubColors {
  const CurrencyHubColors._();

  static const positive = Color(0xFF287A4B);
  static const negative = Color(0xFFB3261E);
  static const neutral = Color(0xFF6D6256);
}

class CurrencyHubTheme {
  const CurrencyHubTheme._();

  static ThemeData get light {
    const accent = Color(0xFFB85C00);
    final scheme =
        ColorScheme.fromSeed(
          seedColor: accent,
          brightness: Brightness.light,
        ).copyWith(
          primary: accent,
          onPrimary: Colors.white,
          surface: const Color(0xFFFFFCF7),
          surfaceContainerLowest: const Color(0xFFFFFFFF),
          surfaceContainerHighest: const Color(0xFFF2EEE6),
          secondary: const Color(0xFF52657A),
          tertiary: const Color(0xFF9A6900),
          error: const Color(0xFFB3261E),
        );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: const Color(0xFFFAF7F1),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        backgroundColor: Color(0xFFFAF7F1),
        foregroundColor: Color(0xFF24211D),
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardThemeData(
        color: scheme.surface,
        elevation: 0,
        margin: const EdgeInsets.symmetric(vertical: 6),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: Color(0xFFE9E2D6)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE1D9CC)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE1D9CC)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: accent, width: 1.5),
        ),
      ),
    );
  }
}

class CurrencyHubScaffold extends StatelessWidget {
  const CurrencyHubScaffold({
    required this.title,
    required this.destination,
    required this.onDestinationSelected,
    required this.body,
    super.key,
  });

  final String title;
  final CurrencyHubDestination destination;
  final ValueChanged<CurrencyHubDestination> onDestinationSelected;
  final Widget body;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title)),
    drawer: NavigationDrawer(
      selectedIndex: destination.index,
      onDestinationSelected: (index) {
        Navigator.of(context).pop();
        onDestinationSelected(CurrencyHubDestination.values[index]);
      },
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(28, 16, 16, 20),
          child: Row(
            children: [
              Icon(
                Icons.currency_exchange,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'CurrencyHub',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
        ),
        for (final item in CurrencyHubDestination.values)
          NavigationDrawerDestination(
            icon: Icon(item.icon),
            selectedIcon: Icon(item.icon),
            label: Text(item.label),
          ),
      ],
    ),
    body: SafeArea(child: body),
  );
}

class CurrencyTypeFilter extends StatelessWidget {
  const CurrencyTypeFilter({
    required this.value,
    required this.onChanged,
    super.key,
  });

  final CurrencyFilter value;
  final ValueChanged<CurrencyFilter> onChanged;

  @override
  Widget build(BuildContext context) => SegmentedButton<CurrencyFilter>(
    key: const Key('currency-type-filter'),
    showSelectedIcon: false,
    segments: const [
      ButtonSegment(value: CurrencyFilter.all, label: Text('All')),
      ButtonSegment(value: CurrencyFilter.fiat, label: Text('Fiat')),
      ButtonSegment(value: CurrencyFilter.crypto, label: Text('Crypto')),
    ],
    selected: {value},
    onSelectionChanged: (selection) => onChanged(selection.first),
  );
}

class CurrencyTypeBadge extends StatelessWidget {
  const CurrencyTypeBadge({required this.type, super.key});

  final CurrencyType type;

  @override
  Widget build(BuildContext context) {
    final color = switch (type) {
      CurrencyType.fiat => Theme.of(context).colorScheme.secondaryContainer,
      CurrencyType.crypto => Theme.of(context).colorScheme.tertiaryContainer,
    };
    return _StatusBadge(
      label: type == CurrencyType.fiat ? 'Fiat' : 'Crypto',
      backgroundColor: color,
    );
  }
}

class FreshnessBadges extends StatelessWidget {
  const FreshnessBadges({required this.rate, super.key, this.prefix});

  final RateProvenance rate;
  final String? prefix;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (label, color) = switch (rate.freshnessState) {
      FreshnessState.live => ('Live', const Color(0xFFE1F2E7)),
      FreshnessState.fallback => ('Fallback', const Color(0xFFFFEDC2)),
      FreshnessState.cached => ('Cached', scheme.secondaryContainer),
    };

    return Wrap(
      spacing: 6,
      runSpacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if (prefix != null)
          Text(prefix!, style: Theme.of(context).textTheme.labelMedium),
        _StatusBadge(label: label, backgroundColor: color),
        if (rate.isFallback)
          const _StatusBadge(
            label: 'Fallback used',
            backgroundColor: Color(0xFFFFEDC2),
          ),
        if (rate.isStale)
          _StatusBadge(
            label: 'Stale',
            backgroundColor: scheme.errorContainer,
            foregroundColor: scheme.onErrorContainer,
          ),
      ],
    );
  }
}

class ExpandableDetails extends StatefulWidget {
  const ExpandableDetails({
    required this.children,
    super.key,
    this.showMoreLabel = 'Show more',
    this.showLessLabel = 'Show less',
  });

  final List<Widget> children;
  final String showMoreLabel;
  final String showLessLabel;

  @override
  State<ExpandableDetails> createState() => _ExpandableDetailsState();
}

class _ExpandableDetailsState extends State<ExpandableDetails> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      TextButton.icon(
        key: const Key('expand-details'),
        onPressed: () => setState(() => _expanded = !_expanded),
        icon: Icon(_expanded ? Icons.expand_less : Icons.expand_more, size: 20),
        label: Text(_expanded ? widget.showLessLabel : widget.showMoreLabel),
        style: TextButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          minimumSize: const Size(0, 40),
        ),
      ),
      if (_expanded) ...widget.children,
    ],
  );
}

class ProvenanceLine extends StatelessWidget {
  const ProvenanceLine({required this.label, required this.value, super.key});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Wrap(
      spacing: 6,
      children: [
        Text('$label:', style: Theme.of(context).textTheme.labelLarge),
        SelectableText(value),
      ],
    ),
  );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.label,
    required this.backgroundColor,
    this.foregroundColor,
  });

  final String label;
  final Color backgroundColor;
  final Color? foregroundColor;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: backgroundColor,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: Theme.of(context).textTheme.labelMedium?.copyWith(
        color: foregroundColor ?? Theme.of(context).colorScheme.onSurface,
        fontWeight: FontWeight.w600,
      ),
    ),
  );
}
