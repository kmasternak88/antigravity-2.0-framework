---
name: cl-learn
description: "Przekształca incydent w test regresyjny i propozycję reguły, bez automatycznej zmiany polityki."
---

# cl-learn

1. Zapisz symptom, root cause, reprodukcję i brakującą kontrolę.
2. Dodaj test regresyjny w normalnym tasku.
3. Oceń czy lekcja lokalna czy globalna; nie dodawaj reguł na każdy przypadek.
4. Przedstaw ADR/propozycję skill z dowodem i kosztem kontekstu.
5. Owner review i osobna zmiana governance; nie używaj /learn jako obejścia approval.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
