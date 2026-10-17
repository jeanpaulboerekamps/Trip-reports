"""Read-only trip comparisons, based entirely on already stored summaries."""
import pandas as pd
import altair as alt
import streamlit as st


def ranking_data(rows, birds):
    result = []
    for row in rows:
        nature = row.get('summary') or {}
        bird = birds.get(row['id']) or {}
        result.append({
            'Trip': row['name'], 'Van': row['start_date'], 'Tot': row['end_date'],
            'iNat waarnemingen': nature.get('observations', 0),
            'iNat soorten': nature.get('species', 0),
            'iNat nieuwe soorten': nature.get('own', 0),
            'eBird waarnemingen': bird.get('Waarnemingen'),
            'eBird soorten': bird.get('Soorten'),
            'eBird nieuwe soorten': bird.get('Nieuw voor mij'),
            'iNat onbekend tot soort': nature.get('unidentified', 0),
        })
    return result


def show_rankings(rows, birds, view):
    data = ranking_data(rows, birds)
    if not data:
        st.info('Nog geen trips beschikbaar.')
        return
    if view == 'Trips in de tijd':
        st.subheader('Trips in de tijd')
        st.caption('Nieuwste trips links. Beweeg over een staaf voor de tripnaam en alle zes kengetallen. Een ontbrekende eBird-export wordt niet als nul weergegeven.')
        ordered = sorted(data, key=lambda x: (x['Van'], x['Tot'], x['Trip']), reverse=True)
        plotted = []
        for i, item in enumerate(ordered):
            for source, key in [('iNaturalist', 'iNat soorten'), ('eBird', 'eBird soorten')]:
                if item[key] is not None:
                    plotted.append({**item, 'Positie': i, 'Bron': source, 'Aantal soorten': item[key],
                                    'Label': f"{item['Van']} · {item['Trip']}"})
        if not plotted:
            st.info('Geen soortenaantallen beschikbaar.')
            return
        chart = alt.Chart(pd.DataFrame(plotted)).mark_bar().encode(
            x=alt.X('Label:N', sort=[f"{x['Van']} · {x['Trip']}" for x in ordered], title='Trip (nieuwste links)',
                    axis=alt.Axis(labelAngle=-65, labelLimit=135)),
            xOffset=alt.XOffset('Bron:N', sort=['iNaturalist', 'eBird']),
            y=alt.Y('Aantal soorten:Q', title='Aantal soorten'),
            color=alt.Color('Bron:N', sort=['iNaturalist', 'eBird'],
                            scale=alt.Scale(domain=['iNaturalist', 'eBird'], range=['#3b985e', '#438bbd'])),
            tooltip=[alt.Tooltip('Trip:N'), alt.Tooltip('Van:N'), alt.Tooltip('Tot:N'),
                     alt.Tooltip('iNat waarnemingen:Q'), alt.Tooltip('iNat soorten:Q'),
                     alt.Tooltip('iNat nieuwe soorten:Q'), alt.Tooltip('eBird waarnemingen:Q'),
                     alt.Tooltip('eBird soorten:Q'), alt.Tooltip('eBird nieuwe soorten:Q')]
        ).properties(width=max(850, len(ordered)*35), height=400)
        st.altair_chart(chart, use_container_width=False)
        return
    metrics = {
        'Top trips – soorten iNaturalist': 'iNat soorten',
        'Top trips – soorten eBird': 'eBird soorten',
        'Top trips – nieuwe soorten iNaturalist': 'iNat nieuwe soorten',
        'Top trips – nieuwe soorten eBird': 'eBird nieuwe soorten',
        'Top trips – onbekend tot soort iNaturalist': 'iNat onbekend tot soort',
    }
    metric = metrics[view]
    eligible = [x for x in data if x[metric] is not None]
    eligible.sort(key=lambda x: (-x[metric], x['Trip'].casefold()))
    st.subheader(view)
    if not eligible:
        st.info('Geen eBird-gegevens beschikbaar. Importeer je eBird-export onderaan de pagina.')
        return
    table = pd.DataFrame(eligible)
    table.insert(0, 'Plaats', range(1, len(table)+1))
    order = ['Plaats', 'Trip', metric, 'Van', 'Tot', 'iNat waarnemingen', 'iNat soorten',
             'iNat nieuwe soorten', 'eBird waarnemingen', 'eBird soorten', 'eBird nieuwe soorten']
    order = list(dict.fromkeys(order))
    st.dataframe(table[order], hide_index=True, use_container_width=True, height=min(680, 40 + 35*len(table)))
