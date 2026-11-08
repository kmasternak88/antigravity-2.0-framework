# [SZABLON] Product Requirements Document (PRD): Lean & Modular Architecture

> **Metadane Dokumentu (System Header)**
> - **ID Dokumentu:** `PRD-2026-001`
> - **Wersja Schematu:** `v3.2.0-MODULAR`
> - **Status Dokumentu:** `[DRAFT | IN_REVIEW | APPROVED | DEPRECATED]`
> - **Architekt / PM:** `[Imię i Nazwisko, Rola]`
> - **Lead Inżynieryjny:** `[Imię i Nazwisko, Rola]`
> - **Klasyfikacja Produktu (Flagi Aktywacji Bloków z Sekcji 7):** `is_SaaS: [TRUE/FALSE]`, `is_Mobile: [TRUE/FALSE]`, `is_Hardware_IoT: [TRUE/FALSE]`
> - **Data Ostatniej Aktualizacji:** `YYYY-MM-DD`

---

## 1. Kontekst Strategiczny i Wizja

### 1.1. Podsumowanie Wykonawcze i Rdzeń Strategii
`[Instrukcja: Wypełnij poniższą tabelę, unikając narracji marketingowej. Zdefiniuj mierzalne fakty rynkowe, precyzyjny koszt problemu u klienta oraz twarde uzasadnienie okna czasowego (Market Timing). Każde twierdzenie musi być możliwe do obrony przed komitetem inwestycyjnym.]`

| Parametr Strategiczny | Typ Danych | Specyfikacja / Wartość Docelowa (Przykład Wzorcowy) |
| :--- | :--- | :--- |
| **Executive Summary** | `String (Max 500 znaków)` | Wdrożenie zautomatyzowanego silnika wykrywania anomalii w łańcuchu dostaw (Supply Chain Anomaly Detection) czasu rzeczywistego, redukującego przestoje magazynowe u klientów Enterprise o min. 22% w skali kwartału. |
| **Problem Statement (Ból Rynkowy)** | `String` | Menedżerowie logistyki tracą średnio 14 godzin tygodniowo na ręczną konsolidację raportów CSV z rozproszonych systemów WMS/ERP. Opóźnienie w detekcji braków magazynowych wynosi średnio 48h, co generuje kary umowne (SLA) na poziomie 15 000 EUR miesięcznie na jeden węzeł dystrybucyjny. |
| **Product Vision (Wizja 3-letnia)** | `String` | Stworzenie autonomicznego, samooptymalizującego się systemu operacyjnego dla logistyki B2B, który przewiduje wąskie gardła na 72h przed ich wystąpieniem i automatycznie przekierowuje wolumeny bez ingerencji człowieka. |
| **Business Value Proposition** | `String` | Dla klienta: Redukcja kosztów operacyjnych (OPEX) o 18% i eliminacja kar SLA. Dla naszej organizacji: Otwarcie nowego strumienia przychodowego (Tier Enterprise) z marżą brutto (Gross Margin) na poziomie 82%. |
| **Dlaczego akurat teraz? (Market Timing)** | `String (Wymagane uzasadnienie)` | 1. Wejście w życie dyrektywy UE o sprawozdawczości łańcucha dostaw (Q3 2026) wymusza na firmach audytowalność w czasie rzeczywistym.<br>2. Spadek kosztów inferencji modeli szeregów czasowych o 60% w ostatnich 12 miesiącach umożliwia rentowne przetwarzanie danych telemetrycznych co 5 sekund. |
| **Strategiczne Cele Organizacji (OKR Alignment)** | `Enum / ID` | `OBJ-2026-Q3`: Ekspansja w segmencie Mid-Market/Enterprise.<br>`KR-02`: Pozyskanie 50 nowych kont z ACV (Annual Contract Value) > 25 000 EUR. |

### 1.2. Model Finansowy i Estymacja ROI
`[Instrukcja: Wprowadź twarde założenia budżetowe dla fazy MVP (Minimum Viable Product) oraz horyzontu 12 miesięcy po wdrożeniu (GA - General Availability). Wszystkie wartości walutowe podawaj w jednej, spójnej walucie bazowej.]`

| Kod Finansowy | Metryka Finansowa | Typ Danych | Wartość Bazowa / Koszt | Wartość Docelowa (12M Post-Launch) | Założenia Kalkulacyjne (Assumptions) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `FIN-01` | **CAPEX / Koszt Wytworzenia MVP** | `Currency (EUR)` | 180 000 EUR | Nie dotyczy (Koszt zamknięty) | 4 FTE Engineering + 1 PM + 0.5 Product Designer przez 3 miesiące (Sprinty 1-6). |
| `FIN-02` | **OPEX (Infrastruktura / Utrzymanie)** | `Currency (EUR/m-c)` | 1 200 EUR / m-c | 4 500 EUR / m-c | Koszt chmury obliczeniowej (AWS EKS, RDS, przetwarzanie strumieniowe Kafka) przy skali 100 aktywnych tenatów. |
| `FIN-03` | **Prognozowany ARR (Annual Recurring Revenue)** | `Currency (EUR)` | 0 EUR | 750 000 EUR | 30 klientów Enterprise x 25 000 EUR średniego ACV w pierwszym roku od premiery. |
| `FIN-04` | **Szacowany Zwrot z Inwestycji (Net ROI)** | `Percentage (%)` | 0% | 288% | Wyliczone jako: `((ARR - (CAPEX + 12*OPEX)) / (CAPEX + 12*OPEX)) * 100%`. |
| `FIN-05` | **Próg Rentowności (Break-Even Point)** | `Integer (Miesiące)` | Nie dotyczy | 5 miesięcy od GA | Moment zrównania skumulowanej marży brutto z kosztem wytworzenia (`FIN-01`). |

---

## 2. Grupa Docelowa i Aktorzy Systemowi

`[Instrukcja: Zdefiniuj wszystkich aktorów (użytkowników końcowych, administratorów, zewnętrzne systemy zautomatyzowane) wchodzących w interakcję z produktem. Każda persona MUSI posiadać unikalny, niezmienny identyfikator w formacie PER-XX. Identyfikatory te są kluczem obcym wykorzystywanym w Sekcji 3 (Matryca Funkcjonalna). Zakaz dodawania wymagań w Sekcji 3 dla person niezdefiniowanych w poniższej tabeli.]`

| ID Persony | Nazwa / Archetyp | Główne Frustracje (Pains) | Cele i Motywacje (Gains) | Częstotliwość Używania | Kontekst Technologiczny (Środowisko / Urządzenia) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`PER-01`** | **Operacyjny Menedżer Logistyki (Heavy User)** | - Przełączanie się między 4 niespójnymi ekranami systemów legacy.<br>- Zalew fałszywych alertów (Alert Fatigue) o niskim priorytecie.<br>- Brak możliwości szybkiego wyeksportowania wsadu dowodowego dla przewoźnika. | - Natychmiastowa identyfikacja przesyłek zagrożonych opóźnieniem.<br>- Skrócenie czasu reakcji na incydent z 4 godzin do 15 minut.<br>- Automatyzacja raportowania do zarządu. | Codziennie (Ciągła praca w tle: 6-8h dziennie). | Desktop (Windows 11, dwa monitory 1080p), przeglądarka Chrome/Edge, sieć korporacyjna za restrykcyjnym firewallem/VPN. |
| **`PER-02`** | **Inspektor Terenowy / Magazynier (Mobile/Edge Actor)** | - Zrywanie połączenia Wi-Fi/LTE w głębi hali magazynowej (utrata niezapisanych formularzy).<br>- Zbyt małe elementy interfejsu, trudne do kliknięcia w rękawicach roboczych.<br>- Powolne działanie skanera kodów kreskowych. | - Szybkie zatwierdzenie odbioru partii towaru w mniej niż 30 sekund.<br>- Pewność, że dane zsynchronizują się automatycznie po odzyskaniu zasięgu. | Codziennie (Interwałowo: 40-60 sesji po 1-2 minuty dziennie). | Urządzenia mobilne Rugged (Zebra TC52 / Android 13) oraz smartfony iOS/Android, praca w ruchu, trudne warunki oświetleniowe, częsty tryb Offline. |
| **`PER-03`** | **Administrator Bezpieczeństwa IT / DevSecOps (Buyer/Gatekeeper)** | - Brak granularnej kontroli uprawnień (RBAC) w narzędziach zewnętrznych.<br>- Brak dzienników audytowych (Audit Logs) wymaganych przez ISO 27001.<br>- Ręczne zarządzanie kontami pracowników (brak SSO/SCIM). | - Pełna automatyzacja provisioningu użytkowników przez Okta/Azure AD.<br>- Gwarancja izolacji danych i zgodności z regulacjami RODO.<br>- Bezproblemowe przejście audytu bezpieczeństwa. | Rzadko (Konfiguracja inicjalna + audyt raz na kwartał / ad-hoc przy incydentach). | Desktop (macOS/Linux), interfejsy CLI, API REST/GraphQL, integracja z systemami klasy SIEM (Splunk/Datadog). |

---

## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)

`[Instrukcja: Poniższa tabela definiuje kompletny zakres funkcjonalny wydania. OBOWIĄZUJĄCA REGUŁA INŻYNIERYJNA: Łączny wolumen wymagań o priorytecie "MUST HAVE" NIE MOŻE przekroczyć 40% całkowitego wolumenu (pracochłonności/liczby pozycji) zaplanowanego na pierwsze wydanie (MVP). Przekroczenie tego limitu oznacza błędną dekompozycję i blokuje zatwierdzenie dokumentu. Każde wymaganie musi posiadać pełny łańcuch powiązań: ID Wymagania -> ID Persony -> Kryteria Akceptacji (w ścisłej notacji Gherkin: Given-When-Then) -> ID Zdarzenia Telemetrycznego (zdefiniowanego w Sekcji 6).]`

| ID Wymagania | Nazwa Funkcji | User Story (`Jako... Chcę... Aby...`) | Przypisane ID Persony | Priorytet (MoSCoW) | Kryteria Akceptacji (Notacja `Given-When-Then`) | Powiązany Punkt Telemetryczny | Wpływ na Architekturę |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Silnik reguł i priorytetyzacji alertów | **Jako** Operacyjny Menedżer Logistyki,<br>**Chcę** widzieć na górze listy wyłącznie anomalie przekraczające próg finansowy 5 000 EUR,<br>**Aby** nie tracić czasu na obsługę incydentów o marginalnym wpływie biznesowym. | `PER-01` | **MUST HAVE** | **Given:** Użytkownik `PER-01` jest zalogowany i posiada aktywny filtr domyślny na tablicy rozdzielczej.<br>**When:** System odbiera z Kafki zdarzenie opóźnienia transportu o szacowanym koszcie SLA równym 6 200 EUR.<br>**Then:** Rekord pojawia się na szczycie listy w czasie poniżej 500ms, oznaczony tagiem `CRITICAL`, oraz wyzwala powiadomienie dźwiękowe/wizualne w UI. | `EVT-001` | **Wysoki** (Wymaga wdrożenia silnika przetwarzania strumieniowego i indeksowania in-memory). |
| **`REQ-002`** | Lokalna kolejka synchronizacji Offline (Offline-First Queue) | **Jako** Inspektor Terenowy,<br>**Chcę** móc zeskanować list przewozowy i zatwierdzić protokół uszkodzenia przy całkowitym braku zasięgu sieci,<br>**Aby** nie wstrzymywać rozładunku rampy magazynowej. | `PER-02` | **MUST HAVE** | **Given:** Urządzenie mobilne użytkownika `PER-02` znajduje się w stanie `Network: Offline`.<br>**When:** Użytkownik skanuje kod QR partii, dodaje 2 zdjęcia uszkodzeń i klika "Zatwierdź protokół".<br>**Then:** Dane są szyfrowane (AES-256) i zapisywane w lokalnej bazie SQLite/WatermelonDB ze statusem `PENDING_SYNC`, a po wykryciu aktywnego połączenia TCP/IP automatycznie wysyłane do API z mechanizmem *exponential backoff*. | `EVT-002` | **Wysoki** (Wymaga obsługi rozwiązywania konfliktów zapisu CRDT / Last-Write-Wins po stronie backendu). |
| **`REQ-003`** | Jednokrotne logowanie (SSO SAML 2.0 / OIDC) oraz SCIM | **Jako** Administrator Bezpieczeństwa IT,<br>**Chcę** podłączyć aplikację do korporacyjnego dostawcy tożsamości (Okta / Entra ID),<br>**Aby** automatycznie odbierać dostęp pracownikom w momencie ich zwolnienia w systemie HR. | `PER-03` | **SHOULD HAVE** | **Given:** Skonfigurowane połączenie SAML 2.0 i token SCIM pomiędzy tenantem klienta a IdP.<br>**When:** Administrator dezaktywuje konto użytkownika `PER-01` w systemie Okta.<br>**Then:** W ciągu maksymalnie 60 sekund wszystkie aktywne sesje JWT i Refresh Tokeny tego użytkownika w naszym systemie zostają unieważnione (HTTP 401 przy kolejnym żądaniu). | `EVT-003` | **Średni** (Integracja z gotowym dostawcą Auth0 / Keycloak, modyfikacja warstwy middleware). |
| **`REQ-004`** | Jednoklikowy eksport pakietu dowodowego (Claim PDF/ZIP) | **Jako** Operacyjny Menedżer Logistyki,<br>**Chcę** wygenerować kompletny pakiet reklamacyjny jednym kliknięciem,<br>**Aby** natychmiast wysłać oficjalne roszczenie do zewnętrznego spedytora. | `PER-01` | **COULD HAVE** | **Given:** Istnieje zamknięty protokół anomalii zawierający logi czasowe i zdjęcia z magazynu.<br>**When:** Użytkownik klika przycisk "Generuj Pakiet Roszczeniowy".<br>**Then:** System asynchronicznie kompiluje dokument PDF ze znakiem wodnym i sumą kontrolną SHA-256 oraz zwraca link do pobrania w czasie poniżej 5 sekund. | `EVT-004` | **Niski** (Wydzielony mikroserwis/worker generujący dokumenty na bazie szablonu HTML/PDF). |
| **`REQ-005`** | Wbudowany moduł czatu wideo z kierowcą | **Jako** Operacyjny Menedżer Logistyki,<br>**Chcę** nawiązać połączenie wideo z kierowcą ciężarówki bezpośrednio z poziomu mapy,<br>**Aby** zweryfikować przyczynę postoju. | `PER-01` | **WON'T HAVE (Ten Release)** | **Given:** Funkcjonalność wykluczona z zakresu MVP (Out of Scope).<br>**When:** Próba wdrożenia w cyklu Q3.<br>**Then:** Odrzucenie przez Product Ownera celem zachowania limitu 40% dla zadań MUST HAVE. | `BRAK (Out of Scope)` | **Wysoki** (Wymagałoby wdrożenia serwerów WebRTC/TURN i zmian w aplikacji kierowcy). |

---

## 4. Przepływy Użytkownika i Logika Interfejsu (User Flows)

`[Instrukcja: Zmapuj kluczowe procesy w systemie, wiążąc je bezpośrednio z wymaganiami z Sekcji 3 i personami z Sekcji 2. Nie opisuj wyglądu przycisków (od tego są makiety Figma) – opisz deterministyczną maszynę stanów: co jest wejściem, jakie warunki logiczne są sprawdzane i jak system zachowuje się w sytuacjach awaryjnych (Error States).]`

### 4.1. Referencje do Zasobów Projektowych (Design Artifacts)
* **Główny System Designu (Design System):** `[Link do biblioteki komponentów w Figma - np. https://figma.com/file/DS-v4.2]`
* **Makiety Interaktywne (High-Fidelity Prototypes):** `[Link do prototypu w Figma przypiętego do epików REQ-001 - REQ-004]`
* **Diagramy Architektury Przepływów (Sequence Diagrams):** `[Link do tablicy Miro / skryptu Mermaid.js]`

### 4.2. Specyfikacja Przepływu: Obsługa Krytycznej Anomalii i Zapisu Terenowego (`FLOW-01`)
* **Powiązane Wymagania:** `REQ-001`, `REQ-002`, `REQ-004`
* **Zaangażowani Aktorzy:** `PER-02` (Inicjator terenowy) $\rightarrow$ `System (Backend)` $\rightarrow$ `PER-01` (Decydent operacyjny)
* **Warunek Początkowy (Pre-condition):** Partia towaru posiada status `IN_TRANSIT` w bazie danych, a inspektor `PER-02` posiada uwierzytelnioną sesję na urządzeniu mobilnym.

#### A. Ścieżka Szczęśliwa (Happy Path - Scenariusz Nominalny)
1. **[Krok 1 - `PER-02`]:** Skanuje kod kreskowy GS1-128 z palety za pomocą wbudowanego czytnika laserowego/kamery.
2. **[Krok 2 - `System`]:** Waliduje sumę kontrolną kodu lokalnie, pobiera metadane zamówienia z pamięci podręcznej (Cache) i wyświetla formularz kontrolny w czasie `< 200ms`.
3. **[Krok 3 - `PER-02`]:** Zaznacza flagę `Uszkodzenie Mechaniczne`, wykonuje 2 zdjęcia dokumentacyjne i zatwierdza formularz przyciskiem akcji głównej.
4. **[Krok 4 - `System`]:** Przesyła ładunek JSON/Multipart przez API, kalkuluje szacowaną wartość straty na podstawie cennika SKU (wynik: `6 200 EUR > próg 5 000 EUR`) i nadaje status `CRITICAL_ANOMALY`.
5. **[Krok 5 - `PER-01`]:** Otrzymuje w czasie rzeczywistym (WebSockets) wiersz na szczycie tabeli w panelu webowym, otwiera szczegóły, weryfikuje zdjęcia i klika "Generuj Pakiet Roszczeniowy" (`REQ-004`).
6. **Warunek Końcowy (Post-condition):** Rekord posiada status `CLAIM_GENERATED`, wygenerowany plik PDF jest zapisany w niemodyfikowalnym хранилиszczu (WORM S3 Bucket), a zdarzenia `EVT-001`, `EVT-002` i `EVT-004` są zarejestrowane w hurtowni analitycznej.

#### B. Ścieżki Alternatywne (Alternative Paths)
* **`ALT-01` (Brak łączności podczas kroku 3 i 4 - Tryb Offline):**
  1. W Kroku 4 aplikacja mobilna wykrywa stan `navigator.onLine == false` lub timeout gniazda powyżej `3000ms`.
  2. Aplikacja przechodzi do procedury z `REQ-002`: zapisuje paczkę w lokalnej kolejce SQLite i wyświetla użytkownikowi `PER-02` nieblokujący komunikat (Toast): *"Zapisano lokalnie. Synchronizacja nastąpi automatycznie po odzyskaniu sieci"*.
  3. Użytkownik `PER-02` może natychmiast przejść do skanowania kolejnej palety bez blokady ekranu (Non-blocking UI).
* **`ALT-02` (Wartość anomalii poniżej progu krytycznego):**
  1. W Kroku 4 wyliczona wartość straty wynosi `800 EUR` (poniżej progu 5 000 EUR zdefiniowanego w `REQ-001`).
  2. System nadaje status `LOW_PRIORITY_ANOMALY`, zapisuje rekord w bazie i pomija wysyłkę natychmiastowego powiadomienia WebSocket do `PER-01` (rekord trafia do zbiorczego raportu dobowego).

#### C. Obsługa Sytuacji Awaryjnych i Stanów Błędu (Edge Cases & Error States)
`[Instrukcja: Zdefiniuj każdy przewidywalny stan błędu. Zabronione jest pozostawianie obsługi błędów domyślnym komunikatom przeglądarki lub systemu operacyjnego (np. "Wystąpił nieznany błąd").]`

| Kod Błędu | Scenariusz Awaryjny (Trigger) | Oczekiwana Reakcja Systemu (Backend / Klient) | Komunikat w Interfejsie (UI Copy & Action) |
| :--- | :--- | :--- | :--- |
| **`ERR-FLOW-01`** | **Konflikt zapisu (Race Condition):** Dwie osoby (`PER-02`) skanują tę samą paletę w trybie Offline i synchronizują dane w odstępie kilku minut. | Backend przyjmuje oba żądania (nie odrzuca drugiego błędem HTTP 409 do klienta mobilnego), łączy załączniki zdjęciowe w jeden wątek i tworzy flagę `MERGE_CONFLICT` dla operatora `PER-01`. | Dla `PER-01`: Baner ostrzegawczy w karcie incydentu: *"Wykryto dwa niezależne raporty terenowe dla tej partii. Zweryfikuj połączoną oś czasu."* |
| **`ERR-FLOW-02`** | **Nieczytelny / Uszkodzony kod GS1-128:** Kamera lub skaner laserowy nie może zdekodować kodu przez `> 5 sekund`. | Aplikacja automatycznie aktywuje doświetlenie LED oraz wyświetla klawiaturę numeryczną z maską walidacyjną. | *"Nie można odczytać kodu kreskowego. Wprowadź 18-cyfrowy numer SSCC ręcznie lub wykonaj zdjęcie etykiety do analizy OCR."* |
| **`ERR-FLOW-03`** | **Przekroczenie limitu pamięci lokalnej urządzenia (Storage Full):** Brak miejsca na zapis zdjęć w trybie Offline (`REQ-002`). | Przed otwarciem aparatu aplikacja sprawdza wolną przestrzeń dyskową. Jeśli `< 100 MB`, blokuje możliwość dodania nowych zdjęć przed zwolnieniem pamięci podręcznej zsynchronizowanych wcześniej zadań. | Modal blokujący: *"Pamięć urządzenia jest pełna. Połącz się z siecią Wi-Fi, aby przesłać 14 oczekujących raportów i zwolnić miejsce."* |
| **`ERR-FLOW-04`** | **Niedostępność usługi generowania PDF (`REQ-004`):** Worker zwraca HTTP 503 lub przekracza timeout `10s`. | System umieszcza zadanie w kolejce Dead-Letter Queue (DLQ), ponawia próbę 3-krotnie w tle i po wygenerowaniu wysyła dokument na adres e-mail użytkownika `PER-01`. | Toast informacyjny: *"Generowanie raportu trwa dłużej niż zwykle. Gotowy pakiet wyślemy bezpośrednio na Twój adres e-mail w ciągu kilku minut."* |

---

## 5. Wymagania Niefunkcjonalne, Bezpieczeństwo i Compliance (NFR)

`[Instrukcja: Określ twarde ramy jakościowe, architektoniczne i prawne. Parametry w tej sekcji stanowią kryteria akceptacji dla zespołów DevOps, Security oraz QA. Zabrania się używania określeń niemierzalnych typu "system ma działać szybko i bezpiecznie" – każda pozycja musi zawierać konkretną wartość liczbową lub nazwę standardu.]`

| ID NFR | Kategoria | Parametr / Obszar | Specyfikacja Docelowa (SLA / SLO / Standard) | Metoda Weryfikacji i Audytu |
| :--- | :--- | :--- | :--- | :--- |
| **`NFR-PERF-01`** | **1. Wydajność (Performance & Latency)** | Czas odpowiedzi API (Read / Write) | - **Odczyt (GET):** `p95 < 150ms`, `p99 < 300ms` przy obciążeniu nominalnym.<br>- **Zapis (POST/PUT):** `p95 < 250ms`, `p99 < 500ms`.<br>- **Strumieniowanie WebSockets:** Opóźnienie end-to-end (od Kafki do przeglądarki) `< 500ms`. | Automatyczne testy obciążeniowe k6 / Gatling w potoku CI/CD przed każdym wdrożeniem na środowisko Staging. |
| **`NFR-PERF-02`** | **1. Wydajność (Performance & Latency)** | Wydajność Klienta (Web / Mobile) | - **Web (Core Web Vitals):** LCP `< 1.8s`, FID/INP `< 100ms`, CLS `< 0.05`.<br>- **Mobile:** Czas zimnego startu aplikacji (Cold Start) `< 2.0s`; płynność przewijania list min. `55 FPS`. | Monitoring Real User Monitoring (RUM) w Datadog / Sentry oraz profilowanie Lighthouse w CI. |
| **`NFR-SCAL-01`** | **2. Skalowalność i Niezawodność (Scalability & Availability)** | Dostępność systemu (Uptime SLA) i Przepustowość | - **SLA Dostępności:** `99.95%` w skali miesiąca (maksymalny dopuszczalny nieplanowany przestój: `21.9 minuty / miesiąc`).<br>- **Skalowalność horyzontalna:** Obsługa piku `5 000 RPS` (Requests Per Second) bez degradacji czasów odpowiedzi `p95` dzięki autoskalowaniu HPA (Kubernetes).<br>- **RPO / RTO:** RPO (Recovery Point Objective) `< 5 minut`, RTO (Recovery Time Objective) `< 30 minut`. | Testy Chaos Engineering (symulacja awarii strefy dostępności AWS AZ) wykonywane raz na kwartał. |
| **`NFR-SEC-01`** | **3. Bezpieczeństwo (Security & Auth)** | Szyfrowanie, Autoryzacja i Ochrona Brzegowa | - **W tranzycie (In-Transit):** Wymuszone TLS 1.3 (HSTS aktywne).<br>- **W spoczynku (At-Rest):** Szyfrowanie baz danych, wolumenów S3 oraz lokalnych baz SQLite na urządzeniach mobilnych algorytmem `AES-256-GCM`.<br>- **Autoryzacja:** OAuth 2.0 / OIDC (krótkowieczne tokeny JWT `exp = 15 min` + rotowane Refresh Tokeny), model uprawnień RBAC z izolacją danych na poziomie wiersza (Row-Level Security - `tenant_id`).<br>- **Zgodność z OWASP:** Brak podatności klasy High/Critical wg OWASP Top 10 (Web & Mobile). | Statyczna analiza kodu (SAST - SonarQube/Snyk) przy każdym Pull Requeście + zewnętrzne testy penetracyjne (Pentesty Black/Grey Box) przed premierą GA. |
| **`NFR-ACC-01`** | **4. Dostępność Cyfrowa (Accessibility)** | Standardy WCAG i Ergonomia | - Pełna zgodność ze standardem **WCAG 2.1 na poziomie AA**.<br>- Kontrast tekstu do tła minimum `4.5:1` (dla trybu jasnego oraz trybu wysokiego kontrastu na hali magazynowej).<br>- Pełna obsługa nawigacji wyłącznie za pomocą klawiatury (Tab-index, skróty klawiszowe dla `PER-01`).<br>- Minimalny rozmiar pola dotykowego (Touch Target) na urządzeniach mobilnych: `48x48 dp` (przystosowanie do pracy w rękawicach dla `PER-02`). | Automatyczny audyt axe-core w testach E2E (Playwright) + manualny test z czytnikiem ekranu (NVDA / VoiceOver). |
| **`NFR-COMP-01`** | **5. Dane, Prywatność i Compliance (Legal & GDPR)** | Regulacje prawne, RODO i Retencja | - **RODO / GDPR:** Rezydencja danych wyłącznie na terenie EOG (np. region AWS `eu-central-1` Frankfurt). Wdrożony mechanizm trwałego usunięcia/anonimizacji danych osobowych na żądanie (`Right to be Forgotten`) w czasie `< 72h`.<br>- **Audit Log:** Niemodyfikowalny dziennik zdarzeń systemowych (kto, kiedy, z jakiego IP zmienił status rekordu lub pobrał dane) przechowywany przez **5 lat** zgodnie z wymogami **ISO/IEC 27001** oraz **SOC 2 Type II**. | Przegląd DPIA (Data Protection Impact Assessment) z Inspektorem Ochrony Danych (DPO) przed włączeniem produkcyjnym. |

---

## 6. Miary Sukcesu, Analityka i Telemetria

`[Instrukcja: Produkt bez wdrożonej telemetrii nie może zostać dopuszczony do wydania produkcyjnego (Definition of Done). W Sekcji 6.1 zdefiniuj hierarchię metryk sukcesu – każda metryka MUSI posiadać wartość bazową (Baseline) oraz cel (Target Value). W Sekcji 6.2 zmapuj konkretne zdarzenia analityczne (Event Tracking), które zasilą te metryki i są bezpośrednio powiązane z wymaganiami z Sekcji 3.]`

### 6.1. Hierarchia Metryk Produktowych i Biznesowych (KPI Matrix)

| Poziom Metryki | Nazwa Metryki (KPI) | Definicja i Formuła Wyliczenia | Baseline (Stan Obecny) | Target Value (Cel po 90 dniach od GA) | Źródło Danych / Narzędzie | Częstotliwość Pomiaru |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **North Star Metric (NSM)** | **Średni Czas Rozwiązania Krytycznej Anomalii (MTTR - Mean Time To Resolution)** | Średni czas (w minutach) od momentu zarejestrowania anomalii (`EVT-002`) do momentu wygenerowania zatwierdzonego pakietu roszczeniowego (`EVT-004`). | `240 minut` (4 godziny pracy manualnej) | `< 15 minut` (Redukcja o 93.7%) | Hurtownia Danych (Snowflake / BigQuery) + Dashboard Amplitude | Ciągły (Agregacja dobowa i tygodniowa) |
| **Metryka Biznesowa #1** | **Wskaźnik Retencji Netto Przychodów (NRR - Net Revenue Retention)** | `(ARR na koniec okresu z kohorty startowej - Churn + Expansion) / ARR na początek okresu * 100%`. | `98%` | `115%` | System Billingowy (Stripe / Chargebee) + CRM (Salesforce) | Miesięczny / Kwartalny |
| **Metryka Biznesowa #2** | **Koszt Obsługi Incydentu na Węzeł (Cost Per Incident Handled)** | Całkowity koszt czasu pracy operatorów `PER-01` i `PER-02` podzielony przez liczbę skutecznie zamkniętych zgłoszeń. | `42.00 EUR / incydent` | `< 8.50 EUR / incydent` | Raporty ERP klienta + Telemetria czasu sesji | Miesięczny |
| **Metryka Produktowa / Behawioralna #1** | **Wskaźnik Skuteczności Synchronizacji Offline (Offline Sync Success Rate)** | `(Liczba paczek danych zsynchronizowanych bez błędu / Całkowita liczba paczek zapisanych w trybie Offline) * 100%`. | `0%` (Brak trybu offline w starej wersji – utrata danych) | `> 99.8%` | Logi telemetryczne klienta mobilnego (`EVT-002`) / Sentry | Ciągły (Alert PagerDuty przy spadku `< 99%`) |
| **Metryka Produktowa / Behawioralna #2** | **Wskaźnik Adopcji Funkcji Jednoklikowego Roszczenia (Feature Adoption Rate)** | `(Liczba incydentów zamkniętych przez wygenerowanie PDF REQ-004 / Całkowita liczba incydentów krytycznych) * 100%`. | `0%` (Funkcja nowa) | `> 75%` | Amplitude / Mixpanel (`EVT-001` vs `EVT-004`) | Tygodniowy |

### 6.2. Specyfikacja Implementacji Zdarzeń Analitycznych (Event Tracking Table)
`[Instrukcja dla Inżynierów: Wszystkie nazwy zdarzeń muszą być zgodne z konwencją snake_case (obiekt_czasownik_w_czasie_przeszłym). Zabrania się przesyłania w ładunku (Payload) jakichkolwiek danych osobowych (PII) typu imię, nazwisko, adres e-mail czy numer telefonu – używaj wyłącznie zanonimizowanych identyfikatorów UUID.]`

| ID Zdarzenia | Nazwa Techniczna Zdarzenia (`event_name`) | Powiązane Wymaganie i Persona | Wyzwalacz (Trigger - Kiedy zdarzenie jest wysyłane) | Struktura Ładunku (JSON Properties / Payload Schema) | Punkt Emisji (Źródło) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`EVT-001`** | `critical_anomaly_displayed` | `REQ-001` / `PER-01` | Zdarzenie emitowane w momencie wyrenderowania wiersza anomalii o priorytecie `CRITICAL` na ekranie operatora i odegrania sygnału ostrzegawczego. | `{"anomaly_id": "UUID", "tenant_id": "UUID", "estimated_loss_eur": "Float", "delivery_latency_ms": "Integer", "filter_preset": "String"}` | Frontend Web (React Telemetry SDK) |
| **`EVT-002`** | `offline_inspection_synced` | `REQ-002` / `PER-02` | Zdarzenie emitowane po otrzymaniu statusu HTTP 201 z backendu potwierdzającego pomyślny zapis paczki danych, która wcześniej oczekiwała w lokalnej kolejce Offline. | `{"inspection_id": "UUID", "device_model": "String", "time_spent_in_offline_queue_sec": "Integer", "photos_count": "Integer", "payload_size_kb": "Integer", "retry_attempts": "Integer"}` | Mobile Client (iOS/Android Background Sync Worker) |
| **`EVT-003`** | `sso_session_revoked_via_scim` | `REQ-003` / `PER-03` | Zdarzenie emitowane przez serwer autoryzacji natychmiast po przetworzeniu webhooka SCIM dezaktywującego konto użytkownika i wyczyszczeniu jego tokenów w bazie Redis. | `{"target_user_uuid": "UUID", "tenant_id": "UUID", "idp_provider": "Enum(okta|entra_id|ping)", "revocation_duration_ms": "Integer", "active_sessions_killed": "Integer"}` | Backend Auth Service (Server-side Event) |
| **`EVT-004`** | `claim_package_generated` | `REQ-004` / `PER-01` | Zdarzenie emitowane w momencie zakończenia kompilacji pliku PDF/ZIP i udostępnienia podpisanego adresu URL (Pre-signed URL) do pobrania przez użytkownika. | `{"claim_id": "UUID", "anomaly_id": "UUID", "generation_time_ms": "Integer", "document_size_bytes": "Integer", "included_attachments_count": "Integer"}` | Backend Document Worker (Server-side Event) |

---

## 7. Moduły Adaptacyjne Specyfiki Produktu (Conditional Architecture Blocks)

`[Instrukcja: Poniższe moduły są blokami warunkowymi. Aktywuj i wypełnij te sekcje, które odpowiadają flagom ustawionym w nagłówku dokumentu (Metadane: is_SaaS, is_Mobile, is_Hardware_IoT). W przypadku produktów hybrydowych (np. ekosystem IoT posiadający chmurę SaaS oraz aplikację mobilną) WSZYSTKIE trzy bloki pozostają aktywne i wiążące dla zespołów inżynieryjnych.]`

---

### `[IF SaaS]` Moduł 7A: Architektura Chmurowa, API i Systemy Rozliczeniowe (Web / B2B SaaS)
`[Instrukcja: Wypełnij tę sekcję, jeśli produkt dostarcza aplikację webową lub platformę usługową w modelu subskrypcyjnym / multi-tenant.]`

| ID Parametru SaaS | Obszar Architektoniczny | Wymaganie Specyficzne dla Domeny SaaS | Standard Techniczny / Kryterium Weryfikacji |
| :--- | :--- | :--- | :--- |
| **`SAAS-API-01`** | **Kontrakt i Wersjonowanie API** | Wszystkie publiczne i partnerskie punkty końcowe REST / GraphQL muszą być wersjonowane w ścieżce URI (np. `/api/v1/...`) i udokumentowane zgodnie ze specyfikacją **OpenAPI 3.1 (Swagger)**. | Złamanie kompatybilności wstecznej (Breaking Change) wymaga utrzymania poprzedniej wersji API przez okres minimum **6 miesięcy (Deprecation Policy)** wraz z nagłówkiem `Sunset` w odpowiedziach HTTP. |
| **`SAAS-API-02`** | **Rate Limiting i Ochrona Zasobów (Throttling)** | Wdrożenie algorytmu *Token Bucket* na bramce API Gateway per `tenant_id` oraz per klucz API, aby zapobiec zjawisku *Noisy Neighbor* (zdegradowaniu usługi przez jednego klienta). | Limit domyślny: `1 000 żądań / minutę` dla planu Standard, `10 000 żądań / minutę` dla planu Enterprise. Przekroczenie zwraca kod **HTTP 429 (Too Many Requests)** z nagłówkiem `Retry-After`. |
| **`SAAS-BILL-01`** | **Silnik Subskrypcji i Bilingu (Entitlements)** | Integracja dwukierunkowa (Webhooks) z operatorem płatności (np. Stripe Billing / Chargebee). Wsparcie dla modelu hybrydowego: stała opłata bazowa (Seat-based) + opłata za zużycie (Usage-based / Metered Billing za liczbę przeprocesowanych anomalii). | W przypadku nieudanej płatności (`invoice.payment_failed`) system uruchamia procedurę *Dunning Management* (okres karencji **14 dni** z banerem ostrzegawczym w UI), po czym przełącza konto w tryb `READ_ONLY` bez usuwania danych. |
| **`SAAS-TEN-01`** | **Izolacja Multi-Tenancy i Onboarding** | Architektura współdzielonej bazy danych z twardą izolacją logiczną (PostgreSQL Row-Level Security - RLS) dla planu Standard oraz opcja izolowanego schematu/instancji (Silo Model) dla klientów Enterprise. | Automatyczny test integracyjny w CI/CD próbujący odczytać zasób `Tenant_B` przy użyciu prawidłowego tokenu JWT należącego do `Tenant_A` (musi zawsze zwrócić HTTP 403/404). |

---

### `[IF MOBILE]` Moduł 7B: Specyfika Urządzeń Mobilnych, OS i Dystrybucji (iOS / Android)
`[Instrukcja: Wypełnij tę sekcję, jeśli produkt obejmuje natywną lub wieloplatformową (React Native / Flutter / Kotlin Multiplatform) aplikację mobilną.]`

| ID Parametru Mobile | Obszar Mobilny | Wymaganie Specyficzne dla Domeny Mobile | Standard Techniczny / Kryterium Weryfikacji |
| :--- | :--- | :--- | :--- |
| **`MOB-OFF-01`** | **Architektura Offline-First i Zarządzanie Stanem** | Pełna separacja warstwy prezentacji od stanu sieci. Lokalna baza danych (SQLite / Realm / WatermelonDB) jest jedynym źródłem prawdy (Single Source of Truth) dla interfejsu użytkownika. | Synchronizacja w tle realizowana przez natywne API systemu: **WorkManager (Android)** oraz **BGTaskScheduler (iOS)**. Maksymalny rozmiar lokalnej bazy danych ograniczony do `250 MB` z polityką czyszczenia LRU (Least Recently Used) dla zsynchronizowanych załączników starszych niż 7 dni. |
| **`MOB-PUSH-01`** | **Powiadomienia Push i Deep Linking** | Integracja z **APNs (Apple Push Notification service)** oraz **FCM (Firebase Cloud Messaging)**. Obsługa powiadomień cichych (Silent Push `content-available: 1`) do wybudzania synchronizacji danych w tle oraz powiadomień krytycznych z obsługą *Universal Links / App Links*. | Kliknięcie powiadomienia Push musi przenieść użytkownika bezpośrednio do konkretnego widoku szczegółów rekordu (Deep Link np. `app://anomalies/uuid-123`) zarówno przy aplikacji zamkniętej (Cold Start), jak i działającej w tle (Warm Start). |
| **`MOB-STORE-01`** | **Zgodność z Wytycznymi App Store i Google Play** | Pełna zgodność z **Apple App Store Review Guidelines** oraz **Google Play Developer Policy**. Wdrożenie mechanizmu wymuszonej aktualizacji (Force Update / Minimum Supported Version) kontrolowanego zdalnie przez Remote Config. | 1. Jeśli aplikacja umożliwia utworzenie konta, musi posiadać widoczną w ustawieniach opcję trwałego usunięcia konta (Wymóg Apple 5.1.1(v)).<br>2. Precyzyjne uzasadnienie uprawnień systemowych w plikach `Info.plist` / `AndroidManifest.xml` (Kamera, Lokalizacja, Pamięć) wyzwalane *Just-In-Time* (dopiero przy próbie użycia funkcji, nie przy pierwszym uruchomieniu). |
| **`MOB-RES-01`** | **Zużycie Baterii i Zasobów Sprzętowych** | Aplikacja nie może powodować nadmiernego drenażu baterii ani przegrzewania urządzenia (Thermal Throttling) podczas ciągłej pracy na hali magazynowej. | Zużycie baterii poniżej `4% na godzinę` aktywnego ekranu; brak ciągłego odpytywania GPS (Polling) na rzecz nasłuchiwania zmian znaczących (Significant Location Change) lub wyzwalania wyłącznie podczas skanowania. |

---

### `[IF HARDWARE/IOT]` Moduł 7C: Inżynieria Sprzętowa, Firmware, Zasilanie i Certyfikacja (Hardware / Embedded / IoT)
`[Instrukcja: Wypełnij tę sekcję, jeśli produkt obejmuje fizyczne urządzenie elektroniczne, czujnik telemetryczny, bramkę brzegową (Edge Gateway) lub oprogramowanie wbudowane (Firmware).]`

| ID Parametru IoT | Obszar Sprzętowo-Układowy | Wymaganie Specyficzne dla Domeny Hardware / IoT | Standard Techniczny / Kryterium Weryfikacji |
| :--- | :--- | :--- | :--- |
| **`IOT-CERT-01`** | **Certyfikacja Regulacyjna i Środowiskowa** | Urządzenie nie może zostać wprowadzone do obrotu ani zamontowane u klienta bez kompletu badań kompatybilności elektromagnetycznej (EMC), bezpieczeństwa radiowego i środowiskowego. | - **Rynek UE:** Certyfikacja **CE** (Dyrektywa radiowa RED 2014/53/UE), zgodność z dyrektywą **RoHS 3** (brak ołowiu i substancji niebezpiecznych) oraz rejestracja **WEEE (BDO)**.<br>- **Rynek USA:** Certyfikacja **FCC Part 15B / 15C**.<br>- **Klasa szczelności obudowy:** Minimum **IP65** (pełna pyłoszczelność i ochrona przed strugą wody) oraz odporność mechaniczna **IK08**; zakres temperatur pracy: od `-20°C do +60°C`. |
| **`IOT-PWR-01`** | **Budżet Energetyczny i Zarządzanie Zasilaniem (Power Budget)** | Optymalizacja profili poboru prądu układu mikrokontrolera (MCU) i modemu komunikacyjnego (BLE / LTE-M / NB-IoT / LoRaWAN) w celu zapewnienia bezobsługowej pracy w terenie. | - Pobór prądu w trybie głębokiego uśpienia (Deep Sleep): `< 15 µA`.<br>- Pobór prądu podczas transmisji radiowej (TX Peak): `< 250 mA` przez maksymalnie `3 sekundy`.<br>- **Minimalny czas pracy na jednym ogniwie (Li-SOCl2 3.6V / 2600 mAh):** Minimum **36 miesięcy** przy częstotliwości raportowania raz na 15 minut. |
| **`IOT-FOTA-01`** | **Aktualizacje Oprogramowania Układowego (FOTA) i Bezpieczeństwo Bootloadera** | Urządzenie musi wspierać zdalną, bezprzewodową aktualizację oprogramowania układowego (**Firmware Over-The-Air - FOTA**) z gwarancją odporności na utratę zasilania w trakcie procesu (Anti-Brick). | - Pamięć Flash podzielona na dwie niezależne partycje w architekturze **Dual-Bank (A/B Partitioning)** z automatycznym wycofaniem (Rollback) do poprzedniej wersji, jeśli nowy obraz nie zgłosi flagi `BOOT_SUCCESS` do układu Watchdog w ciągu `30 sekund`.<br>- **Secure Boot:** Każdy obraz firmware'u musi być podpisany kryptograficznie kluczem prywatnym **ECDSA P-256**; bootloader weryfikuje podpis przed uruchomieniem kodu (zabezpieczenie w układzie sprzętowym Secure Element / TPM, np. ATECC608). |
| **`IOT-TELE-01`** | **Protokoły Komunikacyjne i Buforowanie Brzegowe** | Komunikacja z chmurą zoptymalizowana pod kątem niestabilnych łączy o niskiej przepustowości i wysokich opóźnieniach. | Komunikacja oparta na protokole **MQTT v5.0 over TLS (mTLS - Mutual Authentication z unikalnym certyfikatem X.509 na urządzenie)** lub **CoAP/DTLS**. Wbudowana pamięć nieulotna (SPI NOR Flash / FRAM) przechowująca jako bufor kołowy (Ring Buffer) minimum **10 000 ostatnich ramek pomiarowych** na wypadek utraty zasięgu stacji bazowej. |

---

## 8. Rejestr Ryzyk, Zależności i Bramka Decyzyjna (Sign-Off Matrix)

`[Instrukcja: Przed przekazaniem dokumentu do realizacji (Kick-off deweloperski), zidentyfikuj kluczowe ryzyka techniczne/biznesowe oraz uzyskaj formalną akceptację (Sign-Off) od właścicieli poszczególnych obszarów.]`

### 8.1. Matryca Ryzyk i Plan Mitygacji (RAID Log Extract)

| ID Ryzyka | Opis Ryzyka / Zależności Zewnętrznej | Prawdopodobieństwo (`Niskie/Średnie/Wysokie`) | Wpływ (`Niski/Średni/Krytyczny`) | Strategia Mitygacji (Plan Awaryjny) | Właściciel Ryzyka |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RSK-01` | Opóźnienie w dostarczeniu dokumentacji API przez zewnętrznego dostawcę systemu WMS klienta Enterprise. | Wysokie | Krytyczny | Zbudowanie warstwy adaptera (Anti-Corruption Layer) z serwerem Mock oraz umożliwienie awaryjnego importu paczek danych przez SFTP/CSV w pierwszym miesiącu wdrożenia. | Lead Backend Architect |
| `RSK-02` | Odrzucenie aplikacji mobilnej podczas procesu certyfikacji w Apple App Store z powodu uprawnień do pracy w tle (`MOB-PUSH-01`). | Średnie | Wysoki | Wysłanie wersji Pre-Release (TestFlight External Review) na 3 tygodnie przed planowanym startem GA w celu wcześniejszej weryfikacji przez zespół Apple. | Mobile Tech Lead |

### 8.2. Tabela Akceptacji Dokumentu (Stakeholder Sign-Off)

| Rola w Procesie | Imię i Nazwisko | Status Decyzji (`PENDING / APPROVED / REJECTED`) | Data Decyzji | Komentarz / Warunki Zastrzeżone |
| :--- | :--- | :--- | :--- | :--- |
| **Product Owner / PM** | `[Wpisz Imię i Nazwisko]` | `APPROVED` | `YYYY-MM-DD` | Zakres MVP zweryfikowany. Udział zadań MUST HAVE wynosi 40% (2 z 5 epików). |
| **Principal Systems Architect** | `[Wpisz Imię i Nazwisko]` | `PENDING` | `YYYY-MM-DD` | Oczekiwanie na potwierdzenie limitów przepustowości klastra Kafka dla `REQ-001`. |
| **Security & Compliance Officer** | `[Wpisz Imię i Nazwisko]` | `PENDING` | `YYYY-MM-DD` | Weryfikacja architektury szyfrowania SQLite na urządzeniach mobilnych (`NFR-SEC-01`). |
| **QA & Release Lead** | `[Wpisz Imię i Nazwisko]` | `PENDING` | `YYYY-MM-DD` | Kryteria `Given-When-Then` z Sekcji 3 gotowe do konwersji na skrypty testów automatycznych. |