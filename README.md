# Tripreport Verkenner - versie 19

Een Streamlit-app voor openbare iNaturalist-waarnemingen tijdens een reis.

## Nieuw in versie 19

- De overzichtskaart gebruikt de openbare waarnemingslocatie met de meeste waarnemingen binnen een straal van **25 km**, gelijk aan de concentraties in het rapport. Alle waarnemingen met locatie tellen mee, ook waarnemingen die niet op soort zijn geïdentificeerd. Meerdere waarnemingen op dezelfde coördinaat tellen afzonderlijk. Bij gelijke aantallen kiest de app stabiel op coördinaatvolgorde.
- Nieuwe berekeningen bewaren dit zwaartepunt direct. Voor bestaande trips haalt de app eenmalig alle benodigde waarnemingslocaties op, met behoud van datums, tijden en gebiedsfilters. De historische samenvattingen en versies blijven intact. Bij lange trips kan het eerste openen hierdoor langer duren. De marker wordt in browseropslag bewaard; bij een ophaalfout blijft de eerdere locatie zichtbaar en is opnieuw proberen mogelijk.
- Selecteer een trip en wijzig **Tripnaam wijzigen**. Klik **Naam opslaan**. De naamwijziging maakt geen nieuwe berekeningsversie en behoudt alle eerdere totalen. De nieuwe naam verschijnt ook in kaartpopups en reservekopieën.
- Boven de tabel staan **Sorteren op** en **Volgorde**. Iedere kolom is beschikbaar, waaronder naam, reisdatums, berekendatum, aantal versies en alle aantallen. Kies oplopend of aflopend. Onbekende datums/aantallen staan bij deze sorteerkeuze onderaan. Je kunt daarnaast op een kolomkop klikken voor de ingebouwde tabelsortering. Datumkolommen bevatten echte datumwaarden; onbekende berekendatums verschijnen als lege velden.

## Nieuw in versie 18

- Kies een trip direct in de overzichtstabel door de rij aan te tikken. Er is geen vooraf geselecteerde trip en geen aparte keuzelijst. Pas na selectie verschijnen **Opnieuw berekenen**, **Trip verwijderen** en **Versies bekijken**. De kolom Trip blijft vaststaan bij horizontaal scrollen.
- **Trip verwijderen** verwijdert die trip en alle bijbehorende versies uit deze browser; andere trips blijven behouden. Een gedownloade reservekopie wordt niet gewijzigd.
- De gebruikersnaam is op een nieuw beginscherm vooraf ingevuld met `jeanpaulboerekamps`, ook bij een leeg veld uit een oudere sessie. Een andere ingevulde gebruikersnaam blijft behouden bij terugkeer uit het reisformulier. Een leeg gemaakte gebruikersnaam valt terug op de standaard.
- Oudere trips zonder opgeslagen reisgebied krijgen automatisch een kaartlocatie uit hun openbare iNaturalist-waarnemingen in de bewaarde reisperiode. Datums, tijden en eventuele oude plaatsfilters worden gerespecteerd. Alleen locatiegegevens worden opgehaald; de historische totalen en versies veranderen niet. De herstelde locatie wordt in dezelfde browser opgeslagen en meegenomen in reservekopieën.
- Nieuwe rapporten bewaren een compacte openbare waarnemingslocatie voor de kaart. De kaart past zich opnieuw aan wanneer trips of locaties veranderen. Kaartmarkers zijn getekende cirkels, zodat een ontbrekend markerplaatje op iPad geen onleesbare pin meer oplevert.
- Als er geen openbare locatie gevonden wordt of iNaturalist niet bereikbaar is, noemt het scherm de ontbrekende trips en kun je **Kaartlocaties opnieuw ophalen** gebruiken. Er wordt geen locatie uit de tripnaam geraden.

## Nieuw in versie 17

- Het beginscherm is **Mijn trips**, standaard voor `jeanpaulboerekamps`. De gebruikersnaam is aanpasbaar; het overzicht toont alleen de lokaal bewaarde trips van die gebruiker.
- Eerst verschijnt een kaart met een marker per trip, daarna één compacte tabel met de totalen van de meest recente berekening. Klik op een marker voor naam, periode en totalen. Trips zonder openbaar reisgebied blijven in de tabel staan, met een melding onder de kaart.
- Per trip blijven meerdere versies bewaard, met de datum en tijd waarop de berekening is afgerond. Op het beginscherm kun je een trip kiezen en de totalen van alle versies vergelijken. Tijden worden weergegeven in Europe/Amsterdam.
- **Nieuwe trip** opent het bestaande reisformulier. **Mijn trips** brengt je terug naar het overzicht.
- Selecteer een bestaande trip en klik **Nieuwe versie berekenen** om de instellingen te laden. Klik vervolgens **Tripreport maken**. Dit haalt de gegevens opnieuw op, zodat latere identificaties worden meegenomen. Klik na voltooiing op **Versie bewaren**. De eerdere versies blijven behouden. Dezelfde berekening nogmaals bewaren maakt geen dubbele versie en wijzigt geen oudere snapshot.
- Een automatisch veranderd reisgebied maakt geen nieuwe trip: de gebruiker en begin-/einddatum met tijden bepalen of een berekening bij de geladen trip hoort. Gewijzigde gebruiker of periode wordt als een nieuwe trip bewaard.
- Oude opgeslagen trips en JSON-reservekopieën worden omgezet naar één bestaande versie. Als de oorspronkelijke berekendatum ontbreekt, staat er **Onbekend (oudere trip)**; er wordt geen datum verzonnen.
- Export bevat alle trips en versies van alle gebruikers. Import voegt versies samen en verwijdert geen nieuwere versies die al in de browser staan.

Versies bewaren reisinstellingen, het openbare reisgebied en samenvattingsaantallen. De volledige soortenkaarten/PDF van iedere oude versie worden niet in browseropslag bewaard; download een PDF of herstartbestand voor een volledig rapport. De trips komen uit de browseropslag, niet uit een automatisch uit iNaturalist afgeleide reislijst. Gebruik reservekopieën voor een andere browser of een ander apparaat.

## Gebruik

1. Begin bij **Mijn trips**. Kies indien nodig een andere iNaturalist-gebruikersnaam en klik **Nieuwe trip**.
2. Geef de trip een naam (verplicht, maximaal 120 tekens). Vul de exacte openbare iNaturalist-gebruikersnaam in.
3. Kies datums (vanaf 1965) en tijden. Standaard 00:00 tot 23:59; de eindminuut telt volledig mee. De tijd is lokaal per waarneming.
4. Kies of **nieuw in gebied en nieuw op iNaturalist** ook in de kaartcirkels moeten staan. Deze keuze geldt alleen voor de kaart. Sterren en totalen worden altijd volledig gecontroleerd.
5. Klik **Tripreport maken**. De voortgang vermeldt de actieve stap. Elke expliciet aangevraagde berekening begint met actuele gegevens; een al lopende identieke taak wordt hergebruikt om dubbel werk te voorkomen. Hervatten via een rapport-URL of herstartbestand blijft beschikbaar.
6. Het rapport begint met de heatmap en 25 km-cirkels, gevolgd door samenvatting en soortenkaarten met eigen foto's. Klik na voltooiing op **Versie bewaren** en vervolgens **Mijn trips** om de nieuwste totalen in het overzicht te zien.
7. Maak eventueel een PDF en download een herstartbestand. De PDF begint met tripnaam, samenvatting en kaart, gevolgd door de soortenfoto's. Er is geen CSV-export.

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

De browser bewaart automatisch het nummer van je laatste berekening. Via de gewone app-URL kom je eerst op **Mijn trips**. Daar staat **Verdergaan met vorige berekening** als een vorige taak bekend is. Bij een lopende taak opent dit dezelfde taak; bij een onderbroken servertaak kun je het opgeslagen punt hervatten. De gebruikersnaam, datums, tijden en kaartkeuze worden teruggezet. Een URL met `?report=...` opent het rapport direct. Zonder servergegevens wordt aangegeven dat een herstartbestand nodig is.

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

Zet alle bronbestanden, inclusief `report_jobs.py`, `concentrations.py`, `trip_map.py`, `report_pdf.py`, `trip_store.py`, `trip_overview.py`, `trip_locations.py`, de component en requirements, in de Streamlit-repository. Startbestand: `app.py`.

Installatie: `pip install -r requirements.txt`.
Tests: voer na installatie `python -m unittest discover -s tests -v` uit. Dit controleert versieopslag, migratie, import, verse berekeningen en navigatie met Streamlit AppTest. Ook tabelselectie, verwijderen, standaardgebruikersnaam en locatieherstel worden gecontroleerd. De browsercomponent kan apart worden getest met `node tests/test_browser_store.js`.

Bijwerken: vervang alle bronbestanden uit dit ZIP-bestand in je bestaande Streamlit-project en herstart de app. De browseropslagsleutel blijft gelijk, zodat bewaarde trips op dezelfde app-URL behouden blijven. Maak voor de update een JSON-reservekopie.

API-verzoeken behouden de bestaande globale wachttijd van circa één seconde tussen starts en retries bij tijdelijke fouten. Een mislukte persoonlijke groepscontrole wordt onzeker gemarkeerd en start niet honderden losse zoekacties.

## Grotere kaart

De interactieve kaart is 680 pixels hoog en past het gebied met kleinere buitenmarges. De PDF-kaart staat onder de tripnaam en samenvatting op de eerste pagina. Cirkelteksten zijn kleiner; popups in de app blijven beschikbaar voor details. Alle waarnemingen en cirkels blijven in beeld. Bij een wijziging van alleen de kaartkeuze hergebruikt de server de eerder opgehaalde reisgegevens en stercontroles als het herstartpunt nog beschikbaar is.

## Actuele Research Grade

Een groene rand om de hele soortenkaart betekent dat minstens één van de waarnemingen uit de gekozen trip nu Research Grade is. Dit staat los van de gele/oranje/rode sterren en geldt in de app en PDF. De waarneming hoeft tijdens de reis nog geen RG te zijn geweest. Een waarneming buiten de gekozen trip telt niet mee, ook niet als die van dezelfde soort is.

Bij een nieuwe berekening wordt de huidige RG-status na de stercontroles opnieuw opgehaald. Een eerder bewaard of geladen rapport kan een oudere status hebben: klik **RG-status actualiseren** om alleen deze status te vernieuwen en maak daarna opnieuw de PDF. Een mislukte verversing behoudt de oudere status en geeft een melding.

De PDF vermeldt bovenaan de datum en tijd waarop de berekening afgerond is, in de tijdzone Europe/Amsterdam. Het is de berekeningsdatum, niet de datum van downloaden. Elke pagina heeft Pagina x van y, inclusief kaartpagina en de kleinere foto's achteraan. Bij oudere afgeronde serverrapporten wordt de bewaarde voltooiingstijd gebruikt; als de datum niet beschikbaar is, wordt dat vermeld.
