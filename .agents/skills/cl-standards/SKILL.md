---
name: cl-standards
description: "Design Rule & Architectural Invariant Enforcement Engine (DREE v8.0). Wymusza standard 7 niezmienników kompletnej funkcji, generuje wzorce scaffold-unit i przeprowadza statyczny audyt AST diffs."
version: 5.1.0
---

# /cl-standards — Design Rule & Architectural Invariant Enforcement Engine (DREE)

Komenda `/cl-standards` służy do deterministycznego wymuszania standardów projektowych, architektury zależności i kompletności funkcji (7/7 Niezmienników) w pracy subagentów LLM.

---

## 🏛️ Standard 7 Niezmienników Kompletnej Funkcji (The 7-Invariant Rule)

Każda nowa lub modyfikowana funkcja biznesowa w projekcie musi zawierać pełen zestaw 7 elementów:

| # | Niezmiennik | Standard i Lokalizacja | Egzekucja Maszynowa |
|---|---|---|---|
| 1. | **Jawny Kontrakt Typów** | `dataclass(frozen=True)` / TypeSpec w `contracts/` lub module | Wykrywanie braku typów argumentów i zwracanych wartości w AST |
| 2. | **Walidacja Granicy Wejścia** | Sprawdzenie poprawności argumentów w `__post_init__` lub na początku | Test asercji rzucania wyjątku |
| 3. | **Typowane Wyjątki Domenowe** | Błąd dziedziczący po `Exception` / `DomainError` | Zakaz `except:` i `except Exception: pass` w AST |
| 4. | **Czysta Logika Biznesowa (SRP)** | Maksymalnie 40 linii kodu na funkcję | AST linter sprawdza długość funkcji (SRP $\le 40$) |
| 5. | **Bezpieczna Telemetria / Zero Console** | Ustrukturyzowane logi, brak sekretów | Wykrywanie `print(` i `console.log` |
| 6. | **Podwójna Suita Testowa** | Min. 1 Happy-Path + min. 1 Negative Edge-Case | Wymóg obecności asercji i testu wyjątku w `tests/` |
| 7. | **Rejestracja i Living Spec** | `__all__` / eksporty + wpis w `specs/03_DATA_DICTIONARY.md` | Sprawdzanie eksportu i automatyczna aktualizacja słownika |

---

## 🛠️ Użycie CLI

### 1. Generowanie Kompletnego Wzorca Funkcji (Scaffold-First Priming)
Zamiast pisać kod od zera, wygeneruj w 100% zgodny ze standardem szkielet:
```powershell
python .governance/bin/gov.py scaffold-unit --name OrderProcessing --domain orders --type service
```
Silnik wygeneruje:
1. `src/orders/order_processing.py` — implementacja z kontraktem typów, błędem domenowym, walidacją i eksportem `__all__`.
2. `tests/test_order_processing.py` — podwójna suita testowa (happy path + edge case).
3. `specs/03_DATA_DICTIONARY.md` — automatyczny wpis nowej encji w słowniku danych.

### 2. Statyczny Audyt AST Nowego Kodu (Bramka G4)
Przed przejściem bramki dowodowej, zbadaj czy dodany kod nie narusza standardów:
```powershell
# Audyt konkretnego pliku
python .governance/bin/gov.py check-standards --file src/orders/order_processing.py

# Audyt wszystkich zmodyfikowanych plików w ramach zadania
python .governance/bin/gov.py check-standards --task T002
```

---

## ⚙️ Profile Rygoru (`.governance/standards.json`)

* **`tiny`:** Zadania dokumentacyjne, drobne poprawki UI. Limit 60 linii, brak wymuszenia typów, zakaz gołych exceptów.
* **`standard`:** Nowe funkcje, serwisy, kontrolery. Limit 40 linii, pełne typowanie, zakaz bare except, podwójna suita testowa.
* **`critical`:** Finanse, autoryzacja, operacje niszczące. Limit 25 linii, restrykcyjna walidacja brzegowa, zero untyped.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
