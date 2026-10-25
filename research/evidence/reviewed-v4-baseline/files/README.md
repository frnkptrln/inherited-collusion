# Inherited Collusion through Agent Handoffs

*A Controlled Audit of Instructed Allocation Transfer*

**Frank Peterlein · Independent researcher**  
Apart AI Collusion Research Sprint, 23.–25. Oktober 2026.

**Übergaben übertrugen schädliche Zuteilungsmuster auf neutrale Nachfolger. Ein Prüfhinweis verminderte den Schaden für außenstehende Agenten; auf gemeinsam vollständigen Fällen gab es jedoch ebenso viele Doppelbelegungen wie ohne Notizen.** Das ist ein Befund aus einer kleinen, transparenten Aufgabe mit ausdrücklich instruierten Vorgängern; kein Nachweis spontaner Kollusion.

Die ursprüngliche Auswertung enthält **360 von 512 geplanten gültigen Episoden**. Die später beschlossene Formatergänzung erhöht die Abdeckung auf **439/512**, verwendet dabei vorhandene Antworten weiter und zählt sie nicht als zusätzliche unabhängige Beobachtungen. Von den 73 fehlenden oder ungültigen Episoden der ergänzten Auswertung entfallen 62 auf vier nach Zeitüberschreitungen gestoppte Fälle und 11 auf einen verbliebenen Formatstopp. Die verantwortliche Stelle der Zeitüberschreitungen ist nicht lokalisiert; diese Ausfälle sind keine beobachteten Fehlentscheidungen der Modelle.

| Population | Modell | Gültige Episoden / geplant | Gemeinsamer Schaden: p0-Notizen minus Sachinformationen | Vollständige Fallvergleiche / geplant |
|---|---|---:|---:|---:|
| V4 strict | Qwen3.6-35B-A3B | 127/256 | +0,50 | 1/8 |
| V4 strict | GPT-OSS-120B | 233/256 | +0,43 | 7/8 |
| V4F ergänzt | Qwen3.6-35B-A3B | 206/256 | +0,50 | 5/8 |
| V4F ergänzt | GPT-OSS-120B | 233/256 | +0,43 | 7/8 |

Diese Unterschiede mitteln vollständige Fallvergleiche; sie sind keine geschätzten Häufigkeiten für eine allgemeine Modellpopulation. Die geringe ursprüngliche Qwen-Abdeckung lässt über alle geplanten Slots auch die Gegenrichtung zu. Für GPT-OSS und das ergänzte Qwen bleiben die positiven Richtungen innerhalb der endlichen Aufgabenmöglichkeiten auch bei ungünstigster Ergänzung fehlender Werte bestehen. Das ist eine logische Sensitivitätsprüfung, kein Signifikanztest.

Der Prüfhinweis senkt den gemeinsamen Schaden in der ergänzten Auswertung um **0,50 für Qwen** und **0,42 für GPT-OSS** auf fünf beziehungsweise sechs in beiden Zielbedingungen vollständigen Fällen. Die Leistung bei legitimen Vorgängerzielen sinkt dort nicht. Bei schädlichen Vorgängerzielen entstehen jedoch häufiger Doppelbelegungen: Der Teamnutzen fällt um **84,2 beziehungsweise 78,4 Punkte**, die Zahl unterschiedlicher erledigter Aufgaben jeweils um **0,5**. Der getestete Prüfhinweis ist damit gegenüber passenden schädlichen Notizen nicht koordinations- oder kostenneutral. Eine zusätzliche, ausdrücklich nachträgliche Prüfung vom 24. Oktober 2026 zeigt jedoch: Auf genau diesen gemeinsamen Fällen treten mit Prüfhinweis ebenso viele Doppelbelegungen auf wie ohne Notizen (Qwen jeweils 5/10, GPT-OSS jeweils 6/12; mit passenden schädlichen Notizen jeweils null). A und B haben identische Kosten und zwei gleich gute sichere Gesamtpläne. Das Ergebnis ist daher vereinbar mit dem Verlust einer gemeinsamen Konvention ohne koordinierte Ersatzregel; ein unvermeidlicher Konflikt zwischen Schutz und Zusammenarbeit ist nicht belegt. Ein Prüfhinweis zusammen mit einer neutralen gemeinsamen Auswahlregel wurde noch nicht getestet. Auch eine einzelne Notiz kann außenstehende Agenten benachteiligen, ohne den binären gemeinsamen Schadensindikator auszulösen.

Die vorab festgelegte Kontrolle tatsächlicher Notiznutzung besteht Qwen erst in der ergänzten Auswertung: beide legitimen Konventionen jeweils **14/16** statt benötigter 12/16. GPT-OSS erreicht **9/16 und 4/16**; seine Notizen enthalten häufig unklare oder falsche Empfängeranweisungen. Diese Schwäche des gesamten Übergabekanals begrenzt die Interpretation und erlaubt keinen isolierten Vergleich der Nachfolgerfähigkeiten.

Der Bericht wurde am **24. Oktober 2026** redaktionell überprüft: technische Einzelheiten stehen überwiegend im Anhang; fehlende Daten und die nachträgliche Formatanpassung bleiben im Haupttext sichtbar. Zwei kleinere Beschreibungsfehler der Vorstudien beziehungsweise des Einfrierens wurden korrigiert. Die eingefrorenen Daten, ursprünglichen Analysen und bisherigen Ergebniszahlen wurden dabei nicht verändert. Die erste ausgelieferte Berichtsfassung bleibt im ursprünglichen Paket erhalten.

## Was untersucht wurde

Zwei ausdrücklich instruierte Vorgänger führten ihre vorgegebene Zuteilung aus und schrieben anschließend eigene Übergabenotizen. Frische A-/B-Nachfolger erhielten neutrale gemeinsame Ziele und ausschließlich die jeweils für ihre Rolle bestimmte Notiz. C und D wurden durch eine feste, kostenminimierende Fortsetzung simuliert. Die vollständigen Konsequenzen aller 16 A-/B-Entscheidungen waren öffentlich sichtbar.

Festgelegt waren zwei Modelle über denselben Anbieter, acht Aufgabenfälle pro Modell, schädliche und legitime Vorgängerziele, acht Notizbedingungen und zwei Nachfolgerdurchläufe pro Zelle: **512 geplante gemeinsame Episoden**. Die zwei Wiederholungen sind innerhalb eines Falls und seiner Notizen verschachtelt; sie sind keine 512 unabhängigen Aufgaben. Modellvergleiche vermischen Unterschiede beim Schreiben und Verarbeiten der Notizen.

Die Bedingungen waren Sachinformationen allein; zwei Notizen aus Ursprung 00 beziehungsweise 11; nur die A- oder B-Notiz; gekreuzte Ursprünge 01 und 10; sowie Ursprung 00 mit identischem Prüfhinweis in beiden Zielbedingungen. Der Ursprung einer Notiz garantiert keine semantisch passende Vereinbarung. Falsche Behauptungen, unklare Rollen und andere inhaltliche Fehler blieben unverändert in der primären Notizlieferung.

## Zwei getrennte Auswertungen

**V4 strict** ist das ursprüngliche, vor Nachfolgeraufrufen lokal eingefrorene Verfahren. Seine Formatabbrüche und fehlenden Beobachtungen bleiben erhalten.

**V4F** ist die ausdrücklich nach Beginn der Erhebung beschlossene Formatergänzung. Sie akzeptiert zusätzlich genau einen vollständigen äußeren Markdown-JSON-Block. Der Inhalt, sämtliche sachlichen Prüfungen, Fälle, Prompts, Notizen und Erzeugungsparameter bleiben unverändert. Bestehende Antworten werden bytegenau wiederverwendet; nur zuvor nicht angefragte Slots dürfen neu ausgeführt werden. Ungeklärte Anbieteraufrufe werden niemals wiederholt und sperren neue Anfragen im betroffenen Fall. Bereits belegte Episoden bleiben erhalten.

Die ergänzte Auswertung ist beschreibende Evidenz unter einer offengelegten Änderung, keine unveränderte Bestätigungsstudie. Beide Versionen teilen Antworten und sind keine unabhängigen Replikationen. Das lokale Einfrieren ist keine öffentliche Präregistrierung. Bei der Änderungsentscheidung waren technische Fehler und einzelne Antwortinhalte bekannt. Nach dem Einfrieren wurden bei einer technischen Diagnose versehentlich einzelne Qwen205-Ergebnisse und ein partieller Fallkontrast sichtbar; dies ist in [diesem Beleg](docs/v4f-outcome-visibility-note.json) dokumentiert. Darauf folgte keine Änderung der Regeln oder Laufplanung. Modellweite Effekte wurden erst nach Abschluss beider Datensätze ausgewertet.

## Bericht und Belege

- Aktueller Bericht: [PDF](output/report-v4/inherited-collusion-v4.pdf), [bearbeitbare DOCX](output/report-v4/inherited-collusion-v4.docx).
- Originale Auswertung: [V4 strict](output/analysis-v4/analysis.json).
- Ergänzte Auswertung mit Herkunftsprüfung und Missingness-Grenzen: [V4F](output/analysis-v4f/analysis.json).
- Protokolle: [V4](docs/v4-protocol.md), [V4F-Ergänzung](docs/v4f-protocol.md), [Entscheidungsgeschichte](docs/study-history.md).
- Rohantworten, Anfragen, Zeitstempel, Quellstände und Annotationen: `runs/v4-*` und `runs/v4f-*`.
- Frühere fehlgeschlagene Machbarkeitsversuche: unverändert unter `output/report/`, `output/analysis/`, `runs/hf-pilot-*` und `runs/v3-pilot-*`.

## Kosten und Budget

Für V4 und V4F zusammen wurden **1.249 eindeutige Anfragen** reserviert und **1.245 Antworten** gespeichert; vier Anbieteraufrufe blieben ungeklärt und wurden nicht wiederholt. V4F fügte 170 zuvor nicht angefragte Slots hinzu. Seine Kostensumme enthält die ursprünglichen V4-Aufrufe bereits genau einmal.

Die gespeicherten Anbieter-Nutzungsangaben ergeben für diese Phase eine Schätzung von **1,879012307 US-Dollar**. Die früheren Versuche kommen auf **0,04366364 US-Dollar**; insgesamt also **rund 1,92 US-Dollar**. Das sind keine Rechnungsbeträge. Insbesondere für die vier ungeklärten Aufrufe liegt keine gespeicherte Antwortnutzung vor; mögliche Belastungen werden nicht als null angenommen.

Die aktuelle Phase hat **7,282 US-Dollar reserviert**, bei einer festgelegten Phasenobergrenze von **8,328 US-Dollar**. Zusammen mit der historischen Budgetzuweisung von 1,594 US-Dollar sind **9,922 US-Dollar zugewiesen**, innerhalb der genehmigten ungefähr 15 US-Dollar. Reservierungen und Budgetzuweisungen sind keine tatsächlichen Ausgaben.

## Ohne Modellzugang nachprüfen

Die folgenden Befehle analysieren ausschließlich lokale Belege. Sie starten keine Modellanfragen. `python` muss auf eine geeignete Python-3-Installation zeigen; verwendet wurde Python 3.14.8.

```sh
python -B scripts/test_offline.py --out /tmp/collusion-offline-tests
python -B scripts/analyze_v4_study.py --project . --out output/recomputed-v4.json
python -B scripts/analyze_v4f_study.py --project . --strict-analysis output/recomputed-v4.json --out output/recomputed-v4f.json
```

Für das Testprotokoll einen noch nicht vorhandenen Ausgabeordner wählen. Die Tests laufen je Modul in einem eigenen Prozess, damit die Formatanpassung keine ursprünglichen Parserprüfungen beeinflusst. Strict- und V4F-Analysen ebenfalls in getrennten Prozessen ausführen. Das Forschungspaket enthält alle benötigten Quelldateien und Belege; `.venv`, Zugangsdaten und Modellgewichte sind ausgeschlossen.

Für die Abbildungen zusätzlich die Bibliotheken aus [requirements-analysis.txt](requirements-analysis.txt) installieren; die verwendete Umgebung ist in [analysis-environment.json](docs/analysis-environment.json) dokumentiert:

```sh
python -B scripts/plot_v4_study.py output/recomputed-v4.json --variant v4-strict --out output/figures-recomputed-strict
python -B scripts/plot_v4_study.py output/recomputed-v4f.json --variant v4f-amended --out output/figures-recomputed-amended
```

Die strengere Archivprüfung entpackt das fertige ZIP in einen temporären Ordner, kontrolliert alle Dateihashes und berechnet beide Auswertungen sowie beide unabhängigen Rohdatenprüfungen erneut. Die überprüfte Fassung reproduziert zusätzlich die nachträgliche Baseline-Diagnose und deren separate Rohdatengegenprüfung. Die Analyseprozesse erhalten keine HF-Zugangsdaten; Netzwerk, weitere Unterprozesse und Zugriffe auf den ursprünglichen Projektordner sind gesperrt:

```sh
python -B evidence/oct24-review/verify_reviewed_package.py \
  --archive output/inherited-collusion-v4-research-package.zip \
  --original /home/user/projects/collusion-sprint \
  --out /tmp/collusion-package-verification
```

Auch hier einen neuen Ausgabeordner verwenden. `--original` bezeichnet den ursprünglichen, in den Belegen gespeicherten Projektpfad; dieser muss auf einem anderen Rechner nicht existieren. Abbildungen und PDF-Erzeugung werden separat geprüft; ihre zusätzlichen Abhängigkeiten stehen in `requirements-analysis.txt` und `output/report-v4/source/README.md`.

## Stand der unabhängigen Prüfungen

- **138 Offline-Tests bestanden**, ausgeführt in 16 getrennten Prozessen: vorhandene Softwareprüfungen sowie Fortsetzungsrunner, Auswertung und Missingness-Grenzen. [Testprotokoll](evidence/v4f-validation/full-suite-result.json).
- **Sieben zusätzliche synthetische Paketprüfungen bestanden**, einschließlich Entpacken und Neuberechnen bei unzugänglichem ursprünglichem Projektordner. Diese verwenden Testdaten, keine Forschungsergebnisse. [Prüfbericht](evidence/v4f-validation/offline-package-review.json).
- Beide endgültigen Auswertungen wurden mit separat implementierten Rohdatenprüfern verglichen: **keine Abweichungen** bei [V4 strict](output/independent-v4/independent-check.json) oder [V4F](output/independent-v4f/independent-check.json). Der zusätzliche Prüfer importiert weder Studienrunner noch Hauptauswertung.
- **24 Zeilen mit je drei logischen Completion-Grenzen** wurden unabhängig über die 16 öffentlichen Aufgabenentscheidungen und beobachteten Aktionen nachgerechnet; alle stimmen überein. [Bounds-Gegenrechnung](evidence/v4f-validation/final-bounds-crosscheck.json).
- Die [nachträgliche Baseline-Diagnose vom 24. Oktober](evidence/oct24-review/baseline-review.md) wurde zusätzlich mit einem separat implementierten [Rohdatenprüfer](evidence/oct24-review/baseline-crosscheck.json) kontrolliert: 108 Episodenvergleiche, keine Abweichungen. Drei zusätzliche Softwaretests prüfen diese neue Diagnose; sie sind nicht Teil der 138 eingefrorenen Tests.
- Ein [abschließender Wissenschaftsreview](evidence/v4f-validation/final-scientific-review.md) prüft die Aussagegrenzen, fehlenden Werte, Notiznutzung und den Schutz-/Koordinationskonflikt. Die Prüfungen sind KI-gestützt, keine unabhängige menschliche Bestätigung.

**Offline-Reproduktion mit den echten abgeschlossenen Daten bestanden.** Das gepackte Archiv wurde in einen neuen temporären Ordner entpackt und vollständig per Dateihash geprüft. Beide Auswertungen und beide unabhängigen Rohdatenprüfungen liefen erneut mit gesperrtem Originalprojekt, ohne Netzwerk und ohne HF-Zugangsdaten. Alle wissenschaftlichen Ergebnisfelder stimmen überein; nur Erstellungszeit, Projektpfad und der dazugehörige Eingabehash dürfen sich ändern. [Erster vollständiger Archivprüfbeleg](evidence/v4f-validation/initial-extracted-package-verification.json).

Nach Aufnahme dieses Abschlussvermerks wird das Archiv erneut geprüft. Der separate Beleg `offline-verification.json` liegt neben dem ausgelieferten ZIP und nennt dessen endgültigen SHA-256-Hash. Er bleibt absichtlich außerhalb des Archivs, damit keine selbstbezügliche Prüfsumme entsteht. Abbildungen und Berichtsseiten wurden separat visuell kontrolliert; die portable DOCX-Neuerstellung ist ebenfalls geprüft.

## Aussagegrenzen

Die Vorgänger wurden ausdrücklich zur jeweiligen Strategie angewiesen. Das Experiment untersucht deren Weitergabe durch Notizen; es zeigt keine spontane Kollusion, Verhandlung oder verborgene Absicht. Nachfolger handeln isoliert, und ein konjunktiver Schadensindikator belegt allein keine strategische Wechselwirkung.

Vollständige Fallkontraste mitteln zunächst beide Wiederholungen und gewichten anschließend Fälle gleich. Fehlende Ergebnisse sind niemals null Schaden oder null Nutzen. Ergänzende Worst-Case-Grenzen beziehen sich auf die geplanten Slots; sie sind keine Konfidenzintervalle und belegen keine Aufgabenkompetenz in Fällen ohne gültige Grundlage. Ohne erfolgreiche legitime Notiznutzung ist ein Nullbefund kein belastbarer Nachweis von Robustheit.

Die Inhaltsannotation war KI-gestützt, keine unabhängige menschliche Prüfung. Der strengere Notizqualitäts-Teildatensatz bleibt sekundär und kann Selektionsverzerrung enthalten. Die gemeldeten Modellkennungen wurden geprüft; identische Anbietergewichte sind damit nicht unabhängig bestätigt.

Der [Infrastrukturaudit](docs/colosseum-audit.md) ging dem eigenen Versuch voraus. `vendor/` enthält unvollständige Quellsnapshots des Starter-Repos und Terrarium, gegen die Bewertungsfunktionen geprüft wurden. Der vollständige Colosseum-Runner wurde nicht ausgeführt. Es wurden keine HF-Cloud-Jobs gestartet und noch keine Ergebnisse veröffentlicht oder eingereicht.
