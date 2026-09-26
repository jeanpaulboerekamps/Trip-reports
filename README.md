# Tripreport Verkenner

Een zelfstandige Streamlit-app voor afgeronde reizen op basis van openbare iNaturalist-waarnemingen. Gebouwd in dezelfde opzet als de aangeleverde Biodiversiteit Verkenner.

## Gebruik

1. Vul je openbare iNaturalist-gebruikersnaam en de eerste en laatste reisdag in.
2. Zoek desgewenst één of meer iNaturalist-plaatsen (land, provincie, streek), teken een veelhoek of rechthoek, of combineer die keuzes. De selectie is de **vereniging** van de gebieden: een waarneming in een van de gekozen plaatsen of in de tekening telt mee. Zonder gebiedskeuze worden alle openbare waarnemingen uit de periode gebruikt.
3. Klik op **Tripreport maken**. Sorteer het fotoraster taxonomisch of op het aantal eigen waarnemingen tijdens de reis. Standaard worden alle gevonden soorten getoond; met de schuifregelaar kun je dit aantal verkleinen. Download desgewenst de soortenlijst als CSV.

De sterren tonen de hoogste toepasselijke categorie per soort:

- Geel: de allereerste eigen iNaturalist-waarneming van die soort is een waarneming uit deze reis.
- Oranje: de allereerste openbare iNaturalist-waarneming van die soort in de gekozen plaats(en) en/of tekening is een waarneming uit deze reis.
- Rood: de allereerste openbare iNaturalist-waarneming van die soort wereldwijd is een waarneming uit deze reis.

Een gele ster krijgt een rode rand als minstens één van de geselecteerde reiswaarnemingen van die soort Research Grade heeft. Iedere fotokaart toont zowel het aantal waarnemingen tijdens deze reis als je totale openbare iNaturalist-aantal van die soort, inclusief ondersoorten. De samenvatting telt alle soorten van de reis, ongeacht hoeveel kaarten zichtbaar zijn. Nieuw voor mij en nieuw in gebied zijn onafhankelijke aantallen: een soort kan voor jou al bekend en tegelijk nieuw voor het gebied zijn, of andersom. Een wereldwijde eerste telt ook als eigen eerste en, als er een gebied is gekozen, als eerste in dat gebied. Zonder gebiedskeuze toont het gebiedscijfer een streepje. Bij een onvolledige stercontrole worden de nieuwe aantallen als ondergrens weergegeven.

De vergelijking gebruikt de waarnemingsdatum (`observed_on`) en controleert het **exacte waarnemingsnummer**, zodat een even oude waarneming van iemand anders niet ten onrechte een ster oplevert. De rangorde is rood, oranje, geel. De fotokaarten verschijnen direct en blijven op hun plek tijdens de stercontrole. Alleen de voortgangsbalk verandert; na afloop worden de kaarten één keer met de sterren bijgewerkt. Alle reissoorten worden in groepen van maximaal veertig gecontroleerd en de uitkomst blijft binnen dezelfde sessie bewaard. De app controleert eigen en gebiedsgeschiedenis onafhankelijk. Alleen wanneer geen van beide een eerdere waarneming oplevert, is een wereldwijde eerste nog mogelijk. Onafhankelijke controles binnen een fase lopen gelijktijdig, met een gedeelde limiet voor API-verzoeken. Alleen mogelijke primeurs krijgen vervolgens een afzonderlijke controle. Als de snelle groepscontrole faalt, kun je die opnieuw proberen of bewust de tragere controle per soort starten. Een vraagteken betekent dat die individuele controle niet lukte.

Bij een getekend gebied worden observaties in de begrenzende rechthoek opgehaald en daarna tegen de exacte veelhoek getoetst. Alleen waarnemingen met openbare coördinaten kunnen daarin worden opgenomen. Voor een historische veelhoek met meer dan 10.000 kandidaatwaarnemingen per soort wordt geen oranje ster toegekend; geel en rood blijven beschikbaar. Een drukke reisdag met meer dan 10.000 passende waarnemingen vraagt om een kleinere gebieds- of soortselectie. iNaturalist kan afgeschermde locaties anders behandelen dan openbare kaartcoördinaten.

## Installatie

Pak deze map uit en plaats `app.py`, `trip_data.py`, `taxonomy.py`, `requirements.txt` en `README.md` op het hoogste niveau van een eigen repository. Maak in Streamlit Community Cloud een app met `app.py` als startbestand, of start lokaal:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Er is geen wachtwoord of API-sleutel nodig. API-aanroepen worden begrensd tot ongeveer zestig per minuut. Bij veel zichtbare soorten kan het aanvullen van alle sterren nog enkele minuten duren, maar het fotogrid blijft intussen zichtbaar. Openbare taxonomie wordt in `.cache/taxonomy.sqlite3` hergebruikt.

## Controles

```bash
python -m unittest discover -s tests -v
```
