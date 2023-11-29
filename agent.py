# agent.py
from langchain.chat_models import ChatOpenAI
from real_agents.adapters.interactive_executor import initialize_agent
from real_agents.adapters.agent_helpers import Tool
from real_agents.adapters.data_model import DataModel, JsonDataModel
from typing import Dict, List, Union
from real_agents.adapters.memory import ConversationReActBufferMemory, \
    ReadOnlySharedStringMemory
from real_agents.data_agent import CodeGenerationExecutor
from loguru import logger
import os

API_KEY = os.environ.get("OPENAI_API_KEY", 'sk-abc')
API_BASE = os.environ.get("OPENAI_API_BASE", "http://localhost:18000/v1")

# llm = ChatOpenAI(openai_api_key=API_KEY, model_name='gpt-4-1106-preview', temperature=0)
llm = ChatOpenAI(openai_api_key=API_KEY, openai_api_base=API_BASE,
                 model_name='anthropic.claude-v2', temperature=0, verbose=True, max_tokens=4096)


def create_agent(grounding_source_dict):
    memory = ConversationReActBufferMemory(
        memory_key="chat_history", return_messages=True, llm=llm, max_token_limit=3500
    )
    read_only_memory = ReadOnlySharedStringMemory(memory=memory)

    python_code_generation_executor = CodeGenerationExecutor(
        programming_language="python", memory=read_only_memory)

    def run_python_code_builder(term: str) -> Union[Dict, DataModel]:
        try:
            input_grounding_source = [gs for gs in grounding_source_dict.values()]
            # Get the result
            results = python_code_generation_executor.run(
                user_intent=term,
                llm=llm,
                grounding_source=input_grounding_source,
                code_execution_mode='local',
                jupyter_kernel_pool=None,
                user_id='DefaultUser'
            )

            logger.bind(msg_head=f"PythonCodeBuilder results({llm})").debug(results)

            if results["result"]["success"]:
                if results["result"]["result"] is not None:
                    raw_output = results["result"]["result"]
                elif results["result"]["stdout"] != "":
                    raw_output = results["result"]["stdout"]
                else:
                    raw_output = ""
                # check if we can get plot image from python code tool
                observation = JsonDataModel.from_raw_data(
                    {
                        "success": True,
                        "result": raw_output,
                        "images": results["result"]["outputs"] if "pyplot" in results[
                            "intermediate_steps"] else [],
                        "intermediate_steps": results["intermediate_steps"],
                    },
                    filter_keys=["images"],
                )
            else:
                observation = JsonDataModel.from_raw_data(
                    {
                        "success": False,
                        "result": results["result"]["error_message"],
                        "intermediate_steps": results["intermediate_steps"],
                    }
                )
            return observation
        except Exception as e:
            logger.bind(msg_head=f"PythonCodeBuilder error({llm})").error(str(e))
            import traceback
            traceback.print_exc()
            results = "got an exception!!!"
            return results["result"]

    code_builder = Tool(
        name="PythonCodeBuilder",
        func=run_python_code_builder,
        description="""
    Description: This tool adeptly turns your textual problem or query into Python code & execute it to get results. It shines when dealing with mathematics, data manipulation tasks, general computational problems and basic visualization like matplotlib. Please note it does not generate database queries.
    Input: A natural language problem or question.
    Output: A Python program + its execution result to solve the presented problem or answer the question.
    Note: The tool MUST be used whenever you want to generate & execute Python code.
                    """,
    )
    tools = [code_builder]

    agent_exec = initialize_agent(
        tools=tools,
        llm=llm,
        max_iterations=3,
        early_stopping_method='generate',
        memory=memory
    )

    return agent_exec
