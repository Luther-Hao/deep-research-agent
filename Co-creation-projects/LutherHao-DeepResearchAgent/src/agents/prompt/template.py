import dataclasses
import os
from datetime import datetime
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.infrastructure.config.configuration import Configuration

env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True
)

def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template.
    :param prompt_name:
    :return:
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name} : {e}")


def apply_prompt_template(
        prompt_name:str,
        state: dict,
        configurable: Configuration = None
)-> List:
    """
    Apply a prompt template.
    :param prompt_name:
    :param state:
    :param configurable:
    :return:
    """

    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M%S %z"),
        **state
    }

    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        return [{"role":"system", "content": system_prompt}] + state["message"]
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name} : {e}")
