# Tripreport Verkenner

Een zelfstandige Streamlit-app voor afgeronde reizen op basis van openbare iNaturalist-waarnemingen. Gebouwd in dezelfde opzet als de aangeleverde Biodiversiteit Verkenner.

## Gebruik

1. Vul je openbare iNaturalist-gebruikersnaam en de eerste en laatste reisdag in.
2. Zoek desgewenst één of meer iNaturalist-plaatsen (land, provincie, streek), teken een veelhoek of rechthoek, of combineer die keuzes. De selectie is de **vereniging** van de gebieden: een waarneming in een van de gekozen plaatsen of in de tekening telt mee. Zonder gebiedskeuze worden alle openbare waarnemingen uit de periode gebruikt.
3. Klik op **Tripreport maken**. Sorteer het fotoraster taxonomisch of op het aantal eigen waarnemingen tijdens de reis. Download desgewenst de soortenlijst als CSV.

De sterren tonen de hoogste toepasselijke categorie per soort:

- Geel: de allereerste eigen iNaturalist-waarneming van die soort is een waarneming uit deze reis.
- Oranje: de allereerste openbare iNaturalist-waarneming van die soort in de gekozen plaats(en) en/of tekening is een waarneming uit deze reis.
- Rood: de allereerste openbare iNaturalist-waarneming van die soort wereldwijd is een waarneming uit deze reis.

De vergelijking gebruikt de waarnemingsdatum (`observed_on`) en controleert het **exacte waarnemingsnummer**, zodat een even oude waarneming van iemand anders niet ten onrechte een ster oplevert. De rangorde is rood, oranje, geel. Sterren worden alleen voor de zichtbare fotokaarten berekend en voor dezelfde sessie bewaard. Een vraagteken betekent dat de controle voor die soort niet lukte.

Bij een getekend gebied worden observaties in de begrenzende rechthoek opgehaald en daarna tegen de exacte veelhoek getoetst. Alleen waarnemingen met openbare coördinaten kunnen daarin worden opgenomen. Voor een historische veelhoek met meer dan 10.000 kandidaatwaarnemingen per soort wordt geen oranje ster toegekend; geel en rood blijven beschikbaar. Een drukke reisdag met meer dan 10.000 passende waarnemingen vraagt om een kleinere gebieds- of soortselectie. iNaturalist kan afgeschermde locaties anders behandelen dan openbare kaartcoördinaten.

## Installatie

Pak deze map uit en plaats `app.py`, `trip_data.py`, `taxonomy.py`, `requirements.txt` en `README.md` op het hoogste niveau van een eigen repository. Maak in Streamlit Community Cloud een app met `app.py` als startbestand, of start lokaal:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Er is geen wachtwoord of API-sleutel nodig. API-aanroepen worden begrensd tot ongeveer zestig per minuut. Vooral de eerste stercontrole bij veel soorten kan daarom enkele minuten duren. Openbare taxonomie wordt in `.cache/taxonomy.sqlite3` hergebruikt.

## Controles

```bash
python -m unittest discover -s tests -v
```
