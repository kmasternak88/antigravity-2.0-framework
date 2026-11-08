---
name: cl-page
description: "CADRE v8.3 Page & Template Assembly Engine. Deterministyczny montaż szablonów stron dla WordPress/WooCommerce PHP, React TSX, Vue SFC oraz HTML. Eliminuje halucynacje ścieżek, wstrzykuje sloty i wymusza taksonomię klas CSS."
version: 8.0.0
---

# /cl-page — CADRE Multi-Adapter Page & Template Assembly Engine (Antigravity v8.0)

Komenda `/cl-page` umożliwia agentom LLM i programistom deterministyczny montaż kompletnych stron, widoków i szablonów bez zgadywania ścieżek importów, bez pomijania powiązanych stylów/skryptów i z pełną gwarancją spójności taksonomicznej (SLT/Bramka G4).

Obsługuje natywnie środowiska:
1. **WordPress & WooCommerce (PHP):** Bezpieczne szablony z `defined('ABSPATH') || exit;`, `get_header()`, sekcjami slotów `get_template_part('template-parts/<slug>')` oraz `get_footer()`.
2. **React & Next.js (TypeScript TSX):** Silnie typowane komponenty stron z importami z rejestru, modelami Props i hookami stanu.
3. **Vue 3 SFC:** Szablony `<template>`, `<script setup lang="ts">` oraz zintegrowane powiązania `:prop="val"`.
4. **HTML5 Semantic:** Szablony semantyczne ze slotami sekcji.

---

## 🧭 KIEDY UŻYWAĆ SKILLA?

Używaj `/cl-page` zawsze, gdy:
1. Budujesz nową stronę, widok lub szablon (`Page`, `Template`, `View`, `Screen`).
2. Generujesz szablon WooCommerce/WordPress na podstawie kontraktu blueprint (np. koszyk, checkout, catalog, my-account).
3. Dołączasz komponenty do slotów istniejącej strony (np. `OrderSummary`, `PaymentForm` do `CheckoutPage`).
4. Weryfikujesz poprawność importów i klas CSS przed zgłoszeniem zadania do przeglądu G5.
5. Chcesz naprawić błędy brakujących importów jednym poleceniem (`wire-template`).

---

## 🚀 PROTOKÓŁ WYKONAWCZY (KROK PO KROKU)

### Krok 1: Weryfikacja lub Utworzenie Kontraktu Blueprintu
Sprawdź, czy w `specs/blueprints/` istnieje kontrakt strony (np. `specs/blueprints/checkout.blueprint.json` lub `specs/blueprints/cart.blueprint.json`).

#### Przykład Blueprintu dla WooCommerce / WordPress PHP:
```json
{
  "$schema": "./page.blueprint.schema.json",
  "pageId": "pages.checkout",
  "title": "Zamówienie i Płatność",
  "targetFile": "templates/page-checkout.php",
  "adapter": "woocommerce",
  "taxonomy": {
    "cssPrefix": "cw-checkout-"
  },
  "slots": {
    "order_review": {
      "order": 1,
      "components": [
        { "component": "OrderSummary", "templatePart": "template-parts/checkout/order-summary" },
        { "component": "PaymentGateways", "templatePart": "template-parts/checkout/payment-gateways" }
      ]
    }
  }
}
```

#### Przykład Blueprintu dla React / TypeScript:
```json
{
  "$schema": "./page.blueprint.schema.json",
  "pageId": "pages.checkout",
  "title": "Zamówienie i Płatność",
  "targetFile": "src/pages/CheckoutPage.tsx",
  "adapter": "react-typescript",
  "taxonomy": {
    "cssPrefix": "cw-checkout-",
    "viewModelType": "CheckoutPageProps",
    "stateStoreHook": "useCheckoutStore"
  },
  "slots": {
    "main_content": {
      "order": 1,
      "components": [
        { "component": "OrderSummary", "propBindings": { "cart": "props.cart" } }
      ]
    }
  }
}
```

---

### Krok 2: Deterministyczny Scaffolding Strony (AOT)
Zamiast ręcznie pisać pliki szablonów, uruchom generator CADRE v8.3.
Silnik akceptuje argument pozycyjny lub nazwany `--blueprint`, a także bezpośrednią ścieżkę do pliku:

```powershell
# 1. Argument pozycyjny (najszybszy)
python .governance/bin/gov.py scaffold-page checkout

# 2. Argument nazwany z opcjonalną ścieżką wyjściową
python .governance/bin/gov.py scaffold-page --blueprint checkout --out templates/custom-checkout.php

# 3. Bezpośrednia ścieżka do pliku blueprintu
python .governance/bin/gov.py scaffold-page specs/blueprints/cart.blueprint.json
```

Polecenie:
- Rozpoznaje adapter (`woocommerce`, `php`, `react-typescript`, `vue`, `html`).
- Dla PHP: generuje bezpieczny szablon WordPress z `defined('ABSPATH') || exit;`, `get_header()`, sekcjami slotów i wywołaniami `get_template_part()`.
- Dla React/TSX: wstrzykuje importy symboli z `.governance/registry/components.json` i powiązane arkusze stylów z `.governance/registry/assets.json`.
- Aktualizuje SSoT w `specs/03_DATA_DICTIONARY.md`.

---

### Krok 3: Automatyczne Wstrzykiwanie Zależności (Wiring dla React/TSX)
Jeśli zmodyfikowałeś kod szablonu i użyłeś nowego komponentu z rejestru:
```powershell
python .governance/bin/gov.py wire-template --file src/pages/CheckoutPage.tsx
```
Silnik wykryje użyty tag `<ComponentName>` i automatycznie dopisze brakujący `import` na górze pliku.

---

### Krok 4: Weryfikacja AST Bramki G4
Przed zakończeniem zadania upewnij się, że szablon spełnia rygorystyczne kryteria CADRE:
```powershell
# Sprawdzenie konkretnego pliku
python .governance/bin/gov.py check-templates --file templates/page-checkout.php

# Lub sprawdzenie wszystkich szablonów w zadaniu
python .governance/bin/gov.py check-templates --task task-checkout-page
```

Wymagania bramkowe Bramki G4:
- **Zero Ghost Components:** Każdy użyty komponent JSX musi posiadać poprawny import z rejestru (pomijane dla plików PHP/HTML).
- **Taksonomia CSS:** Wszystkie klasy CSS muszą zaczynać się od wymaganego prefiksu (np. `cw-`). Tagi dynamiczne PHP (`<?php echo esc_attr(...) ?>`, `<?= ... ?>`) są automatycznie sanityzowane i nie wywołują fałszywych błędów.
- **Limit wielkości (SRP):** Szablon strony (Page Orchestrator) nie może przekraczać 60 linii kodu — orkiestruje wyłącznie sloty i komponenty potomne.

---

## 📋 REGUŁY ARCHITEKTONICZNE CADRE v8.3

1. **Szablon Strony to Wyłącznie Orkiestrator:** Strona nie zawiera logiki biznesowej ani surowych zapytań SQL/API — montuje jedynie sloty z komponentami podrzędnymi.
2. **Adapter-Aware Scaffolding:** Dobieraj adapter (`woocommerce`, `php`, `react-typescript`, `vue`) odpowiadający architekturze Twojego projektu.
3. **Pojedyncze Źródło Prawdy (SSoT):** Zależności komponentów i stylów muszą być zarejestrowane w `.governance/registry/`.
4. **Nazewnictwo:** Plik strony React MUSI kończyć się sufiksem `Page` (np. `CheckoutPage.tsx`), a szablony PHP powinny stosować konwencję WordPress/WooCommerce (np. `templates/page-checkout.php`).

Wyjście: plik/raport z aktualnym statusem i zarejestrowanymi komponentami w `specs/03_DATA_DICTIONARY.md`.
