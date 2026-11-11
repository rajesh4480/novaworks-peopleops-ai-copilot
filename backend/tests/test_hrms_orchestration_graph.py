from app.services.ai.orchestration_graph import (
    route_to_agent,
    _normalize_intent,
)


def test_policy_intent_routes_to_policy_agent():
    assert route_to_agent({"intent": "policy"}) == "policy"


def test_sql_intent_routes_to_sql_agent():
    assert route_to_agent({"intent": "sql"}) == "sql"


def test_action_intent_routes_to_action_agent():
    assert route_to_agent({"intent": "action"}) == "action"


def test_unknown_intent_routes_to_unknown_node():
    assert route_to_agent({"intent": "unknown"}) == "unknown"


def test_policy_rag_alias_is_normalized():
    assert _normalize_intent("policy_rag") == "policy"


def test_sql_agent_alias_is_normalized():
    assert _normalize_intent("sql_agent") == "sql"


def test_action_agent_alias_is_normalized():
    assert _normalize_intent("action_agent") == "action"


def test_unrecognized_intent_routes_to_unknown_node():
    assert route_to_agent({"intent": "something_else"}) == "unknown"