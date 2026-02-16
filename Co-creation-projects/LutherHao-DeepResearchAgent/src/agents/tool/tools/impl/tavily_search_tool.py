import json

from typing import Optional, List, Dict, Tuple, Union

import aiohttp
import requests
from langchain_community.tools import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper, TAVILY_API_URL
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_tavily import TavilySearch
from pydantic import Field


class EnhancedTavilySearchWrapper(TavilySearchAPIWrapper):
    def raw_results(
            self,
            query: str,
            max_results: Optional[int] = 5,
            search_depth: Optional[str] = "advanced",
            include_domains: Optional[List[str]] = [],
            exclude_domains: Optional[List[str]] = [],
            include_answer: Optional[bool] = False,
            include_raw_content: Optional[bool] = False,
            include_images: Optional[bool] = False,
            include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        params = {
            "query": query,
            "api_key": self.tavily_api_key.get_secret_value(),
            "max_results": max_results,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions
        }

        response = requests.post(
            f"{TAVILY_API_URL}/search",
            json=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    async def raw_results_async(
            self,
            query: str,
            max_results: Optional[int] = 5,
            search_depth: Optional[str] = "advanced",
            include_domains: Optional[List[str]] = [],
            exclude_domains: Optional[List[str]] = [],
            include_answer: Optional[bool] = False,
            include_raw_content: Optional[bool] = False,
            include_images: Optional[bool] = False,
            include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        async def fetch() -> str:
            params = {
                "query": query,
                "api_key": self.tavily_api_key.get_secret_value(),
                "max_results": max_results,
                "search_depth": search_depth,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions
            }
            timeout_config = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(
                        f"{TAVILY_API_URL}/search",
                        json=params
                ) as res:
                    if res.status == 200:
                        data = await res.text()
                        return data
                    else:
                        raise Exception(f"Error {res.status}:{res.reason}")

        result = await fetch()
        return json.loads(result)

    def clean_results_with_image(self, raw_results: List[Dict]) -> List[Dict]:
        results = raw_results["results"]
        clean_results = []
        for result in results:
            clean_result = {
                "type": "page",
                "title": result["title"],
                "url": result["url"],
                "content": result["content"],
                "score": result["score"]
            }
            if raw_content := result.get("raw_content"):
                clean_result["content"] = raw_content
            clean_results.append(clean_result)
        images = raw_results["images"]
        for image in images:
            clean_result = {
                "type": "image",
                "image_url": image["url"],
                "image_description": image["image_description"]
            }
            clean_results.append(clean_result)
        return clean_results


class MultiTavilySearch(TavilySearchResults):
    include_image_descriptions: bool = False
    api_wrapper: EnhancedTavilySearchWrapper = Field(default_factory=EnhancedTavilySearchWrapper)

    def _run(self,
             query: str,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> Tuple[Union[List[Dict[str, str]], str], Dict]:
        try:
            raw_results = self.api_wrapper.raw_results(
                query,
                self.max_results,
                self.search_depth,
                self.include_domains,
                self.exclude_domains,
                self.include_answer,
                self.include_raw_content,
                self.include_images,
                self.include_image_descriptions
            )
        except Exception as e:
            return repr(e), {}

        cleaned_results = self.api_wrapper.clean_results_with_image(raw_results)
        print("sync", json.dumps(cleaned_results, indent=2, ensure_ascii=False))
        return cleaned_results, raw_results


if __name__ == "__main__":
    pass




