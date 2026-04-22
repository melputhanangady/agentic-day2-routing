from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
import operator

@tool
def check_order_status(order_id: str) -> dict:
    """Check the status of an order."""
    # Mock implementation
    return {
        "order_id": order_id,
        "status": "shipped",
        "eta": "2024-01-20"
    }

@tool
def create_ticket(issue: str, priority: str) -> dict:
    """Create a support ticket for human review."""
    return {
        "ticket_id": "TKT12345",
        "issue": issue,
        "priority": priority
    }

load_dotenv()

tools = [check_order_status, create_ticket]
tool_node = ToolNode(tools)

llm = ChatOpenAI(model="gpt-4.1-nano",seed=6)
llm_with_tools = llm.bind_tools(tools)

class SupportState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    should_escalate: bool
    issue_type: str
    user_tier: str # vip or standard

# --- Nodes ---

def check_user_tier_node(state:SupportState):
    """Decide if user is VIP or Standard(mock implementation)."""
    first_message=state["messages"][0].content.lower()
    if "vip" in first_message or "premium" in first_message:
        return {"user_tier": "vip"}
    return {"user_tier": "standard"}

def vip_agent_node(state: SupportState):
    """VIP path: fast lane, no escalation"""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    # You can call an LLM here if you want.
	 #  For the assignment it is fine to just set a friendly VIP response.
    return {"messages": [response], "should_escalate": False}

def standard_agent_node(state: SupportState):
     """Standard path: may escalate."""
     messages=state["messages"]
     response = llm_with_tools.invoke(messages)
     return {"messages": [response]}
     
# --- Routing Logic ---
     
def route_by_tier(state: SupportState) -> str:
    """Route based on user tier."""
    if state.get("user_tier") == "vip":
        return "vip_path"
    return "standard_path"

def build_graph():
     workflow = StateGraph(SupportState)
     workflow.add_node("check_tier",check_user_tier_node)
     workflow.add_node("vip_agent",vip_agent_node)
     workflow.add_node("standard_agent",standard_agent_node)
     workflow.add_node("tools", ToolNode(tools))
     
     workflow.set_entry_point("check_tier")
     workflow.add_conditional_edges(
          "check_tier",
          route_by_tier,
          {
               "vip_path": "vip_agent",
               "standard_path":"standard_agent",
          },
     )
     workflow.add_edge("vip_agent", "tools")
     workflow.add_edge("standard_agent", "tools")
     workflow.add_edge("tools", END)
   #   workflow.add_edge("vip_agent", END)
   #   workflow.add_edge("standard_agent", END)
     return workflow.compile()

def main() -> None:
     graph = build_graph()

     vip_result = graph.invoke({
          "messages": [HumanMessage(content="I'm a VIP customer, please check my order")],
          "should_escalate": False,
          "issue_type": "",
          "user_tier": "",
     })

     print("VIP result:", vip_result.get("user_tier"), vip_result.get("should_escalate"))

     standard_result = graph.invoke({
          "messages": [HumanMessage(content="Check my order status")],
          "should_escalate": "True",
          "issue_type": "",
          "user_tier": ""
     })

     print("Standard result:", standard_result.get("user_tier"), standard_result.get("should_escalate"))

if __name__ == "__main__":
	main()
