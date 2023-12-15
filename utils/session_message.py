import streamlit as st
from loguru import logger


def display_history_messages():
    logger.info(f'{st.session_state.messages=}')
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], list):
                for seg in message["content"]:
                    if isinstance(seg, str):
                        st.text(seg)
                    else:
                        st.write(seg)
            else:
                st.write(message["content"])
