import sys, pathlib
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import unittest
from pathlib import Path
import tempfile
from tools.prd_parser import PRDParser, PRDValidationError, ParsedPRD, Requirement, PRDMetadata

class TestPRDParser(unittest.TestCase):
    def setUp(self):
        self.parser = PRDParser()
        self.sample_content = """
# [SZABLON] Product Requirements Document (PRD)

> **Metadane Dokumentu (System Header)**
> - **ID Dokumentu:** `PRD-2026-001`
> - **Wersja Schematu:** `v3.2.0-MODULAR`
> - **Status Dokumentu:** `APPROVED`
> - **Architekt / PM:** `John Doe, PM`
> - **Lead Inżynieryjny:** `Jane Doe, Lead`
> - **Klasyfikacja Produktu (Flagi Aktywacji Bloków z Sekcji 7):** `is_SaaS: [TRUE]`, `is_Mobile: [FALSE]`, `is_Hardware_IoT: [FALSE]`
> - **Data Ostatniej Aktualizacji:** `2026-01-01`

## 2. Grupa Docelowa i Aktorzy Systemowi
| ID Persony | Nazwa / Rola | Kontekst |
| :--- | :--- | :--- |
| **`PER-01`** | Manager | Test |

## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title 1 | Story 1 | `PER-01` | **MUST HAVE** | Given-When-Then 1 | `EVT-01` | High |
| **`REQ-002`** | Title 2 | Story 2 | `PER-01` | **SHOULD HAVE** | Given-When-Then 2 | `EVT-02` | Low |
| **`REQ-003`** | Title 3 | Story 3 | `PER-02` | **COULD HAVE** | Given-When-Then 3 | `EVT-03` | Low |
| **`REQ-004`** | Title 4 | Story 4 | `PER-02` | **WON'T HAVE** | Given-When-Then 4 | `EVT-04` | Low |

## 4. Przepływy Użytkownika
### 4.2. Obsługa Krytycznej Anomalii i Zapisu Terenowego (`FLOW-01`)
Krytyczny przepływ, np. `ERR-FLOW-01` w razie błędu.

## 5. Wymagania Niefunkcjonalne
| ID | Kategoria | Wymaganie |
| :--- | :--- | :--- |
| **`NFR-01`** | Security | TLS 1.3 |

## 6. Miary Sukcesu
### 6.1. Hierarchia Metryk
| ID | Nazwa | Baseline | Target |
| :--- | :--- | :--- | :--- |
| **`KPI-01`** | MTTR | 48h | 2h |

### 6.2. Specyfikacja Zdarzeń
| ID | Nazwa | Wyzwalacz | Właściwości |
| :--- | :--- | :--- | :--- |
| **`EVT-01`** | Click | Button | {} |

## 7. Moduły
## 8. Rejestr Ryzyk
### 8.1. Matryca Ryzyk
| ID | Opis | Prawdopodobieństwo | Wpływ | Strategia | Właściciel |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RSK-01` | Risk | Wysokie | Krytyczny | Mitigation | PM |

### 8.2. Tabela Akceptacji
"""

    def test_parse_markdown_comprehensive(self):
        prd = self.parser.parse_markdown(self.sample_content)
        self.assertEqual(prd.metadata.doc_id, "PRD-2026-001")
        self.assertTrue(prd.metadata.is_saas)
        self.assertEqual(len(prd.requirements), 4)
        self.assertEqual(len(prd.personas), 1)
        self.assertEqual(prd.personas[0].id, "PER-01")
        self.assertEqual(len(prd.nfrs), 1)
        self.assertEqual(prd.nfrs[0].id, "NFR-01")
        self.assertEqual(len(prd.kpis), 1)
        self.assertEqual(prd.kpis[0].id, "KPI-01")
        self.assertEqual(len(prd.events), 1)
        self.assertEqual(prd.events[0].id, "EVT-01")
        self.assertEqual(len(prd.risks), 1)
        self.assertEqual(prd.risks[0].id, "RSK-01")

    def test_validate_moscow_limit_pass(self):
        prd = self.parser.parse_markdown(self.sample_content)
        self.assertTrue(self.parser.validate_moscow_limit(prd))

    def test_validate_moscow_limit_fail(self):
        fail_content = self.sample_content.replace(
            "## 4. Przepływy Użytkownika",
            "| **`REQ-005`** | Title 5 | Story 5 | `PER-01` | **MUST HAVE** | Given-When-Then | `EVT-05` | High |\n| **`REQ-006`** | Title 6 | Story 6 | `PER-01` | **MUST HAVE** | Given-When-Then | `EVT-06` | High |\n\n## 4. Przepływy Użytkownika"
        )
        prd = self.parser.parse_markdown(fail_content)
        # 3 out of 6 is 50%, should fail
        with self.assertRaises(PRDValidationError):
            self.parser.validate_moscow_limit(prd)

    def test_transpile_to_specs(self):
        prd = self.parser.parse_markdown(self.sample_content)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            files = self.parser.transpile_to_specs(prd, out_dir)
            self.assertIn("01_PRODUCT_REQUIREMENTS.md", files)
            self.assertTrue(files["01_PRODUCT_REQUIREMENTS.md"].exists())

    def test_to_dag_task_atoms(self):
        prd = self.parser.parse_markdown(self.sample_content)
        atoms = self.parser.to_dag_task_atoms(prd)
        self.assertEqual(len(atoms), 4)
        self.assertEqual(atoms[0]["id"], "task_REQ-001")
        self.assertEqual(atoms[1]["depends_on"], ["task_REQ-001"])

if __name__ == '__main__':
    unittest.main()
