---
name: cl-review
description: "Wykonuje niezależny przegląd kodu (G5), audyt mutacyjny (Mock-Breaker) i semantyczny interlock przed scaleniem do gałęzi głównej w standardzie v8.0."
version: 5.1.0
---

# /cl-review — Adversarial Review & Pre-Merge Gate Protocol

Protokół niezależnego audytu kodu i testów przed dopuszczeniem do scalenia w Bramce G5 i G6.

## Zasady Rygoru Recenzenta

1. **Bezwzględna Niezależność:**
   - Recenzent (`reviewer`) NIE MOŻE być autorem zadania (`actor`). Samozatwierdzanie jest blokowane przez silnik SQLite (`SELF_REVIEW_REJECTED`).
   - Weryfikacja odbywa się na dokładnie tym samym stanie źródeł (`sourceDigest`).

2. **Krok 1: Audyt Standardów Architektonicznych (DREE):**
   - Zweryfikuj, czy kod spełnia Standard 7 Niezmienników:
     ```bash
     python .governance/bin/gov.py check-standards --task <TASK_ID>
     ```
   - Każde naruszenie (brak adnotacji typu, funkcje > 40 linii, surowe `except:`, `print()`) wymusza decyzję `REJECTED`.

3. **Krok 2: Test Mutacyjny Mock-Breaker (Anty-Tautologia):**
   - Uruchom test odporności na testy pozorne:
     ```bash
     python .governance/bin/gov.py audit-tests --task <TASK_ID>
     ```
   - Silnik automatycznie wstrzykuje mutację syntetyczną (`MUTATION_CHECK_TRIGGERED`). Testy subagenta MUSZĄ zgłosić błąd. Jeśli testy przejdą na mutacji, zadanie zostaje natychmiast zablokowane (`TAUTOLOGICAL_TEST_DETECTED`).

4. **Krok 3: Rejestracja Decyzji Recenzenta (G5):**
   - Po pozytywnym zweryfikowaniu diffa i testów zarejestruj werdykt:
     ```bash
     python .governance/bin/gov.py review --task <TASK_ID> --reviewer <REVIEWER_ID> --decision APPROVED --reference "<ID_ZGLOSZENIA_LUB_UWAGI>"
     ```

5. **Krok 4: Pre-Merge Semantic Interlock & Scalenie (G6):**
   - Sprawdź brak kolizji symboli w drzewie AST:
     ```bash
     python .governance/bin/gov.py interlock --task <TASK_ID>
     ```
   - Scal zmiany z izolowanego worktree do głównego repozytorium:
     ```bash
     python .governance/bin/gov.py worktree --task <TASK_ID> --action merge
     ```
   - Zweryfikuj bramkę zadania i sfinalizuj:
     ```bash
     python .governance/bin/gov.py gate --task <TASK_ID>
     python .governance/bin/gov.py finish --task <TASK_ID> --token <FENCING_TOKEN>
     ```

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
