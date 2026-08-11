from langgraph.graph import END, StateGraph

from agent.processors.clean_text import clean_text
from agent.processors.hyde_rewrite import hyde_rewrite
from agent.processors.standardize_query import standardize_query
from agent.processors.structure_ingest import structure_ingest
from agent.state import AgentState


def build_preprocess_graph():
    graph = StateGraph(AgentState)

    graph.add_node("clean_text", clean_text)
    graph.add_node("standardize_query", standardize_query)

    graph.set_entry_point("clean_text")
    graph.add_edge("clean_text", "standardize_query")
    graph.add_edge("standardize_query", END)

    return graph.compile()


def build_ingest_graph():
    graph = StateGraph(AgentState)

    graph.add_node("clean_text", clean_text)
    graph.add_node("structure_ingest", structure_ingest)
    graph.add_node("hyde_rewrite", hyde_rewrite)

    graph.set_entry_point("clean_text")
    graph.add_edge("clean_text", "structure_ingest")
    graph.add_edge("structure_ingest", "hyde_rewrite")
    graph.add_edge("hyde_rewrite", END)

    return graph.compile()


preprocess_agent = build_preprocess_graph()
ingest_agent = build_ingest_graph()
