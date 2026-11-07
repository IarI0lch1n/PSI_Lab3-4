import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../models/rate_models.dart';

class SearchableCurrencyPicker extends StatefulWidget {
  const SearchableCurrencyPicker({
    required this.currencies,
    required this.value,
    required this.label,
    required this.onChanged,
    super.key,
    this.enabled = true,
    this.fieldId,
  });

  final List<CurrencyModel> currencies;
  final String? value;
  final String label;
  final ValueChanged<String?> onChanged;
  final bool enabled;
  final String? fieldId;

  @override
  State<SearchableCurrencyPicker> createState() =>
      _SearchableCurrencyPickerState();
}

class _SearchableCurrencyPickerState extends State<SearchableCurrencyPicker> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _editing = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: _displayForCode(widget.value));
    _focusNode = FocusNode();
  }

  @override
  void didUpdateWidget(covariant SearchableCurrencyPicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value && !_editing) {
      _controller.text = _displayForCode(widget.value);
    }
    if (widget.value != null) {
      _editing = false;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  String _display(CurrencyModel currency) =>
      '${currency.code} — ${currency.name}';

  String _displayForCode(String? code) {
    if (code == null) return '';
    for (final currency in widget.currencies) {
      if (currency.code == code) return _display(currency);
    }
    return '';
  }

  void _onTextChanged(String text) {
    setState(() => _editing = true);
    final selectedText = _displayForCode(widget.value);
    if (widget.value != null && text != selectedText) {
      widget.onChanged(null);
    }
  }

  bool get _hasNoMatches {
    if (!widget.enabled || !_editing) return false;
    final query = _controller.text.trim().toLowerCase();
    return query.isNotEmpty &&
        !widget.currencies.any(
          (currency) =>
              currency.code.toLowerCase().contains(query) ||
              currency.name.toLowerCase().contains(query),
        );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        RawAutocomplete<CurrencyModel>(
          textEditingController: _controller,
          focusNode: _focusNode,
          displayStringForOption: _display,
          optionsBuilder: (value) {
            if (!widget.enabled) return const <CurrencyModel>[];
            final query = value.text.trim().toLowerCase();
            if (query.isEmpty ||
                query == _displayForCode(widget.value).trim().toLowerCase()) {
              return widget.currencies;
            }
            return widget.currencies.where(
              (currency) =>
                  currency.code.toLowerCase().contains(query) ||
                  currency.name.toLowerCase().contains(query),
            );
          },
          onSelected: (currency) {
            _editing = false;
            widget.onChanged(currency.code);
          },
          fieldViewBuilder:
              (context, controller, focusNode, onFieldSubmitted) => TextField(
                key: Key(
                  'currency-picker-${widget.fieldId ?? widget.label.toLowerCase().replaceAll(' ', '-')}',
                ),
                controller: controller,
                focusNode: focusNode,
                enabled: widget.enabled,
                onChanged: _onTextChanged,
                onSubmitted: (_) => onFieldSubmitted(),
                decoration: InputDecoration(
                  labelText: widget.label,
                  hintText: l10n.searchCodeOrName,
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: widget.value == null && controller.text.isNotEmpty
                      ? IconButton(
                          tooltip: l10n.clearSearch,
                          onPressed: () {
                            controller.clear();
                            _onTextChanged('');
                          },
                          icon: const Icon(Icons.close),
                        )
                      : null,
                ),
              ),
          optionsViewBuilder: (context, onSelected, options) {
            final matches = options.toList(growable: false);
            return Align(
              alignment: Alignment.topLeft,
              child: Material(
                elevation: 4,
                borderRadius: BorderRadius.circular(12),
                clipBehavior: Clip.antiAlias,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxHeight: 240,
                    maxWidth: 420,
                  ),
                  child: ListView.separated(
                    padding: EdgeInsets.zero,
                    shrinkWrap: true,
                    itemCount: matches.length,
                    separatorBuilder: (_, _) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final currency = matches[index];
                      return ListTile(
                        dense: true,
                        title: Text(currency.code),
                        subtitle: Text(currency.name),
                        onTap: () => onSelected(currency),
                      );
                    },
                  ),
                ),
              ),
            );
          },
        ),
        if (_hasNoMatches)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: Text(l10n.noSearchResults),
          ),
      ],
    );
  }
}
