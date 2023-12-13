# -*- coding: utf-8 -*-
import os
import json
import streamlit as st
from streamlit_ace import st_ace
import sqlalchemy as db
from dotenv import load_dotenv

# load config.json as dictionary
load_dotenv()

# load config.json as dictionary
with open(os.path.join(os.getcwd(), 'config_files', '1_config.json')) as f:
    env_vars = json.load(f)
    opensearch_config = env_vars['data_sources']['shopping_guide']['opensearch']
    for key in opensearch_config:
        opensearch_config[key] = os.getenv(opensearch_config[key].replace('$', ''))
    print(f'{opensearch_config=}')

st.set_page_config(layout="wide")

st.session_state['view_profiles'] = env_vars['data_sources']

# st.subheader("Add new data source profile")

# Mapping of popular databases to their corresponding SQLAlchemy dialects
db_mapping = {
    'pg': 'postgresql+psycopg2',
    'mysql': 'mysql+pymysql',
    # Add more mappings here for other databases
}

# Part I: Manage Database Profiles Section
# with st.expander("Click to Edit Data Source Profile (Optional - Using default DB)", expanded=True):
#     col1, col2 = st.columns(2)
#
#     with col1:
#         profile_name = st.text_input("Enter profile name")
#         db_type = st.selectbox("Select database type", ['pg', 'mysql'])  # Add more options as needed
#         port = st.text_input("Enter port")
#     with col2:
#         user = st.text_input("Enter username")
#         password = st.text_input("Enter password", type="password")
#         db_name = st.text_input("Enter database name")
#
#     if st.button('Test Connection'):
#         try:
#             db_url = f"{db_mapping[db_type]}://{user}:{password}@localhost:{port}/{db_name}"
#             engine = db.create_engine(db_url)
#             connection = engine.connect()
#             st.success(f"Connected successfully to {profile_name}!")
#         except Exception as e:
#             st.error(f"Failed to connect: {str(e)}")
#
#     if st.button('Add Profile'):
#         if profile_name and db_type and port and user and password and db_name:
#             db_url = f"{db_mapping[db_type]}://{user}:{password}@localhost:{port}/{db_name}"
#             st.session_state['profiles'][profile_name] = db_url
#             # save to json
#             env_vars['data_sources'][profile_name] = {
#                 'db_url': db_url,
#                 'ddl': {},
#                 'hints': "",
#                 'opensearch': ""
#             }
#             with open('config.json', 'w') as f:
#                 json.dump(env_vars, f)
#             st.success(f"Profile {profile_name} added successfully!")
#         else:
#             st.error("Please enter all the required fields.")

st.subheader("Edit profile")

with st.expander("Select a profile", expanded=True):
    selected_profile = st.selectbox("", list(st.session_state['view_profiles'].keys()))

    # if st.button('Delete Profile'):
    #     confirm = st.checkbox("Please confirm deletion")
    #     if confirm:
    #         del st.session_state['profiles'][selected_profile]
    #         st.success(f"Profile {selected_profile} deleted successfully!")

    # Add hints
    st.write("For customizing, please go and edit config.json directly.")
    if selected_profile:
        # json_config = st.text_area("JSON Content", json.dumps(env_vars['data_sources'][selected_profile], indent=4).encode('utf-8').decode('unicode_escape'), height=400)
        # if st.button("Auto-generate"):
        #     # Retrieve tables information and assemble JSON
        #     try:
        #         engine = db.create_engine(env_vars['data_sources'][selected_profile]['db_url'])
        #         connection = engine.connect()
        #         metadata = db.MetaData()
        #         if 'schema' in env_vars['data_sources'][selected_profile]:
        #             metadata.reflect(bind=connection, schema=env_vars['data_sources'][selected_profile]['schema'])
        #         else:
        #             metadata.reflect(bind=connection)
        #         tables = metadata.tables
        #         table_info = {}
        #
        #         for table_name, table in tables.items():
        #             # Start the DDL statement
        #             ddl = f"CREATE TABLE {table_name} -- {table.comment} (\n"
        #             column_descriptions = []
        #             for column in table.columns:
        #                 # get column description
        #                 ddl += f"  {column.name} {column.type} -- {column.comment},\n"
        #             ddl = ddl.rstrip(',\n') + "\n)"  # Remove the last comma and close the CREATE TABLE statement
        #             table_info[table_name] = {}
        #             table_info[table_name]['ddl'] = ddl
        #             table_info[table_name]['description'] = table.comment
        #         st.session_state['table_info'] = table_info
        #         st.success("Auto-generation complete!")
        #
        #     except Exception as e:
        #         st.error(f"Failed to auto-generate JSON: {str(e)}")
        #
        # if st.button('Save JSON'):
        #     try:
        #         with open('config.json') as f:
        #             profiles = json.load(f)
        #         profiles['data_sources'][selected_profile]['ddl'] = st.session_state['table_info']
        #         with open('config.json', 'w', encoding='utf-8') as f:
        #             json.dump(profiles, f, ensure_ascii=False, indent=4)
        #         st.success("JSON saved successfully!")
        #     except Exception as e:
        #         st.error(f"Failed to save JSON: {str(e)}")

        st.write(env_vars['data_sources'][selected_profile])

