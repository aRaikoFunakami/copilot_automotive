from langchain_core.tools import tool

from langchain_community.tools import TavilySearchResults

#import function_weather
import function_launch_navigation
import function_aircontrol
import realtime_function_seach_videos


tavily_tool = TavilySearchResults(
    max_results=5,
    include_answer=True,
    description=(
        "This is a search tool for accessing the internet.\n\n"
        "Let the user know you're asking your friend Tavily for help before you call the tool."
    ),
)

TOOLS = [
            tavily_tool,
            function_aircontrol.AirControl(),
            function_aircontrol.AirControlDelta(),
            function_launch_navigation.LaunchNavigation(),
            realtime_function_seach_videos.SearchVideos(),
        ]