---
trigger: glob
description: "Zgodność typów i stabilność kontraktów."
globs: "**/*.ts, **/*.tsx, **/*.py, **/*.sql, **/*.json"
---

# Reguła 50: Typowanie, Kontrakty i Niezmienniki Domenowe (Types & Contracts)

1. **Interface-First Contract Freezing:** Zanim powstanie kod implementacji, interfejs musi zostać zdefiniowany i zamrożony w `contracts/*.contract.*` oraz zarejestrowany w `contract_manifests`.
2. **Rygor Domenowy:**
   - **Pieniądze i Waluty:** Bezwzględny wymóg przechowywania kwot jako liczby całkowite w jednostkach podrzędnych (`integer minor`, np. grosze, centy). Bezwzględny zakaz stosowania typów zmiennoprzecinkowych (`float`/`double`) do obliczeń finansowych!
   - **Precyzja Danych:** Ścisłe rozróżnianie pól pominiętych (`omitted`) od pól o wartości jawnie pustej (`null`/`None`).
   - **Idempotencja:** Każda operacja biznesowa wywołująca skutki uboczne wymaga klucza idempotencji (`idempotency_key`) i bezpiecznej obsługi niepewności przy timeoutach sieciowych.
3. **Standard 7 Niezmienników DREE:**
   - DTO wejściowe i wyjściowe z immutability (`frozen=True`).
   - Walidacja wejścia w konstruktorze/`__post_init__`.
   - Wyjątek domenowy dziedziczący po `Exception` (końcówka `Error`).
   - Maksymalnie 40 linii na funkcję (SRP).
   - Jawny eksport w `__all__` oraz synchronizacja ze słownikiem danych `specs/03_DATA_DICTIONARY.md`.
