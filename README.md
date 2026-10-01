# Tripreport Verkenner - versie 13

Een Streamlit-app voor openbare iNaturalist-waarnemingen tijdens een reis.

## Gebruik

1. Geef eerst een naam aan de trip (verplicht, maximaal 120 tekens). Deze naam wordt bij de berekening en het herstartpunt bewaard. Vul daarna je exacte iNaturalist-gebruikersnaam in. Hoofdletters en spaties worden genegeerd; typefouten worden gemeld.
2. Kies datums (vanaf 1965) en tijden. Standaard 00:00 tot 23:59; de eindminuut telt volledig mee. De tijd is lokaal per waarneming.
3. Kies of **nieuw in gebied en nieuw op iNaturalist** ook in de kaartcirkels moeten staan. Deze keuze geldt alleen voor de kaart. Sterren en totalen worden altijd volledig gecontroleerd.
4. Klik **Tripreport maken**. De voortgang vermeldt de actieve stap.
5. De app begint met de heatmap en 25 km-cirkels, gevolgd door samenvatting en soortenkaarten met eigen foto's. De PDF begint met de bewaarde tripnaam, direct gevolgd door de samenvatting en dan de kaart op de eerste pagina. De toelichting onder de kaart is verwijderd. Daarna volgen fotopagina's met vier kolommen en vier rijen (16 soorten per volle pagina), in de gekozen soortenvolgorde. Er is geen CSV-export.

Bovenaan de app staat **Versie 13**, zodat je kunt controleren of de nieuwe bestanden zijn gedeployed. Bestaande trips uit eerdere versies blijven bruikbaar. De PDF gebruikt de ingevulde tripnaam of vindt de passende bewaarde naam terug. De download heet exact de tripnaam met .pdf; tekens die niet in een bestandsnaam mogen worden door een underscore vervangen. Oude herstartbestanden zonder naam blijven laadbaar.

## Waarnemingen zonder soortidentificatie

Alle geselecteerde waarnemingen die niet aan een soort in het soortenoverzicht zijn gekoppeld, staan achteraan als afzonderlijke kleinere fotokaarten, in rijen van acht. Dit geldt voor de app en de PDF. Een genus-, familie- of andere taxonnaam staat erbij als die beschikbaar is; anders Onbekend. Zonder openbare foto wordt een lege kaart getoond. Een identificatie op ondersoort wordt via de soortvoorouder wel bij de normale soortenkaarten ingedeeld. Het ophalen van extra PDF-foto’s kan de export langer laten duren.

Kaartlabels staan links van de middelpunten, met pijlen ernaartoe, zodat de concentraties zichtbaar blijven. De kaart houdt ruimte voor de labels aan de linkerkant.

## Snelle cirkels en persoonlijke eerste soorten

Bij minstens 26 waarnemingen binnen een geografische straal van 25 km verschijnt een cirkel. De dichtste locatie wordt eerst gekozen, daarna de dichtste locatie waarvan het middelpunt minstens 25 km van de al gekozen middelpunten ligt. Cirkels kunnen overlappen; hun aantallen zijn niet optelbaar.

De cirkels tonen slechts drie aantallen: waarnemingen, unieke soorten en soorten nieuw voor jou. Waarnemingen zonder soortidentificatie tellen wel mee bij het eerste aantal. Nieuw betekent dat jouw eerste gedateerde iNaturalist-waarneming van een soort in die cirkel ligt. De app controleert de geschiedenis voor de eerste reisdag in groepen van maximaal 80 soorten en hergebruikt de reeds opgehaalde volledige dagen, ook bij een keuze van gedeeltelijke dagen. Een eerdere waarneming op dezelfde dag buiten de cirkel of buiten de gekozen uren telt dus niet als nieuw in die cirkel. Historische volgorde volgt waarnemingsdatum, met ID als gelijke-datumvolgorde voor persoonlijke waarnemingen. Een eerste registratie is geen wetenschappelijke ontdekking.

Zonder de kaartkeuze tonen cirkels drie aantallen. Met de kaartkeuze komen nieuw in het automatische reisgebied en nieuw op iNaturalist erbij. Dit geldt in de app en de PDF. De extra cirkeltellingen gebruiken de IDs van de eerste waarnemingen uit de altijd uitgevoerde stercontrole. De eerste waarneming moet daadwerkelijk binnen de betreffende cirkel vallen; een eerste elders tijdens de reis telt niet in deze cirkel. Onvolledige controles tonen `>= aantal (?)`; onbekend is niet nul. De gebiedstelling is voor het automatische reisgebied, niet voor het hele land.

Gele, oranje en rode sterren en de persoonlijke/gebieds-/wereldtellingen in de samenvatting worden altijd gecontroleerd, onafhankelijk van de kaartkeuze. Geel geeft jouw eerste waarneming. De rode rand om de gele ster is verwijderd. Oranje betekent eerste in automatisch reisgebied; rood betekent eerste op iNaturalist. Deze volledige historische controles kunnen minuten kosten en worden tussentijds opgeslagen per groep. De keuze voor extra kaarttellingen verandert alleen wat de cirkels tonen.

## Onderbreken en hervatten

Het ophalen en controleren draait op de server, los van de browserverbinding. Bewaar de URL met `?report=...` om terug te keren naar dezelfde taak.

De browser bewaart nu ook automatisch het nummer van je laatste berekening. Als je terugkomt via de gewone app-URL, vindt de app deze taak terug. Boven het reisformulier staat **Je vorige berekening** met de voortgang en **Verdergaan met vorige berekening**. Bij een lopende taak opent dit dezelfde taak; bij een onderbroken servertaak hervat het het opgeslagen punt. De gebruikersnaam, datums, tijden en kaartkeuze worden uit de taak teruggezet. Dit werkt in dezelfde browser op hetzelfde apparaat als lokale browseropslag beschikbaar is. Zonder servergegevens wordt duidelijk aangegeven dat een herstartbestand nodig is.

De app slaat een herstartpunt op na accountcontrole, volledig ophalen van de waarnemingen, opbouwen van de soortenlijst, iedere persoonlijke groepscontrole, cirkelberekening en ophalen van totalen. Volledige stercontroles worden per groep van 40 soorten opgeslagen. Een onafgeronde stap wordt opnieuw uitgevoerd, afgeronde stappen en groepen worden hergebruikt.

- Als de taak nog draait: terugkeren naar dezelfde URL sluit erop aan.
- Als alleen het serverproces is herstart maar de opslag nog bestaat: open dezelfde URL en klik **Berekening hervatten**. Dezelfde reisinstellingen opnieuw indienen hervat ook het opgeslagen punt.
- Download tussentijds **Herstartbestand downloaden**. Dit JSON-bestand bevat de tot dan toe opgehaalde gegevens en controles. Download na meer voortgang een nieuw exemplaar om een later punt te bewaren.
- Als Streamlit de hele tijdelijke serveropslag wist: open **Berekening hervatten met een herstartbestand**, kies je JSON-bestand en klik **Berekening uit bestand hervatten**. Alleen werk na dat bestand wordt opnieuw gedaan.

Herstartpunten blijven op de server zeven dagen beschikbaar. Streamlit Cloud kan deze tijdelijke opslag eerder wissen bij herdeploy, herstart of slapen. Een gedownload herstartbestand biedt herstel zonder die serveropslag. Er is geen externe duurzame database. Versie 8- en versie 9-herstartbestanden worden ondersteund. Bij het laden van versie 8 worden ontbrekende volledige sterren alsnog gecontroleerd; niet-afgeronde versie 6/7-berekeningen hadden geen dergelijke opslag en kunnen niet achteraf worden teruggehaald. PDF-generatie start afzonderlijk op verzoek.

## Gebied, locaties en kaart

Het gebied wordt intern bepaald uit de openbare locaties, met ongeveer 1 km marge. De groene omgrenzing wordt niet getekend. Bij oranje sterren blijft dit gebied de geografische scope. Locaties ontbreken soms of zijn door iNaturalist verduisterd; de kaart gebruikt de openbare coördinaten. Gegevens zonder openbare locatie blijven in het rapport.

Waarnemingen zonder tijdstip op een gedeeltelijk gekozen grensdag worden uitgesloten en vermeld. Volledige dagen blijven wel meetellen. Dateline-overschrijdende reizen worden ondersteund.

De interactieve kaart gebruikt OpenStreetMap. De PDF haalt een beperkte hoeveelheid kaarttegels op en toont een melding als de achtergrond niet beschikbaar is; de lokale heatmap blijft beschikbaar. De kaarttegelcache is begrensd.

## Bewaarde trips en installatie

Tripinstellingen en samenvattingen worden lokaal in je browser bewaard; ze zijn apart van de server-herstartpunten. Ze kunnen als JSON worden geëxporteerd en geïmporteerd. Bewaarde trips uit oudere versies gebruiken standaardtijden 00:00 en 23:59.

Zet alle bronbestanden, inclusief `report_jobs.py`, `concentrations.py`, `trip_map.py`, `report_pdf.py`, de component en requirements, in de Streamlit-repository. Startbestand: `app.py`.

Installatie: `pip install -r requirements.txt`.
Tests: installeer ook `tests/requirements.txt` en voer `python -m unittest discover -s tests -v` uit.

API-verzoeken behouden de bestaande globale wachttijd van circa één seconde tussen starts en retries bij tijdelijke fouten. Een mislukte persoonlijke groepscontrole wordt onzeker gemarkeerd en start niet honderden losse zoekacties.

## Grotere kaart

De interactieve kaart is 680 pixels hoog en past het gebied met kleinere buitenmarges. De PDF-kaart staat onder de tripnaam en samenvatting op de eerste pagina. Cirkelteksten zijn kleiner; popups in de app blijven beschikbaar voor details. Alle waarnemingen en cirkels blijven in beeld. Bij een wijziging van alleen de kaartkeuze hergebruikt de server de eerder opgehaalde reisgegevens en stercontroles als het herstartpunt nog beschikbaar is.

## Actuele Research Grade

Een groene rand om de hele soortenkaart betekent dat minstens één van de waarnemingen uit de gekozen trip nu Research Grade is. Dit staat los van de gele/oranje/rode sterren en geldt in de app en PDF. De waarneming hoeft tijdens de reis nog geen RG te zijn geweest. Een waarneming buiten de gekozen trip telt niet mee, ook niet als die van dezelfde soort is.

Bij een nieuwe berekening wordt de huidige RG-status na de stercontroles opnieuw opgehaald. Een eerder bewaard of geladen rapport kan een oudere status hebben: klik **RG-status actualiseren** om alleen deze status te vernieuwen en maak daarna opnieuw de PDF. Een mislukte verversing behoudt de oudere status en geeft een melding.
