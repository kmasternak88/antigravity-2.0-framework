---
name: grill-me
description: "Sokratejski wywiad inżynieryjny (Socratic Questioning & Ambiguity Elimination) w Antigravity Ultra v8.2. Wymusza eliminację domysłów w One-Way Doors, inwariantach finansowych (Rule 50 DREE: integer cents), kontraktach API, odporności SRE i granicach EARS za pomocą natywnych pytań ask_question."
version: 8.2.0
---

# /grill-me — Socratic Interview & Ambiguity Elimination Engine (v8.2)

Tryb `/grill-me` to wyspecjalizowany protokół sokratejski stworzony w celu **bezwzględnej eliminacji leniwych domysłów sztucznej inteligencji (AI Assumptions)** oraz niedopowiedzeń biznesowych przed przystąpieniem do jakichkolwiek prac projektowych i implementacyjnych.

Może być uruchamiany samodzielnie (`/grill-me`) lub jako integralna faza poleceń `/extend`, `/cl-extend` oraz `/cl-inception`.

---

## 🎯 GŁÓWNE ZASADY PROTOKOŁU "GRILL-ME" (RFC 2119)

1. **ZERO ASSUMPTIONS INVARIANT:**
   - Agentowi kategorycznie zabrania się zgadywania założeń architektonicznych, limitów wydajnościowych, schematów walutowych czy strategii awarii.
2. **SOCRATIC QUESTIONING OVER OPEN DIALOGUE:**
   - Agent nie pyta: *"Jak chcesz to zrobić?"*. Agent formułuje precyzyjne pytania wielokrotnego wyboru, przedstawiając:
     - Opcję **[REKOMENDOWANĄ]** z perspektywy Staff SRE / Principal Architect.
     - Alternatywy techniczne wraz z jawną analizą kompromisów (Trade-Offs).
     - Tryby awaryjne (Failure Modes) i wpływ na acykliczny graf zadań (DAG).
3. **ONE-WAY DOORS VS TWO-WAY DOORS:**
   - Pytania skupiają się wyłącznie na decyzjach **nieodwracalnych (One-Way Doors)**: wybór silnika bazodanowego, transakcyjność, format kwot pieniężnych, protokół API. Decyzje odwracalne (Two-Way Doors) agent podejmuje autonomicznie i rejestruje w ADR.

---

## 🔍 5 WYMIARÓW WYWIADU SOKRATEJSKIEGO

Podczas sesji `/grill-me` agent bada dokładnie 5 krytycznych wymiarów (5 Invariant Vectors):

### 1. One-Way Doors & Magazyn Danych (ONE_WAY_DOORS_STORAGE)
- Jaki model persystencji jest wymagany? (Relacyjny PostgreSQL/SQLite z ACID, HPOS dla WooCommerce vs Dziennik zdarzeń Append-Only vs Cache In-Memory).
- Jaka jest strategia migracji i izolacji danych (np. multi-tenancy przez pole `tenant_id` vs odrębne schematy)?

### 2. Inwarianty Finansowe i Kwoty Pieniężne (FINANCIAL_MONEY_INVARIANTS - Reguła 50 DREE)
- Czy funkcja dotyka jakichkolwiek płatności, faktur, sald, subskrypcji lub limitów budżetowych?
- **Żelazna Reguła 50 DREE:** Wszystkie kwoty pieniężne MUSZĄ być reprezentowane jako liczby całkowite w jednostkach podrzędnych (`integer minor`, np. grosze, centy). Bezwzględny zakaz typów `float`/`double`.
- Wymóg nagłówka i klucza idempotencji (`X-Idempotency-Key`) dla operacji mutujących finanse.

### 3. Granice Odporności i Zachowania Niepożądane (RESILIENCE_AND_UNWANTED_EARS)
- Ścisłe zdefiniowanie zachowań awaryjnych w składni EARS Unwanted behavior (`IF awaria THEN DomainError`).
- Dedykowane wyjątki domenowe dziedziczące po `DomainError` (zakaz surowych `except: pass`).

### 4. SRE, Odporność i Ograniczenia Zasobów (SRE_RESOURCE_LIMITS)
- Ścisły timeout dla wywołań (domyślnie 5000ms), rate limiting i budżety pamięci.
- Zachowanie przy awarii systemów zależnych: Fail-Closed (odrzucenie żądania) vs Circuit Breaker.
- Polityka ponowień: Exponential Backoff z Full Jitter.

### 5. Architektura Panelu, Uprawnień i Dostępności (PANEL_PERMISSIONS_WCAG)
- Moduł panelu administracyjnego (Admin Dashboard & Settings, sub-menu, formularze opcji).
- Wymogi UI/UX: paleta barwna OKLCH, dostępność WCAG 2.1 AA (cele dotykowe min. 48px), walidacja uprawnień RBAC / `current_user_can()`.

> **Adaptive Socratic Flow (Bypass Rule):** Jeśli dostarczony brief/PRD jednoznacznie uziemia wszystkie 5 Wektorów Niezmienników (IMS > 0.70), faza zadawania pytań zostaje automatycznie pominięta (`Grill-Me Bypassed: All 5 Invariant Vectors explicitly grounded in input PRD`), a agent przystępuje natychmiast do kompilacji blueprintu.

---

## 🛠️ INTEGRACJA Z NARZĘDZIEM `ASK_QUESTION` W ANTIGRAVITY 2.0

W środowisku Antigravity 2.0 agent wywołuje natywny mechanizm `ask_question` dla każdej niejednoznaczności, generując ustrukturyzowany payload:

```json
{
  "question": "W jaki sposób moduł ma obsługiwać rozliczenia finansowe i salda?",
  "options": [
    {
      "id": "opt_integer_cents",
      "label": "[A] Kwoty w integer minor units (grosze/centy) + Idempotencja (Rekomendowane: Reguła 50 DREE)",
      "recommended": true,
      "trade_off": "Zero błędów zaokrągleń IEEE 754, ochrona przed duplikacją płatności przy timeoutach."
    },
    {
      "id": "opt_decimal_float",
      "label": "[B] Typ float / double (Niedozwolone w standardzie Ultra v8.2)",
      "recommended": false,
      "trade_off": "Prowadzi do nieodwracalnych rozbieżności księgowych w bazie danych."
    },
    {
      "id": "opt_no_money",
      "label": "[C] Moduł nie przetwarza danych finansowych",
      "recommended": false,
      "trade_off": "Brak narzutu walidacji walutowej."
    }
  ]
}
```

---

## 📄 ARTEFAKTY WYJŚCIOWE SESJI "GRILL-ME"

Po zakończeniu wywiadu agent generuje:
1. **Rejestr ADR (Architecture Decision Record):** Zapisany w `docs/adr/ADR-XXXX-[slug].md` oraz utrwalony w pamięci kognitywnej Mem0.
2. **Wymagania w składni EARS:** Zintegrowane bezpośrednio z Living Charter w `specs/01_PRODUCT_REQUIREMENTS.md`.
3. **Triady Testowe Gherkin:** 1 Happy Path + 1 Boundary Negative + 1 Adversarial/Race Negative.
4. **Handoff do Kompilatora:** Przekazanie uzgodnionych parametrów do `tools/extend_project.py` lub `tools/genesis_compiler.py`.
