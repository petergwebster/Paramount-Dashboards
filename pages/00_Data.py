import streamlit as st
from pathlib import Path
import pandas as pd

from data_loader import load_workbook_tables

st.set_page_config(page_title='Data', layout='wide')

st.title('Data Loader Verification')

xlsx_path = Path('data/current.xlsx')

if not xlsx_path.exists():
    st.error('Missing data/current.xlsx. Add a workbook at data/current.xlsx to proceed.')
    st.stop()

mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit='s')
file_size_mb = round(xlsx_path.stat().st_size / (1024 * 1024), 2)

st.markdown('**Current file**')
st.write(str(xlsx_path))
st.write('Last modified')
st.write(mod_ts)
st.write('Size MB')
st.write(file_size_mb)

# Load sheet names (fast)
_, _, all_sheets = load_workbook_tables(str(xlsx_path), selected_sheets=[])

st.markdown('**Select which tabs you want the dashboard to use**')
selected = st.multiselect('Sheets', options=all_sheets, default=all_sheets)

min_text_cells = st.slider('Header detection sensitivity (min non-empty cells in header row)', 2, 10, 4)

if st.button('Load and preview selected tabs'):
    tables, meta_df, _ = load_workbook_tables(
        str(xlsx_path),
        selected_sheets=selected,
        min_text_cells=min_text_cells
    )

    st.markdown('### Sheet cleaning summary')
    st.dataframe(meta_df, use_container_width=True)

    st.markdown('### Previews')
    for sn in selected:
        st.markdown('#### ' + sn)
        if sn not in tables:
            st.warning('No table loaded for this sheet')
            continue

        df_prev = tables[sn]
        st.write('Shape')
        st.write(df_prev.shape)
        st.dataframe(df_prev.head(25), use_container_width=True)

        csv_bytes = df_prev.to_csv(index=False).encode('utf-8')
        st.download_button(
            'Download cleaned CSV for ' + sn,
            data=csv_bytes,
            file_name=sn.replace('/', '_') + '.csv',
            mime='text/csv'
        )
