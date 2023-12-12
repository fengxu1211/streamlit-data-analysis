import json
import os
import streamlit as st
from streamlit_ace import st_ace
import pandas as pd
import plotly.express as px
import sqlalchemy as db
from utils.llm import claude_to_sql, create_vector_embedding_with_bedrock, retrieve_results_from_opensearch, upload_results_to_opensearch
from utils.apis import query_from_database
import logging
from dotenv import load_dotenv
from decimal import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

# load config.json as dictionary
with open(os.path.join(os.getcwd(), 'config_files', '1_config.json')) as f:
    env_vars = json.load(f)
    opensearch_config = env_vars['data_sources']['shopping_guide']['opensearch']
    for key in opensearch_config:
        opensearch_config[key] = os.getenv(opensearch_config[key].replace('$', ''))
    logger.info(f'{opensearch_config=}')


st.set_page_config(layout="wide")

# Title and Description
st.title('Natural Language Querying Playground')
st.write("""
Welcome to the Natural Language Querying Playground! This interactive application is designed to bridge the gap between natural language and databases. 
Enter your query in plain English, and watch as it's transformed into a SQL or Pandas command. The result can then be visualized, giving you insights without needing to write any code. 
Experiment, learn, and see the power of NLQ in action!
""")

# Initialize or set up state variables
if 'profiles' not in st.session_state:
    st.session_state['profiles'] = {i: v['db_url'] for i, v in env_vars['data_sources'].items()}

if 'result' not in st.session_state:
    st.session_state['result'] = ''

if 'option' not in st.session_state:
    st.session_state['option'] = 'Text2SQL'

if 'show_assistant' not in st.session_state:
    st.session_state['show_assistant'] = False

if 'selected_sample' not in st.session_state:
    st.session_state['selected_sample'] = ''

if 'dataframe' not in st.session_state:
    st.session_state['dataframe'] = pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['A', 'B', 'C']
    })

st.markdown("<hr>", unsafe_allow_html=True)

bedrock_model_ids = ['anthropic.claude-v2:1', 'anthropic.claude-v2', 'anthropic.claude-v1']

with st.expander("Settings", expanded=True):
    # The default option can be the first one in the profiles dictionary, if exists
    selected_profile = st.selectbox("Data Source Profile", list(st.session_state.get('profiles', {}).keys()))
    st.session_state['option'] = st.selectbox("Choose your option", ["Text2SQL"])
    model_type = st.selectbox("Choose your model", bedrock_model_ids)

    use_rag = st.checkbox("Using RAG from Q/A Embedding", True)
    visualize_results = st.checkbox("Visualize Results", True)

# Part II: Search Section
st.subheader("Start Searching")

with st.expander("Quick Start: Click on the following buttons to start searching.", expanded=True):
    # Pre-written search samples
    # search_samples = ["oppty最多的use case是什么", "oppty最少的行业是什么", "最近三个月行业涨跌趋势", "aaa"]
    # search_samples = ["what is top 10 use case campaign name with the most oppty", "what is the top 10 industry with the most oppty",
    #                   "what is the number of opptys grouped by oppty stages"]
    search_samples = env_vars['data_sources'][selected_profile]['search_samples']

    # Create columns for the predefined search samples
    search_sample_columns = st.columns(3)

    # Display the predefined search samples as buttons within columns
    for i, sample in enumerate(search_samples):
        if search_sample_columns[i].button(sample, use_container_width=True):
            # Update the selected_sample variable with the text of the clicked button
            st.session_state['selected_sample'] = sample
            st.session_state['show_assistant'] = False

    if "messages" not in st.session_state:
        st.session_state.messages = []

    search_box = st.text_input('Search Box', value=st.session_state['selected_sample'],
                               placeholder='Type your query here...', max_chars=1000, key='search_box',
                               label_visibility='collapsed')
    # add select box for which model to use
    continue_execution = True
    if st.button('Run', type='primary', use_container_width=True):
        # clear last query result
        st.session_state['result'] = ''
        if search_box == '':
            st.error("Please enter a valid query.")
            continue_execution = False

        if continue_execution:
            with st.spinner('Retrieving Q/A (Take up to 5s)'):
                logger.info('Retrieving samples...')
                retrieve_result = None
                if use_rag:
                    try:
                        records_with_embedding = create_vector_embedding_with_bedrock(search_box, index_name=
                        env_vars['data_sources'][selected_profile]['opensearch']['index_name'])
                        retrieve_result = retrieve_results_from_opensearch(
                            index_name=env_vars['data_sources'][selected_profile]['opensearch']['index_name'],
                            region_name=env_vars['data_sources'][selected_profile]['opensearch']['region_name'],
                            domain=env_vars['data_sources'][selected_profile]['opensearch']['domain'],
                            opensearch_user=env_vars['data_sources'][selected_profile]['opensearch']['opensearch_user'],
                            opensearch_password=env_vars['data_sources'][selected_profile]['opensearch'][
                                'opensearch_password'],
                            host=env_vars['data_sources'][selected_profile]['opensearch'][
                                'opensearch_host'],
                            port=env_vars['data_sources'][selected_profile]['opensearch'][
                                'opensearch_port'],
                            query_embedding=records_with_embedding['vector_field'],
                            top_k=2)
                    except Exception as e:
                        logger.exception(e)
                        logger.info(f"Failed to retrieve Q/A from OpenSearch: {str(e)}")
                        retrieve_result = None

            with st.spinner('Generating SQL... (Take up to 20s)'):
                # Whether Retrieving Few Shots from Database
                logger.info('Sending request...')
                # if model_type == "SQLCoder":
                #     # Here you will usually call the API, but it is commented out as per the requirement.
                #     payload = {
                #         'hints': env_vars['data_sources'][selected_profile]['hints'],
                #         'ddl': env_vars['data_sources'][selected_profile]['ddl'],
                #         'question': search_box,
                #         "use_rag": use_rag,
                #         "chain_of_thoughts": chain_of_thoughts
                #     }
                #     response = sqlcoder(env_vars['SQLCoder']['ENDPOINT'], payload)
                response = claude_to_sql(env_vars['data_sources'][selected_profile]['ddl'],
                                         env_vars['data_sources'][selected_profile]['hints'],
                                         search_box,
                                         examples=retrieve_result)

            logger.info('got llm response: ')
            logger.info(response)
            # if model_type == "SQLCoder":
            #     st.session_state['result'] = response.json()['response']
            # elif model_type == "Claude 2":
            st.session_state['result'] = response.split('```sql')[1].split('```')[0]
            st.session_state['gen_explanation'] = response.split('```')[-1]

            st.session_state.messages = []

            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": st.session_state['selected_sample']})

            # for mock purpose
            # st.session_state['result'] = mock_data.get(st.session_state['option'], "")

            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": st.session_state['result']})
            st.session_state.messages.append({"role": "assistant", "content": st.session_state['gen_explanation']})
            st.session_state['show_assistant'] = True

            if visualize_results:
                with st.spinner('Visualizing Results...'):
                    # for mock purpose
                    # st.session_state['result'] = '''SELECT tagging.use_case_campaign_name
                    #  FROM   tagging
                    #  GROUP BY tagging.use_case_campaign_name
                    #  ORDER BY count(*) DESC
                    #  LIMIT 10;'''

                    try:
                        # execute the result
                        if st.session_state['option'] == "Text2SQL":
                            headers = {
                                'Content-Type': 'application/json'
                            }
                            result = query_from_database(p_db_url=str(st.session_state['profiles'][selected_profile]),
                                                         query=str(st.session_state['result']))
                            logger.info(f'{result=}')
                            st.session_state['dataframe'] = pd.DataFrame(eval(result['data']),
                                                                         columns=result['columns'])
                    except Exception as e:
                        logger.exception(e)
                        st.session_state['dataframe'] = None
                        st.error(f"Failed to execute SQL against database: {str(e)}")

# Visualization Section
if st.session_state['show_assistant']:
    st.subheader("Execution Result")
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.chat_message("user"):
        st.markdown(search_box)

    with st.chat_message("assistant"):
        st.markdown('The generated SQL statement is:')

        code_snippet = st.code(st.session_state['result'], language="sql")
        # st_ace(
        #     value=st.session_state['result'],
        #     language="sql" if st.session_state['option'] == "Text2SQL" else "python",
        #     theme="monokai",
        #     key="ace-editor",
        #     font_size=20,
        #     height=300,
        #     wrap=True
        # )

    with st.chat_message("assistant"):
        st.markdown('Generation process explanations:')
        st.markdown(st.session_state['gen_explanation'])

    with st.chat_message("assistant"):
        st.markdown('You can provide feedback:')

        # add a upvote(green)/downvote button with logo
        feedback = st.columns(2)
        if feedback[0].button('👍 Upvote (save as embedding for retrieval)', type='secondary', use_container_width=True):
            upload_results_to_opensearch(
                region_name=env_vars['data_sources'][selected_profile]['opensearch']['region_name'],
                domain=env_vars['data_sources'][selected_profile]['opensearch']['domain'],
                opensearch_user=env_vars['data_sources'][selected_profile]['opensearch']['opensearch_user'],
                opensearch_password=env_vars['data_sources'][selected_profile]['opensearch']['opensearch_password'],
                index_name=env_vars['data_sources'][selected_profile]['opensearch']['index_name'],
                query=search_box,
                sql=st.session_state['result'],
                host=env_vars['data_sources'][selected_profile]['opensearch'][
                    'opensearch_host'],
                port=env_vars['data_sources'][selected_profile]['opensearch'][
                    'opensearch_port']
            )
        if feedback[1].button('👎 Downvote', type='secondary', use_container_width=True):
            # do something here
            pass

    if visualize_results:
        with st.chat_message("assistant"):
            st.markdown('Visualizing the results:')

            if st.session_state['dataframe'] is not None:
                st.markdown('The generated visualization is:')
                # Auto-detect columns
                available_columns = st.session_state['dataframe'].columns
                x_column = st.selectbox('Choose x-axis column', available_columns)
                y_column = st.selectbox('Choose y-axis column', available_columns)

                chart_type = st.selectbox('Choose the chart type', ['Table', 'Bar', 'Line', 'Pie'])
                if chart_type == 'Table':
                    st.table(st.session_state['dataframe'])
                elif chart_type == 'Bar':
                    st.plotly_chart(px.bar(st.session_state['dataframe'], x=x_column, y=y_column))
                elif chart_type == 'Line':
                    st.plotly_chart(px.line(st.session_state['dataframe'], x=x_column, y=y_column))
                elif chart_type == 'Pie':
                    st.plotly_chart(px.pie(st.session_state['dataframe'], names=x_column, values=y_column))
            else:
                st.markdown('No visualization generated.')

