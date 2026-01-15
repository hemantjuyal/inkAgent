from crewai.tools import BaseTool
from crewai_tools import ScrapeElementFromWebsiteTool

class WebsiteSearchTool(BaseTool):
    name: str = "Website Search Tool"
    description: str = "A tool to scrape and extract text content from web pages."

    def _run(self, url: str, css_selector: str = None) -> str:
        if css_selector:
            return ScrapeElementFromWebsiteTool().run(website_url=url, css_selector=css_selector)
        else:
            return ScrapeElementFromWebsiteTool().run(website_url=url)