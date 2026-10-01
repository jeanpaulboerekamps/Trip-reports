# Tripreport Verkenner - versie 6

Een Streamlit-app voor afgeronde reizen met openbare iNaturalist-waarnemingen.

## Gebruik

1. Vul je openbare iNaturalist-gebruikersnaam in.
   De app controleert de exacte accountnaam voordat waarnemingen worden
   opgehaald. Hoofdletters en omringende spaties worden genegeerd; typefouten
   worden gemeld. De zoekacties gebruiken daarna het bevestigde gebruikersnummer.
2. Kies de begin- en einddatum en de tijden. Datums zijn beschikbaar vanaf
   1 januari 1965. Standaardtijden zijn 00:00 en 23:59. De eindminuut telt
   volledig mee, inclusief seconden. Tijden zijn de lokale tijden per
   waarneming, volgens de tijdzone die iNaturalist registreert.
3. Klik op **Tripreport maken**. Alle eigen openbare waarnemingen in deze
   periode worden opgehaald, zonder handmatig gebiedsfilter.
4. Het rapport begint met een interactieve heatmap op OpenStreetMap. Daarna
   volgen de samenvatting en soortenkaarten. Je kunt de kaarten sorteren en
   het aantal zichtbare soorten kiezen.
5. Klik op **PDF van volledig overzicht maken** en daarna **PDF downloaden**.
   De eerste PDF-pagina bevat de heatmap; daarna volgen de samenvatting en
   alle soorten in de gekozen sorteervolgorde. Er is geen CSV-export meer.

## Automatisch reisgebied

De groene omgrenzing wordt niet meer getekend. Het gebied blijft intern beschikbaar voor de bestaande oranje sterren.

## Concentraties op de kaart

Kaart en PDF tonen cirkels met een geografische straal van 25 km bij minstens 26 openbare waarnemingen. De dichtste locatie wordt eerst gekozen; andere middelpunten binnen 25 km daarvan krijgen geen extra cirkel. Vervolgens wordt de dichtste overgebleven locatie gekozen. Zo verschijnen niet tientallen identieke cirkels rond dezelfde concentratie. Cirkels kunnen overlappen; tel de aantallen dus niet bij elkaar op.

Elke cirkel toont waarnemingen (ook zonder soortidentificatie), unieke soorten, nieuwe soorten voor jouw account, voor het betreffende land en wereldwijd op iNaturalist. Een soort is nieuw wanneer de eerste gedateerde iNaturalist-waarneming in de betreffende scope een van jouw waarnemingen binnen die cirkel is. Dit is een registratie-eerste, geen wetenschappelijke ontdekking. Landen komen uit de standaard iNaturalist-plaatsen op de waarneming (`admin_level=0`), niet uit het automatische reisgebied. Bij grensoverschrijdende cirkels telt een soort eenmaal als die in minstens één van die landen nieuw is. Ontbrekende landen en mislukte historische controles worden als `>= aantal (?)` getoond; onbekend is niet nul. De historische volgorde volgt iNaturalist `observed_on`, met de door de API gekozen eerste waarneming bij gelijke datums.

Deze extra historische controles kunnen vooral bij veel nieuwe soorten langer duren. Exacte eerste-recordvragen worden in het app-proces gecachet. Bij opnieuw ophalen wordt de controle opnieuw opgebouwd.

De app bepaalt het reisgebied uit de openbare locaties in de gekozen periode.
Het gebied is de omhullende grens (convexe omhulling) van alle locaties, met
circa 1 km marge. Ook één locatie levert daarmee een bruikbaar gebied op.
De groene grens is zichtbaar op de kaarten en wordt gebruikt voor de controle
van eerste waarnemingen in het gebied. Bij verspreide locaties kan de grens
ook tussenliggende plekken omvatten waar je niet bent geweest. Een reis over
de internationale datumgrens krijgt een passend gebied aan beide kanten.

Heatmapkleuren tonen relatieve dichtheid, geen exact aantal per kleur.
Alle geselecteerde waarnemingen met een openbare locatie tellen mee,
ook waarnemingen die nog niet op soort zijn geïdentificeerd. Waarnemingen
zonder openbare locatie blijven in de samenvatting en soortenlijst staan.
Zonder locaties kan geen heatmap of gebied worden bepaald en zijn oranje
sterren niet beschikbaar. Afgeschermde locaties worden uitsluitend gebruikt
zoals ze openbaar door iNaturalist worden aangeleverd.

Wanneer een waarneming geen tijdstip heeft, telt zij mee op een volledig
gekozen dag. Op een gedeeltelijk gekozen begin- of einddag wordt zij niet
meegenomen; de app en PDF vermelden het aantal van deze uitsluitingen.

De PDF haalt kaarttegels van OpenStreetMap op en bewaart tijdelijk maximaal
96 tegels in het geheugen. Als tegels niet beschikbaar zijn, blijft de heatmap
zichtbaar en krijgt de PDF een melding over de ontbrekende achtergrondkaart.
De interactieve kaart en PDF gebruiken dezelfde locaties en gebiedsgrens;
de dichtheidsweergave past zich aan het kaartformaat aan.

## Sterren en aantallen

- Geel: je allereerste waarneming van de soort is een waarneming uit deze reis.
- Oranje: de eerste openbare waarneming van de soort in het automatische
  reisgebied is een waarneming uit deze reis.
- Rood: de eerste openbare waarneming van de soort wereldwijd is uit deze reis.

Alle toepasselijke sterren staan naast elkaar. Geel krijgt een rode rand
wanneer minstens één reiswaarneming van de soort Research Grade heeft.
De vergelijking gebruikt het exacte waarnemingsnummer. De eigen geschiedenis
wordt wereldwijd gecontroleerd, ook als die buiten het reisgebied ligt.
Een eerdere waarneming op dezelfde kalenderdag maar buiten de gekozen tijden
kan daardoor verhinderen dat een nieuwe reiswaarneming een eerste is.

Soortenkaarten bevatten de eerste foto van je eerste geselecteerde waarneming,
het aantal tijdens deze reis en je totale openbare aantal. Foto's behouden hun
beeldverhouding. De samenvatting telt de hele reis, ook wanneer minder kaarten
zichtbaar zijn. Ontbrekende stercontroles worden als onzeker aangeduid.
Bij een zeer groot historisch gebied kan de oranje controle onvolledig blijven.
De app bewaart alleen de waarnemingsvelden die voor het rapport nodig zijn en
begrenst iNaturalist-verzoeken tot ongeveer zestig per minuut.

## Trips bewaren

Geef het rapport een naam en klik na de stercontrole op **Trip bewaren**.
In **Bewaarde trips** zoek je op naam, gebruiker, gebied of datum. De samenvatting
is direct beschikbaar. **Zoekkenmerken laden** herstelt gebruiker, datums en
beide tijden; maak daarna het rapport opnieuw om de locaties en het gebied
opnieuw te bepalen. Oude bewaarde trips zonder tijden krijgen 00:00 en 23:59.
Eventuele oude handmatige gebieden worden niet meer als zoekfilter gebruikt.

Trips worden lokaal in deze browser op dit apparaat bewaard, zonder account
of database. Download een JSON-reservekopie om ze te bewaren of in een andere
browser te importeren. Dit is een reservekopie van trips, geen CSV-soortenexport.
Browsergegevens wissen of privémodus kan bewaarde trips verwijderen.

## Installatie

Plaats alle Python-bestanden (inclusief **trip_map.py**), requirements.txt en
README.md bovenaan de repository. De map local_store_component is optioneel:
app.py bevat dezelfde browsercomponent als reserve. Start op Streamlit
Community Cloud met app.py, of lokaal:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Er zijn geen wachtwoorden of API-sleutels nodig. Internet is nodig voor
waarnemingen, foto's en achtergrondkaarten. Openbare taxonomie wordt lokaal
in .cache/taxonomy.sqlite3 hergebruikt.

## Controles

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
```
