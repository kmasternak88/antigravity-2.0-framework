# Antigravity Ultra v8.3 - Jules Deployment Management

Niniejszy dokument opisuje rygorystyczny mechanizm zarządzania wdrożeniami chmurowymi (Cloud Execution Loop) w ekosystemie Antigravity Ultra v8.3, gdzie **Antigravity (Orchestrator)** przejmuje pełną kontrolę zarządczą nad procesem (Sovereign Orchestrator), a **Google Jules** funkcjonuje jako wykonawca chmurowy (Cloud Builder & Deployment Engine).

## 1. 9-Stanowa Maszyna Stanów Wdrożenia

Każde wdrożenie przechodzi przez rygorystyczną, 9-stanową maszynę stanów (Deployment State Machine):

1. **DEPLOYMENT_INCEPTION**: Inicjacja zgłoszenia wdrażania; Antigravity analizuje manifest operacyjny.
2. **MCP_DISPATCH**: Orkiestrator przekazuje zlecenie wdrożenia do agenta Jules poprzez protokół FastMCP.
3. **SOCRATIC_PLAN_AUDIT**: Jules generuje szczegółowy plan (manifest) wdrożenia, który jest poddawany Sokratejskiemu Audytowi przez Task Supervisora (zob. Wymogi Audytu Planu poniżej).
4. **CLOUD_EXECUTION**: Po zatwierdzeniu (i tylko wtedy) Jules wykonuje infrastrukturę lub proces CI/CD w chmurze (np. Docker build, Terraform apply).
5. **EVIDENCE_HARVEST**: Pobranie artefaktów i logów (dowodów) ze środowiska wdrożeniowego.
6. **MUTATION_AUDIT**: Weryfikacja dowodów za pomocą asercji (Testy Dymne, Health Checki, weryfikacja zero-downtime).
7. **SELF_HEALING_LOOP**: W przypadku odrzucenia dowodów lub błędu, pętla naprawcza (max 3 cykle), wykorzystująca `FEEDBACK_PACKET.json`.
8. **G7_RELEASE_SEAL**: Zatwierdzenie (Operational Release) - zamrożenie wdrożenia z kryptograficznym odciskiem w manifestach.
9. **POST_DEPLOY_VERIFY**: Dodatkowy, niezależny nadzór nad funkcjonowaniem środowiska po pełnym rolloucie.

## 2. Protokół Delegowania Zadań Wdrożeniowych

Antigravity zarządza operacjami poprzez `tools/jules_bridge.py` z zachowaniem zasady *evidence-first*.

* **Środowiska chmurowe**: Jules może operować m.in. na kontenerach (Docker), Google Cloud Run, GitHub Actions, czy na bezpośrednich wdrożeniach (Caddy/VPS).
* **Zero-Downtime Rolling Updates**: Wszystkie plany wdrożenia muszą deklarować metodę wymiany wersji z zerowym przestojem (np. blue-green deployment).
* **Migracje baz danych**: Wdrożenia schematów są zablokowane za asercjami i dedykowanymi strategiami rollbacku.

## 3. SecretShield i Granice Bezpieczeństwa

* **Hermetyczna izolacja środowisk**: Agenci operują w oddzielnych kontenerach/sesjach. Zmiany nie wyciekają poza ich zakres (*blast radius*).
* **Zakaz wycieku tokenów/kluczy**: Jules i Antigravity operują na zredagowanych logach (Redaction API). Żadne sekrety (API Keys, Hasła, Certyfikaty) nigdy nie trafiają do logów systemowych (`console.log`, stdout) ani repozytorium kodu.
* **Chronione Konfiguracje**: Pliki produkcyjne (np. z hasłami, URL) znajdują się w odseparowanej przestrzeni niedostępnej dla planów agenta bez explicit zgody (G2).

## 4. Sokratejski Audyt Planu Wdrożenia (Socratic Plan Audit)

Każdy plan musi zostać zatwierdzony przez nadrzędnego Supervisora (Antigravity). Weryfikacja polega na:
- Obecności **procedury rollbacku** w przypadku awarii (wraz z testami).
- Sprawdzeniu **testów dymnych** (smoke tests) przed pełnym przepięciem ruchu.
- Potwierdzeniu strategii **Zero-Downtime**.
- Analizie **nienaruszalności chronionych plików konfiguracyjnych** (nie wolno ich nadpisywać bez osobnego zatwierdzenia).