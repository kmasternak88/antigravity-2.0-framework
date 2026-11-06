# Profil AgenticPayload Core

Ten adapter używa ustaleń rozmowy: CMS+commerce, ChangeSet, PostgreSQL inventory ledger, Stripe recovery, OIDC, REST/MCP, admin/storefront i implementacyjny DAG S01–S27. Wcześniej wygenerowany blueprint nie jest tu automatycznie dołączony ani odtworzony jako rzekomo odczytany plik. Umieść zatwierdzony dokument w repo przed projektowym Spec Lock.

## Invariants projektu

- Jedna autorytatywna DB dla zapasu; role runtime bez bezpośredniego DML saldo/ledger.
- Tenant-scoped FK i RLS oraz testy roli runtime.
- Plan ChangeSet bez DML/sieci; commit rewaliduje rewizje, schemat i permissions.
- Published revision oddzielona od draft.
- Timeout Stripe=uncertain i reconcile, nie automatyczny release stock.
- Inbox durable przed2xx; dedupe eventId i efektu biznesowego.
- Refund nie zwiększa automatycznie magazynu.
- Pieniądze bigint w domenie/string minor w API.
- Client credentials i PKCE to różne profile integracji MCP.

## Mapowanie etapów na zadania

S01–S03 toolchain/contracts/infra → S04–S07 DB/RLS/OIDC/idempotency → S08–S11 schema/content/planner/commit → S12–S14 catalog/inventory/cart → S15–S18 durable jobs/Stripe/reconcile/refund → S19–S21 outbound integrations/export/MCP → S22–S23 admin/storefront → S24–S27 security/load/restore/release.

Zachowaj szczegółowy DAG oryginalnego blueprintu przy generowaniu tasks.json; powyższe grupowanie nie jest dowodem, że wszystkie wewnętrzne zależności odczytano. Task lockfile, FK/RLS functions i API schemas przechodzą single integrator. Nie uruchamiaj równolegle refactorów schematów i kodu, który zakłada poprzednie kontrakty.

## Suites wymagane przed produktem R1

Build/typecheck/lint; pure money/policy/planner; migrations/runtime-role/RLS; inventory race; cart/quote; payment unknown-result/cancel race/duplicate/out-of-order/late success; refund; webhook SSRF/retry; media XSS/upload; export/import; SDK MCP HTTP+stdio; admin/store UI; provider staging Stripe/Keycloak; restore i load.

Dodaj rzeczywiste argv do config checks dopiero po sprawdzeniu package scripts. Nie generuj PASS dlatego, że blueprint zawiera komendę. Ustaw profile critical dla inventory/payments/authz/DB migrations i protected approval dla rollout.
