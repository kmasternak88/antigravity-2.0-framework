---
trigger: model_decision
description: "Implementacja, błąd testu, regresja lub przygotowanie merge."
---

# 30-test-and-repair

Zacznij od reprodukcji i failing acceptance test dla zmienianego zachowania. Nie wymagaj sztucznego unit test per każdy plik; testuj zachowanie i ryzyko. Pokryj null, puste dane, duplicates, permissions, limits, timeout, rollback, retries, races i recovery tam gdzie domena ich używa. Trzy cykle repair dla tego samego symptom, potem eskalacja. Screen jest dowodem wyglądu, nie poprawności bazy/płatności.
