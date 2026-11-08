---
name: cl-learn
description: "Kodyfikacja wiedzy z aktywnej sesji (G-LEARN v8.3): destylacja wniosków, kwarantanna w learning_inbox, audyt check-rules, integracja z Mem0 i Słownikiem Danych SSoT."
version: 8.0.0
trigger: model_decision
---

# /cl-learn — Kodyfikacja Wiedzy i Ewolucja Standardów (G-LEARN v8.3)

Protokół ciągłego uczenia się frameworka i repozytorium. Przekształca incydenty, poprawki deweloperskie i odkryte wzorce w trwałe zasoby projektowe bez ryzyka zatrucia kontekstu (*Epistemic Contamination*).

---

## 🔴 KARDYNALNA ZASADA KWARANTANNY (G-LEARN QUARANTINE)

Żaden wniosek, reguła ani skrót wypracowany podczas sesji **NIE MOŻE** zostać zapisany bezpośrednio do `.agents/rules/*.md`.
Wszelkie nowe reguły podlegają bezwzględnej procedurze: **Kandydat w Kwarantannie -> Audyt AST -> Zgoda Człowieka / Gate Pass -> Promocja**.

---

## 1. Procedura Kodyfikacji Krok po Kroku

### Krok 1: Analiza Sesji i Destylacja Wniosków (Knowledge Distillation)
1. Zidentyfikuj napotkany problem, root cause oraz wprowadzone rozwiązanie.
2. Sformułuj zwięzłą regułę operacyjną skupioną na **mechanizmie zapobiegania regresji**.
3. Ustal typ zasobu:
   - **Reguła Projektowa:** Dla ogólnych wytycznych architektonicznych i standardów kodowania (np. formaty walut, idempotencja, wzorce transakcyjne).
   - **Skill Agentowy:** Dla wielokrokowych procedur operacyjnych (np. testowanie specyficznego modułu, migracja danych).

### Krok 2: Zapis Kandydata do Kwarantanny (`learning_inbox`)
Zapisz kandydata w katalogu kwarantanny:
`.agents/learning_inbox/<nazwa-reguly>.candidate.md`

Wymagany nagłówek YAML frontmatter:
```yaml
---
trigger: model_decision
description: "Kodyfikacja wiedzy z aktywnej sesji (G-LEARN v8.3): destylacja wniosków, kwarantanna w learning_inbox, audyt check-rules, integracja z Mem0 i Słownikiem Danych SSoT."
---
```
Treść reguły:
- Zwięzła, jednoznaczna i deterministyczna ($\le 400$ tokenów).
- Zakaz formułowania wytycznych osłabiających 16 Zasad (np. zakaz pomijania testów, zakaz cichych sukcesów).

### Krok 3: Automatyczny Audyt Niezmienników (`check-rules`)
Uruchom weryfikator zgodności:
```powershell
python .governance/bin/gov.py check-rules --candidate .agents/learning_inbox/<nazwa-reguly>.candidate.md
```
Silnik sprawdza:
- Obecność i poprawność YAML frontmatter.
- Brak naruszeń 16 Zasad Kardynalnych (dual-control, mock-breaker, zero-print, integer currency).
- Limit tokenowy kandydata ($\le 400$ tokenów).

### Krok 4: Zatwierdzenie i Promocja (Promote to Rules)
Po uzyskaniu statusu `APPROVED_FOR_PROMOTION` i autoryzacji operatora:
```powershell
python .governance/bin/gov.py approve-rule --candidate <nazwa-reguly>.candidate.md
```
Silnik automatycznie:
- Weryfikuje łączny budżet tokenów reguł projektu ($\le 2500$ tokenów, max 10 aktywnych reguł).
- Przenosi plik do `.agents/rules/<nazwa-reguly>.md`.
- Generuje trwały artefakt dowodowy w `.governance/evidence/RULE_APPROVED_*.json`.

### Krok 5: Utrwalenie w Pamięci Trwałej Mem0 i Living Charterze
1. **Mem0 (Port 8765):** Wyślij utrwaloną regułę do wektorowej pamięci projektu pod kategorią `invariants` lub `adr`.
2. **SSoT Sync:** Jeśli reguła definiuje nowe modele lub pola danych, zaktualizuj `specs/03_DATA_DICTIONARY.md`.

---

## 2. Format Odpowiedzi i Klauzula Wyjściowa

Raport z wykonania procedury `/cl-learn` musi zawierać:
1. **Zidentyfikowany incydent / wzorzec:** (krótkie podsumowanie problemu i rozwiązania).
2. **Plik kandydata w kwarantannie:** ścieżka do `.agents/learning_inbox/*.candidate.md`.
3. **Wynik audytu `check-rules`:** status i estymowana liczba tokenów.
4. **Artefakt dowodowy:** wygenerowany plik `.governance/evidence/RULE_APPROVED_*.json` (w przypadku promocji).

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
