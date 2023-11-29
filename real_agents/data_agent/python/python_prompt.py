USER_PROMPT = """
history_code = \"\"\"{history_code}\"\"\"
human_question = \"\"\"{question}\"\"\"
data = \"\"\"{data}\"\"\"
reference_code = \"\"\"{reference_code}\"\"\"

history_dict = {{
    "history code": history_code,
    "human question": human_question,
    "data": data,
    "reference_code": reference_code,
}}
"""

"""
final format:
user_prompt + reference_prompt + history_prompt
"""
