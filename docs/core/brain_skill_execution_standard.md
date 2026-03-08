# BRAiN Skill Execution Standard

## Standard-Workflow zur Reduktion von LLM-Fehlern

Version: 1.0
Status: Core Standard
Projekt: **BRAiN – Bio-inspired Rational Autonomous Intelligence Network**

---

# 1 Zweck

Dieser Standard definiert den **verbindlichen Ablauf zur sicheren Ausführung von Skills in BRAiN**.

Er reduziert typische Fehler von LLM-Systemen:

* falscher Kontext
* unvollständige Lösungen
* Halluzinationen
* falsche Formatierung
* ungetesteter Code
* Qualitätsprobleme

Der Workflow trennt klar:

```
Kontext → Ausführung → Bewertung → Abschluss
```

---

# 2 Grundprinzip

Jeder Skill in BRAiN folgt diesem Ablauf:

```
GROUNDING
↓
EXECUTION
↓
EVALUATION
↓
FINALIZATION
```

Bei Fehlern erfolgt eine **gezielte Rückkopplung**.

---

# 3 Workflow

## 1 Grounding Phase

Ziel: Kontext vollständig verstehen.

Aufgaben:

* Problem definieren
* Eingaben validieren
* Anforderungen klären
* relevante Daten sammeln
* Dokumentation / Quellen prüfen
* Einschränkungen erkennen

Beispiele:

### Übersetzung

* Was wird übersetzt?
* Zielsprache
* gewünschter Stil
* Terminologie
* Format (HTML / Markdown / Text)

### Coding

* Issue analysieren
* relevanten Code identifizieren
* Dokumentation lesen
* vorhandene Tests prüfen

Output der Phase:

```
task_context
requirements
constraints
success_criteria
```

---

## 2 Execution Phase

Ziel: Aufgabe ausführen.

Beispiele:

* Übersetzung generieren
* Code implementieren
* Daten analysieren
* Inhalte erzeugen

Die Execution Phase darf **keine endgültige Entscheidung treffen**.

Das Ergebnis ist ein **Entwurf**.

Output:

```
draft_result
```

---

## 3 Evaluation Phase

Der Evaluator prüft das Ergebnis anhand definierter Kriterien.

Die Evaluation ist **regelbasiert** und nicht allgemein.

---

### Evaluation Beispiel: Übersetzung

Prüfpunkte:

* Bedeutung korrekt übertragen
* Grammatik korrekt
* Stil eingehalten
* Terminologie konsistent
* Formatierung unverändert
* keine Inhalte ausgelassen
* keine Inhalte hinzugefügt

---

### Evaluation Beispiel: Coding

Prüfpunkte:

* löst der Code das Issue
* keine Regression
* Code sauber und wartbar
* Sicherheitsprobleme ausgeschlossen
* Tests vorhanden oder ergänzt
* bestehende Tests bestehen

---

### Evaluation Output

```
evaluation_score
issues_detected
error_classification
```

---

# 4 Fehlerklassifikation

Fehler werden kategorisiert.

```
context_error
execution_error
quality_error
format_error
test_error
```

Dadurch kann BRAiN gezielt reagieren.

---

# 5 Korrekturzyklus

Wenn Fehler erkannt werden:

```
Evaluation
↓
Fehlerklassifikation
↓
gezielte Korrektur
↓
erneute Evaluation
```

Maximale Anzahl der Iterationen:

```
max_review_cycles = 3
```

Dadurch werden Endlosschleifen verhindert.

---

# 6 Spezialisierte Reviewer

Anstatt viele generische Reviews durchzuführen, werden spezialisierte Evaluatoren verwendet.

Beispiele:

### Coding

* correctness reviewer
* security reviewer
* maintainability reviewer
* test reviewer

### Übersetzung

* meaning reviewer
* grammar reviewer
* terminology reviewer
* style reviewer

---

# 7 Stop-Kriterien

Der Prozess endet wenn eine der Bedingungen erfüllt ist:

```
evaluation_score ≥ required_threshold
ODER
max_review_cycles erreicht
ODER
budget_limit erreicht
ODER
time_limit erreicht
```

Bei Abbruch kann eine Eskalation erfolgen:

```
human_review
```

---

# 8 Finalization Phase

Wenn die Evaluation erfolgreich ist:

* Ergebnis speichern
* Logs erstellen
* Skill Run dokumentieren
* optional veröffentlichen

Beispiele:

```
DB speichern
Git commit
API Antwort
Content veröffentlichen
```

---

# 9 Standard Skill Pipeline

Der vollständige Ablauf:

```
GROUNDING AGENT
↓
EXECUTION AGENT
↓
EVALUATION AGENT
↓
FINALIZING AGENT
```

Bei Fehlern:

```
Evaluation → gezielte Korrektur → Execution
```

---

# 10 Verbindung zur Skill Engine

Die Skill Engine nutzt diesen Standard für:

* Skill Ausführung
* Agentenarbeit
* Code Generierung
* Content Generierung
* Automatisierung

Alle Skills müssen diesen Ablauf implementieren.

---

# 11 Leitprinzip

Der wichtigste Grundsatz lautet:

> **Ein LLM-Ergebnis gilt erst als gültig, wenn es die Evaluation bestanden hat.**

---

# 12 Kurzform des Standards

```
Grounding → Execution → Evaluation → Finalization
```

Mit:

* klaren Prüfkriterien
* spezialisierter Evaluation
* begrenzten Korrekturzyklen

---

# 13 Zweck für BRAiN

Dieser Standard sorgt dafür, dass BRAiN:

* zuverlässiger arbeitet
* weniger Halluzinationen produziert
* stabileren Code erzeugt
* reproduzierbare Ergebnisse liefert

---

Ende des Dokuments
