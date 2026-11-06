---
name: cl-characterize
description: "Brownfield Deep Discovery & Golden Master Harness dla Antigravity Ultra v8.0. Skanuje topologię tras i bazy danych, generuje Living Spec oraz rejestruje deterministyczne snapshoty zachowań przed modyfikacją kodu."
version: 5.1.0
---

# /cl-characterize — Brownfield Reconstruction & Zero-Regression Harness

Komenda `/cl-characterize` jest uruchamiana w aktywnych projektach (`S1_BROWNFIELD`), aby bezpiecznie zmapować kod źródłowy, ocenić dług techniczny i zamrozić zachowanie produkcyjne w testach asekuracyjnych (*Golden Master Tests*).

```
[Istniejący Projekt] 
       ↓
(1. AST & Dependency Topology Discovery) → [Mapa komponentów, tras i modeli]
       ↓
(2. Test Debt & Fragility Audit)         → [Macierz pokrycia i martwych punktów]
       ↓
(3. Characterization Harness (Golden))   → [Snapshoty bieżącego stanu zachowań]
       ↓
(4. Surgical Modernization Roadmap)      → [Zadania refaktoringu z asercją 0-regresji]
```

---

## 🛡️ PROTOKÓŁ KROK PO KROKU

### Krok 1: Głęboka Rekonstrukcja Topologii (`gov.py discover --deep`)
Uruchom statyczny skaner AST, tras i modeli:
```powershell
python .governance/bin/gov.py discover --deep
```
Rezultaty:
* `.governance/inventory.json` — pełny spis plików i zależności
* `.governance/topology.json` — graf tras, modele i Fragility Score (0-100)
* `specs/RECONSTRUCTED_SPEC.md` — żyjąca specyfikacja z diagramem ERD w formacie Mermaid

### Krok 2: Zamrożenie Zachowania (Golden Master Baseline)
> ⚠️ **Żelazna Zasada Brownfield:** **Żaden agent nie ma prawa modyfikować logiki biznesowej, dopóki aktualne zachowanie nie zostanie zamrożone w teście Golden Master!**

Zarejestruj istniejące zachowanie systemu za pomocą:
```powershell
python .governance/bin/gov.py golden-record --name baseline_regression --record "<polecenie_uruchomienia_testow_lub_api>"
```
*Silnik automatycznie maskuje zmienne ulotne (UUID, timestampy ISO, losowe identyfikatory, porty).*

### Krok 3: Izolacja Zadań Refaktoringu (Atomic Handoff)
Przed przystąpieniem do modyfikacji wygeneruj atomowy pakiet handoffu:
```powershell
python .governance/bin/gov.py package-handoff --task T00X
```
Hook `native_guard.py` wymusi blokadę zapisu dla wszystkich plików poza `targetFiles.allowedToWrite`.

### Krok 4: Weryfikacja Asercji Zero-Regresji (`gov.py golden-assert`)
Po zakończeniu implementacji sprawdź brak regresji względem zamrożonego snapshotu:
```powershell
python .governance/bin/gov.py golden-assert --name baseline_regression
```
Jeśli asercja zwróci `PASS`, zadanie jest w 100% bezpieczne i gotowe do bramki G5 (Review).

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
