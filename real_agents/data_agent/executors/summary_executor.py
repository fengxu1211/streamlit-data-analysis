from abc import ABC
from typing import Any, Dict, Tuple, Union
from langchain import PromptTemplate
from langchain.base_language import BaseLanguageModel
import pandas as pd
from real_agents.adapters.llm import LLMChain


class DataSummaryExecutor(ABC):
    tool_name = "DataProfiling"

    def _intelligent_summary(self, table_data: pd.DataFrame, num_insights: int, llm: BaseLanguageModel, df_name: str) -> str:
        """Use LLM to generate data summary."""
        pass


class TableSummaryExecutor(DataSummaryExecutor):
    SUMMARY_PROMPT_TEMPLATE = """
{table_info}

Provide a succinct yet meaningful summary of the table with less than 20 words, encapsulating its essence beyond just enumerating the columns. Please ensure your summary is a complete sentence and include it within <summary></summary> tags.
Note the table actually far more rows than shown above, so you MUST NOT make any rash conclusions based on the shown table rows or cells.
Then provide {num_insights} insightful and interesting suggestions in natural language that users can directly say to analyze the table. The suggestions should be able to be solved by python/sql.
The final results should be markdown '+' bullet point list, e.g., + The first suggestion.

Begin.
"""
    def run(
        self,
        df_name: str,
        df: pd.DataFrame,
        llm: BaseLanguageModel,
        use_intelligent_summary: bool = True,
        num_insights: int = 3,
    ) -> Dict[str, Any]:
        summary = ""

        # Basic summary
        summary += f"Your table {df_name} contains {df.shape[0]} rows and {df.shape[1]} columns. "

        null_count = df.isnull().sum().sum()  # Get total number of null values
        unique_values_avg = df.nunique().mean()  # Get average number of unique values

        summary += f"On average, each column has about {unique_values_avg:.0f} unique values. "
        if null_count > 0:
            summary += f"Watch out, there are {null_count} missing values in your data. "
        else:
            summary += "Good news, no missing values in your data. "

        # Intelligent summary
        if use_intelligent_summary:
            intelligent_summary = self._intelligent_summary(
                df,
                num_insights=num_insights,
                llm=llm,
                df_name=df_name
            )
            table_summary, suggestions = self._parse_output(intelligent_summary)
            summary += table_summary
            summary += "\n" + "Here are some additional insights to enhance your understanding of the table."
            summary += "\n" + suggestions

        return summary

    def _intelligent_summary(
        self, table_data: pd.DataFrame, num_insights: int, llm: BaseLanguageModel, df_name: str
    ) -> str:
        """Use LLM to generate data summary."""
        summary_prompt_template = PromptTemplate(
            input_variables=["table_info", "num_insights"],
            template=self.SUMMARY_PROMPT_TEMPLATE,
        )
        method = LLMChain(llm=llm, prompt=summary_prompt_template)
        table_info = (
            "Here are table columns and the first {} rows of the table"
            '(only a small part of the whole table) called "{}":\n'.format(5, df_name)
        )
        table_info += table_data.head(5).to_csv(sep="\t", index=False)
        result = method.run({"table_info": table_info, "num_insights": num_insights})
        return result

    def _parse_output(self, content: str) -> Tuple[str, str]:
        """Parse the output of the LLM to get the data summary."""
        from bs4 import BeautifulSoup

        # Using 'html.parser' to parse the content
        soup = BeautifulSoup(content, "html.parser")
        # Parsing the tag and summary contents
        try:
            table_summary = soup.find("summary").text
        except Exception:
            import traceback

            traceback.print_exc()
            table_summary = ""

        lines = content.split("\n")
        # Initialize an empty list to hold the parsed bullet points
        bullet_points = []
        # Loop through each line
        bullet_point_id = 1
        for line in lines:
            # If the line starts with '+', it is a bullet point
            if line.startswith("+"):
                # Remove the '+ ' from the start of the line and add it to the list
                bullet_points.append(f"{bullet_point_id}. " + line[1:].strip().strip('"'))
                bullet_point_id += 1
        return table_summary, "\n".join(bullet_points)


