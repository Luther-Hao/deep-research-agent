from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class Step(BaseModel):
    need_search: Optional[bool]
    title: str
    description: str
    step_type: str
    execution_res: Optional[str] = Field(
        default=None,
        description="The step execution result"
    )

class StepType(str,Enum):
    RESEARCH = "research"
    PROCESSING = "processing"
    REPORT = "report"

STEP_TYPE_TO_NODE_MAP = {
    StepType.RESEARCH :"researcher",
    StepType.PROCESSING:"coder",
    StepType.REPORT:"reporter",
}



class Plan(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    has_enough_context: Optional[bool]
    thought: str
    title: str
    steps: List[Step] = Field(
        default_factory=list,
        description="Research and Processing Steps"
    )

    def get_research_steps(self) -> List[Step]:
        research_type = {
            "research", "processing", "excel_analysing"
        }

        return [step for step in self.steps if step.step_type in research_type]


    def get_next_unexecuted_research_team_step(self) -> Optional[Step]:
        """获取第一个未执行的研究步骤"""
        for step in self.get_research_steps():
            if not step.execution_res:
                return step
        return None

    def get_completed_steps(self) -> List[Step]:
        return [step for step in self.steps if step.execution_res]

    def to_json(self, indent: Optional[int] = None) -> str:
        return self.model_dump_json(indent=indent)


