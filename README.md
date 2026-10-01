# Tripreport Verkenner - versie 8

Een Streamlit-app voor openbare iNaturalist-waarnemingen tijdens een reis.

## Gebruik

1. Vul je exacte iNaturalist-gebruikersnaam in. Hoofdletters en spaties worden genegeerd; typefouten worden gemeld.
2. Kies datums (vanaf 1965) en tijden. Standaard 00:00 tot 23:59; de eindminuut telt volledig mee. De tijd is lokaal per waarneming.
3. Laat **Uitgebreide oranje en rode stercontrole** uit voor het snelle rapport.
4. Klik **Tripreport maken**. De voortgang vermeldt de actieve stap.
5. Het rapport begint met de heatmap en 25 km-cirkels, gevolgd door samenvatting en soortenkaarten met eigen foto's. De PDF gebruikt dezelfde cirkels en gekozen soortenvolgorde. Er is geen CSV-export.

Bovenaan de app staat **Versie 8**, zodat je kunt controleren of de nieuwe bestanden zijn gedeployed. Bestaande trips uit eerdere versies blijven bruikbaar.

## Snelle cirkels en persoonlijke eerste soorten

Bij minstens 26 waarnemingen binnen een geografische straal van 25 km verschijnt een cirkel. De dichtste locatie wordt eerst gekozen, daarna de dichtste locatie waarvan het middelpunt minstens 25 km van de al gekozen middelpunten ligt. Cirkels kunnen overlappen; hun aantallen zijn niet optelbaar.

De cirkels tonen slechts drie aantallen: waarnemingen, unieke soorten en soorten nieuw voor jou. Waarnemingen zonder soortidentificatie tellen wel mee bij het eerste aantal. Nieuw betekent dat jouw eerste gedateerde iNaturalist-waarneming van een soort in die cirkel ligt. De app controleert de geschiedenis voor de eerste reisdag in groepen van maximaal 80 soorten en hergebruikt de reeds opgehaalde volledige dagen, ook bij een keuze van gedeeltelijke dagen. Een eerdere waarneming op dezelfde dag buiten de cirkel of buiten de gekozen uren telt dus niet als nieuw in die cirkel. Historische volgorde volgt waarnemingsdatum, met ID als gelijke-datumvolgorde voor persoonlijke waarnemingen. Een eerste registratie is geen wetenschappelijke ontdekking.

De cirkels doen geen land- of wereldwijde historische controles. Die aantallen zijn ook uit de PDF-cirkels verwijderd. Onvolledige persoonlijke controles tonen `>= aantal (?)`; onbekend is niet nul.

Oranje en rode sterren en de gebieds-/wereldtellingen in de samenvatting staan standaard uit. Uitgeschakelde tellingen tonen een streepje. Je kunt die uitgebreide controles bij de reisinstellingen aanzetten; dan kunnen vele historische API-verzoeken opnieuw minuten kosten. Dit voegt geen land-/wereldtellingen aan de cirkels toe. Geel geeft jouw eerste waarneming; een rode rand om geel betekent Research Grade tijdens de reis.

## Onderbreken en hervatten

Het ophalen en controleren draait op de server, los van de browserverbinding. Bewaar de URL met `?report=...` om terug te keren naar dezelfde taak.

De app slaat een herstartpunt op na accountcontrole, volledig ophalen van de waarnemingen, opbouwen van de soortenlijst, iedere persoonlijke groepscontrole, cirkelberekening en ophalen van totalen. Optionele uitgebreide stercontroles worden per groep van 40 soorten opgeslagen. Een onafgeronde stap wordt opnieuw uitgevoerd, afgeronde stappen en groepen worden hergebruikt.

- Als de taak nog draait: terugkeren naar dezelfde URL sluit erop aan.
- Als alleen het serverproces is herstart maar de opslag nog bestaat: open dezelfde URL en klik **Berekening hervatten**. Dezelfde reisinstellingen opnieuw indienen hervat ook het opgeslagen punt.
- Download tussentijds **Herstartbestand downloaden**. Dit JSON-bestand bevat de tot dan toe opgehaalde gegevens en controles. Download na meer voortgang een nieuw exemplaar om een later punt te bewaren.
- Als Streamlit de hele tijdelijke serveropslag wist: open **Berekening hervatten met een herstartbestand**, kies je JSON-bestand en klik **Berekening uit bestand hervatten**. Alleen werk na dat bestand wordt opnieuw gedaan.

Herstartpunten blijven op de server zeven dagen beschikbaar. Streamlit Cloud kan deze tijdelijke opslag eerder wissen bij herdeploy, herstart of slapen. Een gedownload herstartbestand biedt herstel zonder die serveropslag. Er is geen externe duurzame database. Herstartbestanden zijn bedoeld voor versie 8; niet-afgeronde versie 6/7-berekeningen hadden geen dergelijke opslag en kunnen niet achteraf worden teruggehaald. PDF-generatie start afzonderlijk op verzoek.

## Gebied, locaties en kaart

Het gebied wordt intern bepaald uit de openbare locaties, met ongeveer 1 km marge. De groene omgrenzing wordt niet getekend. Bij optionele oranje sterren blijft dit gebied de geografische scope. Locaties ontbreken soms of zijn door iNaturalist verduisterd; de kaart gebruikt de openbare coördinaten. Gegevens zonder openbare locatie blijven in het rapport.

Waarnemingen zonder tijdstip op een gedeeltelijk gekozen grensdag worden uitgesloten en vermeld. Volledige dagen blijven wel meetellen. Dateline-overschrijdende reizen worden ondersteund.

De interactieve kaart gebruikt OpenStreetMap. De PDF haalt een beperkte hoeveelheid kaarttegels op en toont een melding als de achtergrond niet beschikbaar is; de lokale heatmap blijft beschikbaar. De kaarttegelcache is begrensd.

## Bewaarde trips en installatie

Tripinstellingen en samenvattingen worden lokaal in je browser bewaard; ze zijn apart van de server-herstartpunten. Ze kunnen als JSON worden geëxporteerd en geïmporteerd. Bewaarde trips uit oudere versies gebruiken standaardtijden 00:00 en 23:59.

Zet alle bronbestanden, inclusief `report_jobs.py`, `concentrations.py`, `trip_map.py`, `report_pdf.py`, de component en requirements, in de Streamlit-repository. Startbestand: `app.py`.

Installatie: `pip install -r requirements.txt`.
Tests: installeer ook `tests/requirements.txt` en voer `python -m unittest discover -s tests -v` uit.

API-verzoeken behouden de bestaande globale wachttijd van circa één seconde tussen starts en retries bij tijdelijke fouten. Een mislukte persoonlijke groepscontrole wordt onzeker gemarkeerd en start niet honderden losse zoekacties.
