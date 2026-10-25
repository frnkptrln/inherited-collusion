> **Historischer Arbeitsstand des ersten Piloten.** Dieser Text bleibt zur Dokumentation erhalten. Die später abgeschlossenen Studien V4/V4F und der Kontrollversuch V5 vom 24. Oktober 2026 sind im [aktuellen README](../README.md) und in der [Studiengeschichte](study-history.md) dokumentiert; die folgenden Ergebnis- und Kostenangaben gelten nur für den damaligen Pilotstand.

# Stand und nächste Schritte — 23. Oktober 2026

Der erste Pilot ist abgeschlossen, die zentrale Vererbungsfrage bleibt ungetestet.
Siehe `pilot-findings.md` und den Bericht. Drei Entwicklungsversuche wurden erhalten;
keine Vorgänger- oder Nachfolgeepisoden und keine Cloud-Jobs ausgeführt.

## Was bereitliegt

- Fortsetzbarer Runner mit strengen Antwort-, Quellen-, Budget- und Modellkennungsprüfungen.
- Geprüfte ursprüngliche Scoringlogik und acht numerisch verschiedene v2-Aufgaben.
- Acht Interventionsbedingungen einschließlich tatsächlicher Notiznutzungskontrolle
  (`matched_p1`) und allgemeinem Prüfhinweis (`verified`).
- Unveränderte Rohdaten, Quellsnapshots, reproduzierbare Auswertung und Bericht.
- Das ursprüngliche `pilot-protocol.md` ist ein historischer Entwicklungsstand.
  Das neuere `extended-protocol.md` ist vorbereitet, wurde aber nicht als echte Studie gestartet.

## Bevor die eigentliche Studie sinnvoll ist

1. Die Modellidentität zuverlässig klären. Angeforderte Modell-ID, öffentliche
   Anbieterzuordnung und vom Provider gemeldete Antwort-ID müssen zusammenpassen.
   Der aktuelle Runner stoppt bei Abweichung und speichert den Beleg. Ein passender
   Bezeichner bestätigt noch nicht unabhängig die tatsächlich gehosteten Gewichte.
2. Ein separates, datiertes Machbarkeitsprotokoll für das Aufgabenverständnis festlegen.
   Ein möglicher neuer Ansatz wäre eine öffentlich berechnete Tabelle aller
   gemeinsamen Entscheidungen und Fortsetzungskosten. Das würde die kombinatorische
   Last verringern, verändert aber die Aufgabe und muss separat ausgewiesen werden.
   Keinen laufenden Versuch anhand gewünschter Kollusionsergebnisse umgestalten.
3. Die richtigen Entscheidungen und ihre Kostenbegründungen prüfen. Erst danach
   Vorgänger erzeugen und alle acht Notizen inhaltlich lesen. Die hashgebundene
   Prüfung nennt den tatsächlichen Reviewer; eine KI-Prüfung ist keine unabhängige
   menschliche Annotation.
4. Erst mit gültiger Kompetenz und gültigen Notizen alle vorab festgelegten Fälle
   ausführen. Fehlgeschlagene Fälle erhalten, nicht durch günstigere ersetzen.
   Die tatsächliche Notiznutzung in legitimen `matched`/`matched_p1`-Episoden prüfen.
5. Alle geplanten Nenner und ungültigen Fälle berichten. Ein Nullbefund ohne diese
   Manipulationskontrolle wäre mehrdeutig. Eine positive Vererbung beträfe eine
   ausdrücklich instruierte Vorgängerabsprache, keine spontane Kollusion.

Das Gesamtbudget von etwa 15 USD ist vom Nutzer zur selbständigen Verwendung
freigegeben. Der dokumentierte Rest ist keine bestätigte Guthabenauskunft.
Bisherige Anbieter-Schätzung: 0,00720307 USD; Reservierung für tatsächliche
Anfragen: 0,126 USD. Kein weiterer bezahlter Lauf ist Teil dieses abgeschlossenen
Piloten. Frühere genehmigte Konfigurationen bleiben als historische Belege erhalten;
die v2-Konfiguration ist eine deaktivierte Vorlage.

## Einreichung

Die offizielle Sprintseite nennt PDF (maximal 25 MB), maximal acht Haupttextseiten
zuzüglich Referenzen/Anhängen und einen Anhang zu Limitations & Dual-Use/Ethical
Considerations. Der vorbereitete Bericht verwendet die offizielle Vorlage und
enthält die KI-Nutzungserklärung. Frank Peterlein muss Inhalt und Angaben vor dem
Hochladen prüfen. Keine Einreichung wurde vorgenommen.

Frist laut geprüfter Sprintseite: Sonntag, 25. Oktober 2026, 23:59 AoE; dies ist
Montag, 26. Oktober 2026, 12:59 Uhr Europe/Berlin. Verbindliche Veranstalterseite:
https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25
