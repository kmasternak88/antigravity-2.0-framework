---
trigger: model_decision
description: "Release, deployment, raport końcowy lub utrwalanie lessons."
---

# Reguła 60: Integracja, Wydanie i Uczenie Się (Release & Learning)

1. **Jednoznaczny Kandydat Wydania:** Proces release weryfikuje dokładnie tego kandydata, który pomyślnie przeszedł wszystkie bramki G1–G6. Jakakolwiek późniejsza edycja unieważnia dotychczasowe dowody.
2. **Certyfikat Bramkowy GATE_PASS:** Zadanie może zostać włączone do wydania wyłącznie po uzyskaniu certyfikatu przejścia bramki G5 podpisanego przez niezależnego audytora (`reviewer != actor`).
3. **Higiena Pamięci i Promptu:**
   - Utrwalaj w pamięci Mem0 wyłącznie kluczowe decyzje architektoniczne (ADR) oraz powtarzalne wzorce systemowe.
   - Bezwzględny zakaz wpisywania danych specyficznych dla pojedynczego, jednostkowego błędu do promptu globalnego lub reguł workspace.
4. **Nienaruszalny Manifest Wydania:** Komenda `gov.py release` generuje `.governance/RELEASE_MANIFEST.json` z kompletem sum kontrolnych SHA-256 specyfikacji, źródeł i zarejestrowanych dowodów.
