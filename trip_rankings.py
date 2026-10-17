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
        from datetime import date
        import html
        from streamlit.components.v1 import html as show_html
        st.subheader('Trips in de tijd')
        st.caption('Nieuwste jaren links. Scroll horizontaal door de jaren; elk blok toont de zes kerncijfers.')
        dated = []
        for item in data:
            try:
                day = date.fromisoformat(str(item['Van'])[:10])
                dated.append((day, item))
            except (ValueError, TypeError):
                pass
        if not dated:
            st.info('Geen geldige reisdatums beschikbaar.')
            return
        first_year = min(day.year for day, _ in dated)
        last_year = max(day.year for day, _ in dated)
        year_width = 1050
        width = (last_year-first_year+1)*year_width
        def esc(x): return html.escape(str(x))
        def val(x): return '—' if x is None else esc(x)
        years = ''.join(f'<div class="year" style="left:{(last_year-y)*year_width}px;width:{year_width}px">{y}</div>' for y in range(last_year,first_year-1,-1))
        quarters = ''.join(f'<div class="quarter" style="left:{(last_year-y)*year_width+(4-q)*year_width/4}px">Q{q} {y}</div>' for y in range(last_year,first_year-1,-1) for q in range(4,0,-1))
        cards=[]
        axis_bars=[]
        connectors=[]
        maximum=max((float(it["iNat soorten"] or 0) for _,it in dated),default=1)
        maximum=max(maximum,max((float(it["eBird soorten"] or 0) for _,it in dated),default=1),1)
        # Overlapping dates get separate vertical lanes.
        lanes=[]
        for day,item in sorted(dated,key=lambda z:z[0],reverse=True):
            fraction=(day-date(day.year,1,1)).days/(date(day.year+1,1,1)-date(day.year,1,1)).days
            x=(last_year-day.year)*year_width+(1-fraction)*year_width
            lane=next((i for i,limit in enumerate(lanes) if abs(x-limit)>150),len(lanes))
            if lane==len(lanes):lanes.append(x)
            else:lanes[lane]=x
            y=65+(lane%4)*105
            nat=float(item['iNat soorten'] or 0); bird=float(item['eBird soorten'] or 0)
            # A shared scale makes the vertical bars comparable across all trips.
            axis_bars.append((x,nat,bird))
            rows=''.join(f'<tr><td>{label}</td><td>{val(item[a])}</td><td>{val(item[b])}</td></tr>' for label,a,b in [('Obs.','iNat waarnemingen','eBird waarnemingen'),('Soorten','iNat soorten','eBird soorten'),('Nieuw','iNat nieuwe soorten','eBird nieuwe soorten')])
            connectors.append(f'<line x1="{x:.1f}" y1="{y+102:.1f}" x2="{x:.1f}" y2="{axis_y if False else 482}" stroke="#77828d" stroke-width="1" opacity=".8"/>')
            cards.append(f'<div class="trip" style="left:{x-70:.1f}px;top:{y}px"><strong>{esc(item["Trip"])}</strong><small>{esc(item["Van"])} t/m {esc(item["Tot"])}</small><table><tr><th></th><th>iNat</th><th>eBird</th></tr>{rows}</table></div>')
        axis_y=485
        height=axis_y+45
        vertical_bars=[]
        for x,nat,bird in axis_bars:
            for offset,value,kind in [(-12,nat,'nat'),(2,bird,'bird')]:
                if value > 0:
                    bar_height=max(3, 340*value/maximum)
                    vertical_bars.append(f'<div class="axis-bar {kind}" title="{kind}: {int(value)} soorten" style="left:{x+offset:.1f}px;top:{axis_y-bar_height:.1f}px;height:{bar_height:.1f}px"></div>')
        time_axis=f'<div class="time-axis" style="top:{axis_y}px"></div>'
        legend=f'<div class="axis-legend" style="top:{axis_y+12}px"><span class="nat-key">■</span> iNaturalist soorten &nbsp; <span class="bird-key">■</span> eBird soorten · Hoogte op dezelfde schaal (maximum {int(maximum):,})</div>'
        markup=f'''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>
        body{{font:13px Arial,sans-serif;margin:0;color:#252525}}.scroll{{overflow-x:auto;overflow-y:auto;max-height:550px;border:1px solid #ddd;border-radius:9px}}.canvas{{position:relative;width:{width+300}px;height:{height}px;background:repeating-linear-gradient(90deg,#fff 0px,#fff 261px,#edf0f2 262px,#fff 263px)}}
        .year{{position:absolute;top:8px;font-size:17px;font-weight:bold;border-bottom:2px solid #aaa;padding:3px 8px;box-sizing:border-box}}.quarter{{position:absolute;top:43px;color:#777}}.trip{{position:absolute;width:140px;height:102px;overflow:hidden;z-index:3;box-sizing:border-box;background:white;border:1px solid #d6d9df;border-radius:8px;padding:5px;box-shadow:0 2px 5px #0002}}strong{{display:block;font-size:10px;line-height:1.12;max-height:23px;overflow:hidden}}small{{display:block;color:#777;margin:2px 0;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.axis-bar{{position:absolute;width:12px;z-index:1;border-radius:3px 3px 0 0;opacity:.85}}.nat{{background:#3b985e}}.bird{{background:#438bbd}}.time-axis{{position:absolute;left:0;right:0;border-top:2px solid #737b85}}.axis-legend{{position:absolute;left:12px;color:#555;font-size:12px}}.nat-key{{color:#3b985e}}.bird-key{{color:#438bbd}}table{{width:100%;font-size:9px;margin-top:2px;border-collapse:collapse}}td:not(:first-child),th:not(:first-child){{text-align:right}}td{{padding:1px 0}}
        </style></head><body><div class="scroll"><div class="canvas">{years}{quarters}{''.join(vertical_bars)}{time_axis}{legend}<svg style="position:absolute;left:0;top:0;pointer-events:none;z-index:2" width="{width+300}" height="{height}">{''.join(connectors)}</svg>{''.join(cards)}</div></div></body></html>'''
        show_html(markup,height=height+15,scrolling=False)
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
    source = 'eBird' if metric.startswith('eBird') else 'iNat'
    source_cols = (["eBird waarnemingen", "eBird soorten", "eBird nieuwe soorten"]
                   if source == 'eBird' else
                   ["iNat waarnemingen", "iNat soorten", "iNat nieuwe soorten"])
    if metric == 'iNat onbekend tot soort':
        source_cols.append(metric)
        remaining = eligible
        start_rank = 1
    else:
        import html
        medals = ['🥇', '🥈', '🥉']
        top_items = []
        # Show all three figures from the selected source, with the ranking
        # metric first. Never mix eBird and iNaturalist figures in one ranking.
        display_cols = [metric] + [col for col in source_cols if col != metric]
        labels = {'iNat waarnemingen': 'Waarn.', 'iNat soorten': 'Soorten',
                  'iNat nieuwe soorten': 'Nieuw', 'eBird waarnemingen': 'Waarn.',
                  'eBird soorten': 'Soorten', 'eBird nieuwe soorten': 'Nieuw'}
        header = '<div class="rank-row rank-header"><span></span><span>Trip</span>' + ''.join(
            '<span>' + labels[col] + '</span>' for col in display_cols) + '</div>'
        for i, item in enumerate(eligible[:10]):
            number = medals[i] if i < 3 else f'{i+1}.'
            values = ''.join('<span class="rank-value' + (' rank-primary' if col == metric else '') + '">' +
                             ('—' if item[col] is None else f'{item[col]:,}'.replace(',', '.')) + '</span>'
                             for col in display_cols)
            top_items.append('<div class="rank-row"><span class="rank-number">' + number +
                             '</span><span class="rank-name">' + html.escape(str(item['Trip'])) +
                             '</span>' + values + '</div>')
        st.markdown('''<style>
        .rank-frame{border:1px solid #d6dbe1;border-radius:12px;padding:10px 15px;margin:8px 0 20px;background:var(--secondary-background-color, #f8f9fb)}
        .rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) repeat(3,minmax(60px,85px));gap:8px;align-items:center;padding:9px 5px;border-bottom:1px solid #d9dfe4;font-size:14px}
        .rank-row:last-child{border-bottom:0}.rank-number{font-weight:700;font-size:17px}.rank-name{font-weight:600;overflow-wrap:anywhere}.rank-value{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.rank-primary{font-weight:750}.rank-header{color:#777;font-size:12px;font-weight:600;padding-top:3px;padding-bottom:6px}.rank-header span:nth-child(n+3){text-align:right}
        @media(max-width:600px){.rank-frame{padding:7px}.rank-row{grid-template-columns:25px minmax(0,1fr) repeat(3,minmax(42px,65px));gap:4px;font-size:12px;padding:8px 2px}.rank-number{font-size:14px}.rank-header{font-size:10px}}
        </style>''', unsafe_allow_html=True)
        st.markdown('<div class="rank-frame">' + header + ''.join(top_items) + '</div>', unsafe_allow_html=True)
        remaining = eligible[10:]
        start_rank = 11
        if remaining:
            st.caption('Overige trips – vanaf plaats 11')
    if remaining:
        table = pd.DataFrame(remaining)
        table.insert(0, 'Plaats', range(start_rank, start_rank+len(table)))
        order = list(dict.fromkeys(['Plaats', 'Trip', metric] + source_cols))
        st.dataframe(table[order], hide_index=True, use_container_width=True,
                     height=min(680, 40 + 35*len(table)))
