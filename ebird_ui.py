"""eBird overview and private browser persistence for imported personal data."""
import hashlib
import json
import tempfile
from pathlib import Path
from datetime import date
from uuid import uuid4

import pandas as pd
import streamlit as st
from streamlit.components.v1 import declare_component

from ebird_data import read_export, EbirdIndex, bird_csv

_STORE_HTML = '''<!doctype html><html><body style="margin:0"><script>
let lastNonce = null;
function send(type,extra={}){window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*');}
function database(){return new Promise((resolve,reject)=>{const request=indexedDB.open('tripreport-ebird-v1',1);request.onupgradeneeded=()=>request.result.createObjectStore('exports');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}
async function operate(op,data){const db=await database();try{return await new Promise((resolve,reject)=>{const tx=db.transaction('exports',op==='save'?'readwrite':'readonly');const store=tx.objectStore('exports');const request=op==='save'?store.put(data,'personal'):store.get('personal');let value=null;request.onsuccess=()=>{value=op==='save'?data:request.result||null;};tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('Opslag afgebroken'));});}finally{db.close();}}
window.addEventListener('message',async event=>{if(event.data.type!=='streamlit:render')return;const {op='load',nonce='initial',data}=event.data.args||{};if(nonce===lastNonce)return;lastNonce=nonce;try{const result=await operate(op,data);if(lastNonce!==nonce)return;send('streamlit:setComponentValue',{dataType:'json',value:{nonce,data:result,error:''}});}catch(error){if(lastNonce!==nonce)return;send('streamlit:setComponentValue',{dataType:'json',value:{nonce,data:null,error:String(error.message||error)}});}});
send('streamlit:componentReady',{apiVersion:1});send('streamlit:setFrameHeight',{height:0});
</script></body></html>'''
_store_dir = Path(tempfile.gettempdir()) / 'tripreport-ebird-store-v25'
_store_dir.mkdir(parents=True, exist_ok=True)
(_store_dir / 'index.html').write_text(_STORE_HTML, encoding='utf-8')
_ebird_store = declare_component('trip_ebird_store', path=str(_store_dir))


def load_ebird_index():
    """Load/import the private export once, before rendering the shared trip table."""
    action = st.session_state.get('ebird_storage_action', {'op': 'load', 'nonce': 'initial'})
    event = _ebird_store(**action, key='ebird_personal_store', default=None)
    if isinstance(event, dict) and event.get('nonce') != st.session_state.get('ebird_storage_nonce'):
        st.session_state.ebird_storage_nonce = event.get('nonce')
        st.session_state.ebird_storage_error = event.get('error', '')
        st.session_state.ebird_storage_action = {'op': 'load', 'nonce': event.get('nonce')}
        if event.get('data'):
            st.session_state.ebird_data = event['data']
    with st.expander('eBird-export importeren of vernieuwen', expanded=not bool(st.session_state.get('ebird_data'))):
        st.caption('Upload MyEBirdData.csv of de originele eBird-zip. De import wordt in deze browser bewaard en vervangt de vorige eBird-import.')
        with st.form('ebird_import'):
            upload = st.file_uploader('Persoonlijke eBird-export', type=['zip', 'csv'], key='ebird_export_upload')
            submit = st.form_submit_button('eBird-export laden')
        if submit:
            if upload is None:
                st.error('Kies eerst je eBird-export.')
            else:
                try:
                    with st.spinner('eBird-export verwerken…'):
                        data = read_export(upload.getvalue())
                    nonce = str(uuid4())
                    st.session_state.ebird_data = data
                    st.session_state.ebird_storage_action = {'op': 'save', 'nonce': nonce, 'data': data}
                    st.session_state.ebird_storage_nonce = None
                    st.rerun()
                except (ValueError, UnicodeError, OSError) as exc:
                    st.error(str(exc))
    if st.session_state.get('ebird_storage_error'):
        st.warning('eBird kon niet in deze browser worden bewaard. De geladen export blijft beschikbaar zolang deze sessie open is. ' + st.session_state.ebird_storage_error)
    data = st.session_state.get('ebird_data')
    if not data:
        st.info('Importeer je eBird-export om de vogels voor je bewaarde trips te bekijken.')
        return None
    try:
        index = EbirdIndex(data)
    except (ValueError, KeyError, TypeError) as exc:
        st.error('De bewaarde eBird-import kon niet worden gelezen. Importeer de originele export opnieuw.')
        return None
    st.caption(f"Import: {len(data['observations']):,} waarnemingen op {len(data['checklists']):,} checklists; {data['first_date']} t/m {data['last_date']}.".replace(',', '.'))
    st.caption('Waarnemingen = vogelregels op checklists. Ondersoorten worden op soort samengevoegd; onbepaalde vogels, hybriden en domestic types staan apart. Nieuw voor mij = eerste datum van die soort in deze export valt binnen de trip.')
    st.caption('eBird gebruikt uitsluitend de tripdatums; gebied en tijdstip tellen niet mee. Nieuwe trips worden direct uit deze import berekend.')
    return index


def render_ebird_birds(selected, index):
    """Show the eBird bird details for the selected row of the combined table."""
    if selected is None or index is None:
        return
    summary, birds = index.trip(selected)
    st.subheader('Vogels — ' + selected['name'])
    if not birds:
        st.info('Geen eBird-waarnemingen in deze tripperiode in de geladen export.')
        return
    only_new = st.checkbox('Alleen nieuwe soorten voor mij', key='ebird_only_new')
    visible = [bird for bird in birds if bird['Nieuw voor mij']] if only_new else birds
    if visible:
        st.dataframe(pd.DataFrame(visible), hide_index=True, use_container_width=True,
                     column_config={'Nieuw voor mij': st.column_config.CheckboxColumn('Nieuw voor mij'),
                                    'Op soort': st.column_config.CheckboxColumn('Op soort')})
        safe_name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in selected['name']).strip('-') or 'trip'
        st.download_button('Vogellijst downloaden (CSV)', bird_csv(visible), f'ebird-{safe_name}.csv', 'text/csv', key='ebird_birds_download')
    else:
        st.info('Geen nieuwe soorten in deze trip.')
    st.caption('Bekend aantal is de som van opgegeven aantallen, geen aantal unieke vogels. X betekent aanwezig zonder opgegeven aantal. Overlappende trips kunnen dezelfde checklists bevatten.')
