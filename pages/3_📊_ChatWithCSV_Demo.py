from typing import Union

import streamlit as st
import pandas as pd
import sys
import os
from io import StringIO

from loguru import logger
from streamlit.runtime.uploaded_file_manager import UploadedFile

from real_agents import Constants
from real_agents.adapters.data_model import TableDataModel, JsonDataModel
from real_agents.data_agent.executors.summary_executor import TableSummaryExecutor
from langchain.schema import AgentAction
from agent import create_agent, llm
import base64
from io import BytesIO
from PIL import Image
from PIL.Image import Image as PILImage
import textwrap

st.set_page_config(
    page_title="Chat With CSV Demo",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)


def init_log():
    """Initialize loguru log information"""
    # Just for sys.stdout log message
    format_stdout = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | <lvl>{level}</lvl>"
        ": {message}"
    )

    logger.remove()

    logger.configure(
        handlers=[
            dict(sink=sys.stdout, format=format_stdout, level="TRACE"),
        ],
    )

    return logger


def write_response(response_dict: dict):
    """
    Write a response from an agent to a Streamlit app.
    Args:
        response_dict: The response from the agent.
    Returns:
        None.
    """
    resp_list = []
    # Check if the response is an answer.
    if 'output' in response_dict:
        result_area = st.empty()
        output_text = response_dict["output"]
        result_container = result_area.container()
        # wrap long text into 100 chars per line
        wrapped_lines = textwrap.wrap(output_text, 100)
        result_container.text('\n'.join(wrapped_lines))
        resp_list.append('\n'.join(wrapped_lines))
        with st.expander('Intermediate Results'):
            if isinstance(response_dict["intermediate_steps"], list):
                for (agent_action, json_data_model) in response_dict["intermediate_steps"]:
                    if isinstance(agent_action, AgentAction):
                        st.markdown(agent_action.log)
                    if isinstance(json_data_model, JsonDataModel):
                        st.write('Generated python code:')
                        py_code = json_data_model.raw_data['intermediate_steps']
                        st.code(py_code)

                        if json_data_model.raw_data['success']:
                            # display image stored in python code executed result
                            for image in json_data_model.raw_data['images']:
                                if 'image/png' in image.data:
                                    data = image.data['image/png']
                                    image_data = base64.b64decode(data)
                                    image = Image.open(BytesIO(image_data))
                                    result_container.image(image, caption='PNG Image')
                                    resp_list.append(image)

                                # print('local code result:', json_data_model.raw_data['result'])
                                # exec(json_data_model.raw_data['intermediate_steps'], {}, locals_dict)
                                # st.pyplot(locals_dict['fig'])
                                # resp_list.append(locals_dict['fig'])
                            st.write('Code executed output:')
                            if isinstance(json_data_model.raw_data['result'], str):
                                st.text(json_data_model.raw_data['result'])
    else:
        st.write(response_dict)

    return resp_list


def preview_csv(file: Union[UploadedFile, str]) -> (str, pd.DataFrame):
    """ Function to preview CSV file.
    Args:
        file: The uploaded CSV file.
    Returns:
        filename and dataframe.
    """
    if file is not None:
        if isinstance(file, str):
            df = pd.read_csv(file, index_col=False)
            filename = os.path.basename(file)
        elif isinstance(file, UploadedFile):
            string_data = StringIO(file.getvalue().decode('utf-8'))
            filename = file.name
            df = pd.read_csv(string_data, index_col=False)

        return filename, df


def profile_data(filename, dataframe):
    """Function to perform data profiling using Langchain agent.
    Args:
        agent: The Langchain agent.
        dataframe: The pandas DataFrame to profile.
    Returns:
        dict: Profiling result.
    """
    results = TableSummaryExecutor().run(filename, dataframe, llm)
    return results.__str__()


def get_session_messages() -> list:
    return st.session_state.csv_messages


def set_session_messages(messages: list):
    if "csv_messages" not in st.session_state:
        st.session_state.csv_messages = messages


def persist_assistant_message(message):
    get_session_messages().append({"role": "assistant", "content": message})


def persist_user_message(message):
    get_session_messages().append({"role": "user", "content": message})


init_log()

set_session_messages([])

if 'data_file' not in st.session_state:
    st.session_state.data_file = None

if 'data_filename' not in st.session_state:
    st.session_state.data_filename = None

if 'has_profiled' not in st.session_state:
    st.session_state.has_profiled = False

st.sidebar.title("👨‍💻 Chat with your CSV")

available_models = {
    "Claude2(Bedrock)": "anthropic.claude-v2",
}

with st.sidebar:
    files = os.listdir(os.path.join(os.getcwd(), Constants.DataFilesFolder))
    csv_files = [f for f in files if f.endswith('.csv')]
    csv_files.insert(0, 'Not selected')
    selected_csv_file = st.radio(':computer: Choose existing files:', csv_files)
    st.write("You selected:", selected_csv_file)
    if selected_csv_file != 'Not selected':
        filename, df = preview_csv(os.path.join(os.getcwd(), Constants.DataFilesFolder, selected_csv_file))
        # if selected file has changed, then reset messages and profiling flag
        if filename != st.session_state.data_filename:
            logger.info(f'selected file: {filename}')
            set_session_messages([])
            st.session_state.has_profiled = False
            st.session_state.data_file = df
            st.session_state.data_filename = filename

    # Add facility to upload a dataset
    try:
        uploaded_file = st.file_uploader(":computer: Or upload a new CSV file:", type="csv")
        if uploaded_file:
            # save the uploaded_file to DataFilesFolder
            with open(os.path.join(os.getcwd(), Constants.DataFilesFolder, uploaded_file.name), 'wb') as f:
                f.write(uploaded_file.getbuffer())

            filename, df = preview_csv(uploaded_file)
            st.session_state.data_file = df
            st.session_state.data_filename = filename
    except Exception as e:
        st.error("File failed to load. Please select a valid CSV file.")
        logger.error("File failed to load.\n" + str(e))

    selected_model = st.selectbox(
        ":brain: Choose your model(s):",
        tuple(available_models.keys())
    )
    selected_model_id = available_models[selected_model]

logger.info(f'program start. current messages length: {len(get_session_messages())}')
for message in get_session_messages():
    with st.chat_message(message["role"]):
        if isinstance(message["content"], list):
            for seg in message["content"]:
                if isinstance(seg, str):
                    st.text(seg)
                elif isinstance(seg, tuple):
                    # tuple should be written as markdown
                    st.write(seg[0])
                elif isinstance(seg, PILImage):
                    st.image(seg)
                else:
                    st.write(seg)
        else:
            st.write(message["content"])

if not st.session_state.has_profiled and st.session_state.data_file is not None:
    file_df = st.session_state.data_file
    filename = st.session_state.data_filename
    with st.chat_message("assistant"):
        st.write(file_df.head())
        with st.spinner('analyzing...'):
            profile_result = profile_data(filename, file_df)
            write_response(profile_result)
            message_list = [file_df.head(), (profile_result, 'md')]
            st.session_state.has_profiled = True
        if 'SaaSSales' in filename:
            with st.expander("Click here for more sample questions..."):
                more_questions_md = """
                    4. show me an bar chart of monthly total sales using order date in the format of yyyy-mm.
                    5. what are the top 5 most profitable customers?
                """
                st.markdown(more_questions_md)
                message_list.append((more_questions_md, 'md'))
        persist_assistant_message(message_list)

if query := st.chat_input("Insert your query", disabled=not st.session_state.data_filename):
    file_df = st.session_state.data_file
    filename = st.session_state.data_filename
    persist_user_message(query)
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner('thinking...'):
            gs = TableDataModel.from_raw_data(
                raw_data=file_df,
                raw_data_name=filename,
            )
            agent_exec = create_agent({'defaultfile': gs})
            response = agent_exec({'input': query})

            # Write the response to the Streamlit app.
            resp_list = write_response(response)
            persist_assistant_message(resp_list)

logger.info(f'program end. current messages length: {len(get_session_messages())}')
