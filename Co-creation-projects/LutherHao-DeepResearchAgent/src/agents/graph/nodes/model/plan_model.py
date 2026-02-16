from typing import Optional, List

from pydantic import BaseModel, Field


class Step:
    need_search: Optional[bool]
    title: str
    description: str
    execution_res: Optional[str] = Field(
        default=None,
        description="The step execution result"
    )


class Plan(BaseModel):
    has_enough_context: Optional[bool]
    thought: str
    title: str
    steps: List[Step] = Field(
        default_factory=list,
        description="Research and Processing Steps"
    )

    def get_research_steps(self) -> List[Step]:
        research_type = {
            "research","processing","excel_analysing"
        }

        return [step for step in self.steps if step in research_type]


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


