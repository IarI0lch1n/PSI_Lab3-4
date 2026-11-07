import 'dart:async';

import 'package:flutter/material.dart';

import 'currency_hub_locale_controller.dart';
import '../../l10n/app_localizations.dart';
import '../models/rate_models.dart';

enum CurrencyHubDestination {
  currentRates(Icons.currency_exchange_outlined),
  allCurrencies(Icons.table_chart_outlined),
  converter(Icons.calculate_outlined),
  analytics(Icons.insights_outlined);

  const CurrencyHubDestination(this.icon);

  final IconData icon;

  String label(AppLocalizations l10n) => switch (this) {
    CurrencyHubDestination.currentRates => l10n.navCurrentRates,
    CurrencyHubDestination.allCurrencies => l10n.navAllCurrencies,
    CurrencyHubDestination.converter => l10n.navConverter,
    CurrencyHubDestination.analytics => l10n.navAnalytics,
  };
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
                  AppLocalizations.of(context)!.appName,
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
            label: Text(item.label(AppLocalizations.of(context)!)),
          ),
        const SizedBox(height: 24),
        const CurrencyHubLanguageSelector(),
      ],
    ),
    body: SafeArea(child: body),
  );
}

class CurrencyHubLanguageSelector extends StatelessWidget {
  const CurrencyHubLanguageSelector({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final activeLanguage = _languageName(
      l10n,
      Localizations.localeOf(context).languageCode,
    );
    final controller = CurrencyHubLocaleScope.maybeOf(context);

    return ListTile(
      key: const Key('language-selector'),
      leading: const Icon(Icons.language),
      title: Text(l10n.language),
      trailing: PopupMenuButton<Locale>(
        tooltip: l10n.language,
        onSelected: (locale) {
          if (controller != null) {
            unawaited(_saveLocale(context, controller, locale));
          }
        },
        itemBuilder: (context) => [
          for (final locale in CurrencyHubLocaleController.supportedLocales)
            PopupMenuItem(
              value: locale,
              child: Row(
                children: [
                  Expanded(
                    child: Text(_languageName(l10n, locale.languageCode)),
                  ),
                  if (locale.languageCode ==
                      Localizations.localeOf(context).languageCode)
                    const Icon(Icons.check, size: 18),
                ],
              ),
            ),
        ],
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(activeLanguage),
            const SizedBox(width: 4),
            const Icon(Icons.arrow_drop_down),
          ],
        ),
      ),
    );
  }

  String _languageName(AppLocalizations l10n, String languageCode) =>
      switch (languageCode) {
        'ro' => l10n.languageRomanian,
        'ru' => l10n.languageRussian,
        _ => l10n.languageEnglish,
      };

  Future<void> _saveLocale(
    BuildContext context,
    CurrencyHubLocaleController controller,
    Locale locale,
  ) async {
    try {
      await controller.setLocale(locale);
    } on Exception catch (error, stackTrace) {
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          stack: stackTrace,
          library: 'CurrencyHub localization',
          context: ErrorDescription('while saving the selected language'),
        ),
      );
      if (!context.mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context)!.languageSaveFailed),
        ),
      );
    }
  }
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
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SegmentedButton<CurrencyFilter>(
      key: const Key('currency-type-filter'),
      showSelectedIcon: false,
      segments: [
        ButtonSegment(value: CurrencyFilter.all, label: Text(l10n.filterAll)),
        ButtonSegment(value: CurrencyFilter.fiat, label: Text(l10n.filterFiat)),
        ButtonSegment(
          value: CurrencyFilter.crypto,
          label: Text(l10n.filterCrypto),
        ),
      ],
      selected: {value},
      onSelectionChanged: (selection) => onChanged(selection.first),
    );
  }
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
    final l10n = AppLocalizations.of(context)!;
    return _StatusBadge(
      label: type == CurrencyType.fiat ? l10n.filterFiat : l10n.filterCrypto,
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
    final l10n = AppLocalizations.of(context)!;
    final (label, color) = switch (rate.freshnessState) {
      FreshnessState.live => (l10n.freshnessLive, const Color(0xFFE1F2E7)),
      FreshnessState.fallback => (
        l10n.freshnessFallback,
        const Color(0xFFFFEDC2),
      ),
      FreshnessState.cached => (
        l10n.freshnessCached,
        scheme.secondaryContainer,
      ),
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
          _StatusBadge(
            label: l10n.fallbackUsed,
            backgroundColor: const Color(0xFFFFEDC2),
          ),
        if (rate.isStale)
          _StatusBadge(
            label: l10n.freshnessStale,
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
    this.showMoreLabel,
    this.showLessLabel,
  });

  final List<Widget> children;
  final String? showMoreLabel;
  final String? showLessLabel;

  @override
  State<ExpandableDetails> createState() => _ExpandableDetailsState();
}

class _ExpandableDetailsState extends State<ExpandableDetails> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextButton.icon(
          key: const Key('expand-details'),
          onPressed: () => setState(() => _expanded = !_expanded),
          icon: Icon(
            _expanded ? Icons.expand_less : Icons.expand_more,
            size: 20,
          ),
          label: Text(
            _expanded
                ? widget.showLessLabel ?? l10n.showLess
                : widget.showMoreLabel ?? l10n.showMore,
          ),
          style: TextButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            minimumSize: const Size(0, 40),
          ),
        ),
        if (_expanded) ...widget.children,
      ],
    );
  }
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
