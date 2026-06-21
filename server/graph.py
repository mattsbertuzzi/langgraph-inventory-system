from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from state import StockState
from nodes.weather_getter import get_7day_forecast
from nodes.tool_caller import call_tools
from nodes.stock_setter import set_stock
from tools.forecast_tools import get_sales_by_month, get_sales_by_week, get_sales_by_day, get_sales_by_weather, get_sales_by_temperature_range

def build_graph():
    graph = StateGraph(StockState)

    tools = [get_sales_by_month, get_sales_by_week, get_sales_by_day, get_sales_by_weather, get_sales_by_temperature_range]
    tool_node = ToolNode(tools)

    graph.add_node('get_weather', get_7day_forecast)
    graph.add_node('call_tools', call_tools)
    graph.add_node('tools', tool_node)
    graph.add_node('set_stocks', set_stock)

    def tool_router(state: StockState) -> str:
        last_message = state.get('messages')[-1]
        if last_message.tool_calls:
            return 'tools'
        return 'set_stocks'

    graph.add_edge(START, 'get_weather')
    graph.add_edge('get_weather', 'call_tools')
    graph.add_conditional_edges('call_tools', tool_router, {
        'tools': 'tools',
        'set_stocks': 'set_stocks',
    })
    graph.add_edge('tools', 'call_tools')
    graph.add_edge('set_stocks', END)

    return graph.compile()



