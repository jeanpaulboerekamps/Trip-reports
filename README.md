# Tripreport Verkenner

Een zelfstandige Streamlit-app voor afgeronde reizen op basis van openbare iNaturalist-waarnemingen. Gebouwd in dezelfde opzet als de aangeleverde Biodiversiteit Verkenner.

## Gebruik

1. Vul je openbare iNaturalist-gebruikersnaam en de eerste en laatste reisdag in. Beide datumvelden laten datums vanaf 1 januari 1965 kiezen.
2. Zoek desgewenst een iNaturalist-plaats (land, provincie, streek) of teken een veelhoek of rechthoek. Een nieuwe keuze vervangt standaard het vorige gebied. Een unieke exacte plaatsnaam, ook zonder accent getypt, wordt direct gekozen. Bij meerdere treffers kies je een resultaat en klik je op **Gebied vervangen**. Vink **Samenvoegen met huidig gebied** aan wanneer je meerdere plaatsen als één gebied wilt gebruiken; bij een nieuwe tekening bestaat dezelfde optie. Een waarneming in een van de samengevoegde plaatsen of in de tekening telt dan mee. Het rapport vermeldt het werkelijk actieve gebied. Zonder gebiedskeuze worden alle openbare waarnemingen uit de periode gebruikt.
3. Klik op **Tripreport maken**. Sorteer het fotoraster taxonomisch of op het aantal eigen waarnemingen tijdens de reis. Standaard worden alle gevonden soorten getoond; met de schuifregelaar kun je dit aantal verkleinen. Download desgewenst de soortenlijst als CSV of maak een PDF met het volledige overzicht.

## Trips bewaren en terugvinden

Na het maken en controleren van een trip kun je boven de samenvatting een naam invullen en op **Trip bewaren** klikken. In **Bewaarde trips** zoek je later op naam, iNaturalist-gebruiker, gebied of datum. De lijst toont de opgeslagen samenvatting zonder iNaturalist opnieuw te bevragen. **Zoekkenmerken laden** zet de gebruiker, datums en het gebied terug in de invoervelden; klik vervolgens op **Tripreport maken** om het actuele foto-overzicht opnieuw op te bouwen. Een geladen trip kun je met bijgewerkte aantallen opnieuw bewaren.

De gegevens staan in de lokale opslag van deze browser op dit apparaat. Je hebt geen account of database nodig. Gebruik **Reservekopie downloaden** en bewaar het JSON-bestand zelf; met **Reservekopie importeren** kun je de trips in een andere browser overzetten. De import voegt trips op hun unieke ID samen en vervangt een bestaande trip met dezelfde ID. Browsergegevens wissen of privémodus gebruiken kan opgeslagen trips verwijderen. Foto's en de volledige soortenlijst worden niet bewaard.

De sterren tonen alle toepasselijke categorieën per soort naast elkaar:

- Geel: de allereerste eigen iNaturalist-waarneming van die soort is een waarneming uit deze reis.
- Oranje: de allereerste openbare iNaturalist-waarneming van die soort in de gekozen plaats(en) en/of tekening is een waarneming uit deze reis.
- Rood: de allereerste openbare iNaturalist-waarneming van die soort wereldwijd is een waarneming uit deze reis.

Een gele ster krijgt een rode rand als minstens één van de geselecteerde reiswaarnemingen van die soort Research Grade heeft. Iedere fotokaart gebruikt de eerste foto van je eigen eerste geselecteerde waarneming van die soort (als die een foto heeft) en toont zowel het aantal waarnemingen tijdens deze reis als je totale openbare iNaturalist-aantal van die soort, inclusief ondersoorten. De samenvatting toont ook het aantal geselecteerde waarnemingen dat nog niet op soort is geïdentificeerd. Dit is het verschil tussen alle geselecteerde waarnemingen en de waarnemingen die in het soortenraster meetellen. Ze telt alle soorten van de reis, ongeacht hoeveel kaarten zichtbaar zijn. Nieuw voor mij en nieuw in gebied zijn onafhankelijke aantallen: een soort kan voor jou al bekend en tegelijk nieuw voor het gebied zijn, of andersom. Een wereldwijde eerste telt ook als eigen eerste en, als er een gebied is gekozen, als eerste in dat gebied. Zonder gebiedskeuze toont de app duidelijk dat er geen gebied actief is en berekent hij geen oranje sterren. Zoek een plaats en klik op **Plaats toevoegen**, of teken een gebied, en maak het tripreport opnieuw. Bij een onvolledige stercontrole worden de nieuwe aantallen als ondergrens weergegeven.

De vergelijking gebruikt de waarnemingsdatum (`observed_on`) en controleert het **exacte waarnemingsnummer**, zodat een even oude waarneming van iemand anders niet ten onrechte een ster oplevert. Alle toepasselijke sterren verschijnen, in de volgorde geel, oranje, rood. De fotokaarten verschijnen direct en blijven op hun plek tijdens de stercontrole. Alleen de voortgangsbalk verandert; na afloop worden de kaarten één keer met de sterren bijgewerkt. Alle reissoorten worden in groepen van maximaal veertig gecontroleerd en de uitkomst blijft binnen dezelfde sessie bewaard. De app controleert eigen en gebiedsgeschiedenis onafhankelijk. De eerste eigen waarnemingen in de reisperiode worden wereldwijd in één paginagewijze zoekactie bepaald, zodat een eerdere eigen waarneming buiten het gebied correct meetelt en veel individuele API-verzoeken vervallen. Alleen wanneer geen van beide een eerdere waarneming oplevert, is een wereldwijde eerste nog mogelijk. Onafhankelijke controles binnen een fase lopen gelijktijdig, met een gedeelde limiet voor API-verzoeken. Alleen mogelijke primeurs krijgen vervolgens een afzonderlijke controle. Als de snelle groepscontrole faalt, kun je die opnieuw proberen of bewust de tragere controle per soort starten. Een vraagteken betekent dat die individuele controle niet lukte. Foto's behouden hun volledige beeldverhouding in het raster en in de PDF.

Bij een getekend gebied worden observaties in de begrenzende rechthoek opgehaald en daarna tegen de exacte veelhoek getoetst. Alleen waarnemingen met openbare coördinaten kunnen daarin worden opgenomen. Voor een historische veelhoek met meer dan 10.000 kandidaatwaarnemingen per soort wordt geen oranje ster toegekend; geel en rood blijven beschikbaar. Een drukke reisdag met meer dan 10.000 passende waarnemingen vraagt om een kleinere gebieds- of soortselectie. iNaturalist kan afgeschermde locaties anders behandelen dan openbare kaartcoördinaten.

Bij het ophalen bewaart de app per waarneming alleen de velden die voor het tripreport nodig zijn. Dit beperkt het geheugengebruik bij grotere reizen.

## Installatie

Pak deze map uit en plaats alle Python-bestanden, `requirements.txt` en `README.md` op het hoogste niveau van je repository. De browsercomponent zit ook in `app.py`; de meegeleverde map `local_store_component` is optioneel. Maak in Streamlit Community Cloud een app met `app.py` als startbestand, of start lokaal:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Voor alleen het opbouwen van een tripreport is geen wachtwoord of API-sleutel nodig; voor duurzaam bewaren wel. iNaturalist API-aanroepen worden begrensd tot ongeveer zestig per minuut. Bij veel zichtbare soorten kan het aanvullen van alle sterren nog enkele minuten duren, maar het fotogrid blijft intussen zichtbaar. Openbare taxonomie wordt in `.cache/taxonomy.sqlite3` hergebruikt.

## Controles

```bash
python -m unittest discover -s tests -v
```

## PDF

Klik boven de fotokaarten op **PDF van volledig overzicht maken** en daarna op **PDF downloaden**. De PDF bevat alle soorten in de gekozen sorteervolgorde, met je eigen eerste reiswaarnemingsfoto waar beschikbaar. Het ophalen van veel foto’s kan enige tijd duren; foto’s die niet geladen kunnen worden krijgen een lege achtergrond.
