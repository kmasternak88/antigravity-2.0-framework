---
name: cl-verify
description: "Weryfikuje scalony candidate i pokrycie acceptance dowodami."
---

# cl-verify

1. Uruchom suites z risk profile na świeżym środowisku.
2. Dla UI: asercje DOM/network/accessibility; opcjonalny /browser do eksploracji i screenshoty z oznaczeniem candidate.
3. Dla API: integration/contracts, nie obowiązkowa przeglądarka.
4. Porównaj PASS z check/source/spec/log hashes. Missing=NOT_RUN.
5. Zapisz report: co testowano, co nie, ryzyka i blokady.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
