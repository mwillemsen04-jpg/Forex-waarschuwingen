# Forex-waarschuwingen – zelf online zetten

Deze map is een complete website. GitHub zet hem online (GitHub Pages) en haalt elke ochtend
vanzelf het nieuws van Forex Factory op (GitHub Actions). Daarna hoef je niets meer te doen.

## Wat zit erin

| Bestand | Wat het doet |
|---|---|
| `index.html` | De pagina zelf |
| `ff.json` | Het nieuws van Forex Factory (wordt elke dag vervangen) |
| `rates.json` | De rentes per centrale bank |
| `fx.json` | De wisselkoersen voor het tabblad Munten (elke werkdag nieuw) |
| `update.py` | Het script dat het nieuws ophaalt |
| `.github/workflows/update.yml` | Zegt tegen GitHub: draai `update.py` elke ochtend |

Let op: de map `.github` is verborgen op Windows en Mac. Kopieer daarom de hele map, niet alleen de losse bestanden.

## Eenmalig instellen (ongeveer 5 minuten)

1. **Nieuwe repository maken.** Open GitHub Desktop → *File* → *New repository*.
   Naam: `forex-waarschuwingen`. Kies een plek op je computer en klik *Create repository*.
2. **Bestanden erin zetten.** Kopieer alles uit deze map (ook de map `.github`) naar de nieuwe repository-map.
3. **Online zetten.** In GitHub Desktop: typ een korte tekst bij *Summary* (bijv. "eerste versie"),
   klik *Commit to main* en daarna *Publish repository*. Haal het vinkje bij *Keep this code private* weg
   (GitHub Pages is alleen gratis voor openbare repositories).
4. **GitHub Pages aanzetten.** Ga op github.com naar de repository → *Settings* → *Pages*.
   Bij *Source* kies je *Deploy from a branch*, branch `main`, map `/ (root)` → *Save*.
5. **Schrijfrechten voor de update.** *Settings* → *Actions* → *General* → helemaal onderaan bij
   *Workflow permissions* kies je **Read and write permissions** → *Save*.
6. **Eerste update testen.** Tabblad *Actions* → links *Nieuws bijwerken* → *Run workflow*.
   Na ongeveer een halve minuut staat er een groen vinkje.

De pagina staat daarna op:
**https://mwillemsen04-jpg.github.io/forex-waarschuwingen/**

## Hoe het daarna werkt

Alles gaat vanzelf, elke ochtend rond 06:17 en op werkdagen ook rond 16:47 (in de zomer een uur later):

- **Nieuws en feestdagen** komen van Forex Factory (deze week en volgende week), met de verwachte en vorige waarde, in dezelfde kleuren als Forex Factory: rood = hoog, oranje = middel, geel = laag.
- **Rentes** worden opgehaald bij de bronnen zelf: Fed en ECB via FRED, de Bank of England, de Bank of Canada,
  de Zwitserse Nationale Bank en de Reserve Bank of Australia. Verandert een rente, dan past de tabel zich aan,
  met de verandering en de datum erbij. Voor de Bank of Japan en Nieuw-Zeeland bestaat geen open databron:
  die rente neemt het script over van Forex Factory zodra het volgende besluit in de kalender staat.
- **Koersen voor het tabblad Munten** komen van de Europese Centrale Bank (via frankfurter.dev), de laatste 3 maanden.
- **Alle data en tijden** (rentebesluiten, CPI, banenrapport enzovoort) komen alleen van Forex Factory. Verandert daar iets, dan verandert het hier ook. Je ziet deze en volgende week vooruit.
- Is een bron een keer onbereikbaar, dan blijft de oude informatie staan en probeert GitHub het de volgende ochtend opnieuw.
- Wil je zien of het werkt? Kijk op github.com bij het tabblad *Actions*: elke dag hoort er een groen vinkje bij te komen.
