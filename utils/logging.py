from loguru import logger
import sys

def init_log():
    pass
    """Initialize loguru log information"""
    # Just for sys.stdout log message
    # format_stdout = (
    #     "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | <lvl>{level}</lvl>"
    #     ": {message}"
    # )
    #
    # logger.remove()
    #
    # logger.configure(
    #     handlers=[
    #         dict(sink=sys.stdout, format=format_stdout, level="TRACE"),
    #     ],
    # )
    #
    # return logger