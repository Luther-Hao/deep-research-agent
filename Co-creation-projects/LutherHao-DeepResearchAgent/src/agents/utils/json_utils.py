import json
import logging

import json_repair

logger = logging.getLogger(__name__)

def repair_json_output(content:str) -> str:
    content=content.strip()
    if content.startswith(('{','[')) or "```json" in content or "```ts" in content:
        try:
            if content.startswith("```json"):
                content = content.removeprefix("```json")

            if content.startswith("```ts"):
                content = content.removeprefix("```ts")


            if content.startswith("```"):
                content = content.removesuffix("```")

            repaired_content = json_repair.loads(content)
            return json.dumps(repaired_content, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to repair json: {e}")
        return content