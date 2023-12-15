import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from loguru import logger
from utils.llm import claude_to_sql, create_vector_embedding_with_bedrock, retrieve_results_from_opensearch, \
    upload_results_to_opensearch
from utils.apis import query_from_sql_pd
from utils.session_message import display_history_messages

load_dotenv()


def button_clicked(sample):
    # Update the selected_sample variable with the text of the clicked button
    st.session_state['selected_sample'] = sample
    st.session_state['show_assistant'] = False
    # st.session_state.show_assistant = True


def upvote_clicked(question, sql):
    # HACK: configurable opensearch endpoint
    target_profile = 'shopping_guide'
    aos_config = env_vars['data_sources'][target_profile]['opensearch']
    upload_results_to_opensearch(
        region_name=['region_name'],
        domain=aos_config['domain'],
        opensearch_user=aos_config['opensearch_user'],
        opensearch_password=aos_config['opensearch_password'],
        index_name=aos_config['index_name'],
        query=question,
        sql=st.session_state['result'],
        host=aos_config['opensearch_host'],
        port=aos_config['opensearch_port']
    )
    logger.info(f'up voted "{question}" with sql "{sql}"')


# load config.json as dictionary
with open(os.path.join(os.getcwd(), 'config_files', '1_config.json')) as f:
    env_vars = json.load(f)
    opensearch_config = env_vars['data_sources']['shopping_guide']['opensearch']
    for key in opensearch_config:
        opensearch_config[key] = os.getenv(opensearch_config[key].replace('$', ''))
    # logger.info(f'{opensearch_config=}')

st.set_page_config(layout="wide")

# Title and Description
st.title('Natural Language Querying Playground')
st.write("""
Welcome to the Natural Language Querying Playground! This interactive application is designed to bridge the gap between natural language and databases. 
Enter your query in plain English, and watch as it's transformed into a SQL or Pandas command. The result can then be visualized, giving you insights without needing to write any code. 
Experiment, learn, and see the power of NLQ in action!
""")
st.divider()

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

if 'current_profile' not in st.session_state:
    st.session_state['current_profile'] = ''

bedrock_model_ids = ['anthropic.claude-v2:1', 'anthropic.claude-v2', 'anthropic.claude-v1']

with st.sidebar:
    st.title('Setting')
    # The default option can be the first one in the profiles dictionary, if exists
    selected_profile = st.selectbox("Data Source Profile", list(st.session_state.get('profiles', {}).keys()))
    if selected_profile != st.session_state.current_profile:
        # clear session state
        st.session_state.selected_sample = ''
        st.session_state.result = ''
        st.session_state.current_profile = selected_profile

    st.session_state['option'] = st.selectbox("Choose your option", ["Text2SQL"])
    model_type = st.selectbox("Choose your model", bedrock_model_ids)

    use_rag = st.checkbox("Using RAG from Q/A Embedding", True)
    visualize_results = st.checkbox("Visualize Results", True)

# Part II: Search Section
st.subheader("Start Searching")

st.info("Quick Start: Click on the following buttons to start searching.")
# Pre-written search samples
search_samples = env_vars['data_sources'][selected_profile]['search_samples']

question_column_number = 3
# Create columns for the predefined search samples
search_sample_columns = st.columns(question_column_number)

# Display the predefined search samples as buttons within columns
for i, sample in enumerate(search_samples[0:question_column_number]):
    search_sample_columns[i].button(sample, use_container_width=True, on_click=button_clicked, args=[sample])

# Display more predefined search samples as buttons within columns, if there are more samples than columns
if len(search_samples) > question_column_number:
    with st.expander('More questions...'):
        more_sample_columns = st.columns(question_column_number)
        col_num = 0
        for i, sample in enumerate(search_samples[question_column_number:]):
            more_sample_columns[col_num].button(sample, use_container_width=True, on_click=button_clicked,
                                                args=[sample])
            if col_num == question_column_number - 1:
                col_num = 0
            else:
                col_num += 1

if "messages" not in st.session_state:
    st.session_state.messages = []

search_box = st.text_input('Search Box', value=st.session_state['selected_sample'],
                           placeholder='Type your query here...', max_chars=1000, key='search_box',
                           label_visibility='collapsed')

# add select box for which model to use
if st.button('Run', type='primary', use_container_width=True):
    # clear last query result
    st.session_state['result'] = ''
    if search_box == '':
        st.error("Please enter a valid query.")
    else:
        with st.chat_message("user"):
            st.markdown(search_box)
        with st.chat_message("assistant"):
            with st.spinner('Retrieving Q/A (Take up to 5s)'):
                logger.info('Retrieving samples...')
                retrieve_result = None
                if use_rag:
                    try:
                        # HACK: always use first opensearch
                        origin_selected_profile = selected_profile
                        selected_profile = "shopping_guide"

                        records_with_embedding = create_vector_embedding_with_bedrock(
                            search_box, index_name=env_vars['data_sources'][selected_profile]['opensearch']['index_name'])
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
                        selected_profile = origin_selected_profile
                    except Exception as e:
                        logger.exception(e)
                        logger.info(f"Failed to retrieve Q/A from OpenSearch: {str(e)}")
                        retrieve_result = []
                        selected_profile = origin_selected_profile

            with st.spinner('Generating SQL... (Take up to 20s)'):
                # Whether Retrieving Few Shots from Database
                logger.info('Sending request...')
                response = claude_to_sql(env_vars['data_sources'][selected_profile]['ddl'],
                                         env_vars['data_sources'][selected_profile]['hints'],
                                         search_box,
                                         examples=retrieve_result)

            logger.info(f'got llm response: {response}')

            st.session_state['result'] = response.split('```sql')[1].split('```')[0]
            st.session_state['gen_explanation'] = response.split('```')[-1]

            st.session_state.messages = []

            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": st.session_state['selected_sample']})

            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": st.session_state['result']})
            st.session_state.messages.append({"role": "assistant", "content": st.session_state['gen_explanation']})
            st.session_state['show_assistant'] = True

            st.markdown('The generated SQL statement is:')

            st.code(st.session_state['result'], language="sql")

            with st.expander(f'Retrieve result: {len(retrieve_result)}'):
                examples = []
                for example in retrieve_result:
                    examples.append({'Score': example['_score'],
                                     'Question': example['_source']['text'],
                                     'Answer': example['_source']['sql'].strip()})
                st.write(examples)

            if visualize_results:
                with st.spinner('Querying database...'):
                    try:
                        # execute the result
                        if st.session_state['option'] == "Text2SQL":
                            headers = {
                                'Content-Type': 'application/json'
                            }
                            pd_result = query_from_sql_pd(p_db_url=str(st.session_state['profiles'][selected_profile]),
                                                          query=str(st.session_state['result']))
                            st.session_state['dataframe'] = pd_result
                    except Exception as e:
                        logger.exception(e)
                        st.session_state['dataframe'] = None
                        st.error(f"Failed to execute SQL against database: {str(e)}")

            st.markdown('Generation process explanations:')
            st.markdown(st.session_state['gen_explanation'])

            st.markdown('You can provide feedback:')

            # add a upvote(green)/downvote button with logo
            feedback = st.columns(2)
            feedback[0].button('👍 Upvote (save as embedding for retrieval)', type='secondary', use_container_width=True,
                               on_click=upvote_clicked,args=[search_box, st.session_state['result']])

            if feedback[1].button('👎 Downvote', type='secondary', use_container_width=True):
                # do something here
                pass

        # Visualization Section
        if st.session_state['show_assistant']:
            if visualize_results:
                with st.chat_message("assistant"):
                    st.markdown('Visualizing the results:')
                    sql_query_result = st.session_state['dataframe']
                    if sql_query_result is not None:
                        # Auto-detect columns
                        visualize_config_columns = st.columns(3)

                        available_columns = sql_query_result.columns
                        x_column = visualize_config_columns[0].selectbox('Choose x-axis column', available_columns)
                        y_column = visualize_config_columns[1].selectbox('Choose y-axis column', available_columns)
                        chart_type = visualize_config_columns[2].selectbox('Choose the chart type',
                                                                           ['Table', 'Bar', 'Line', 'Pie'])

                        if chart_type == 'Table':
                            st.table(sql_query_result)
                        elif chart_type == 'Bar':
                            st.plotly_chart(px.bar(sql_query_result, x=x_column, y=y_column))
                        elif chart_type == 'Line':
                            st.plotly_chart(px.line(sql_query_result, x=x_column, y=y_column))
                        elif chart_type == 'Pie':
                            st.plotly_chart(px.pie(sql_query_result, names=x_column, values=y_column))
                    else:
                        st.markdown('No visualization generated.')

# display_history_messages()
