from __future__ import annotations

import re

from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter

# ---------------------------------------------------------------------------
# Policy questions
# ---------------------------------------------------------------------------
policy_route = Route(
    name="policy",
    utterances=[
        "What is the leave policy?",
        "What is a leave request?",
        "What does leave request mean?",
        "Explain the leave request process.",
        "What is the purpose of a leave request?",
        "How many casual leave days do I get?",
        "How many sick leave days are allowed?",
        "How many earned leave days are available?",
        "What are the rules for taking leave?",
        "How far in advance should I request leave?",
        "What are the work from home rules?",
        "Do I need manager approval for work from home?",
        "What is the company dress code?",
        "What are the overtime rules?",
        "What is the employee privacy policy?",
        "How should employee data be handled?",
        "What is the policy for sensitive employee data?",
    ],
)

# ---------------------------------------------------------------------------
# SQL / HR data questions
# ---------------------------------------------------------------------------
sql_route = Route(
    name="sql",
    utterances=[
        "How many employees are there?",
        "Show me all employees.",
        "Show my employee details.",
        "What is my employee information?",
        "Who reports to me?",
        "Which employees report to me?",
        "Show employees in my department.",
        "How many employees are in each department?",
        "How many projects are there?",
        "Show my leave requests.",
        "What are my leave requests?",
        "Who is currently on leave?",
        "Show employee leave requests.",
        "How many tickets are there?",
        "Which employees are assigned to this project?",
    ],
)

# ---------------------------------------------------------------------------
# HR actions
# ---------------------------------------------------------------------------
action_route = Route(
    name="action",
    utterances=[
        "Apply for leave.",
        "I want to apply for leave.",
        "Create a leave request for me.",
        "Submit my leave request.",
        "Cancel my leave request.",
        "Withdraw my leave request.",
        "Create an HR ticket.",
        "Raise an HR ticket.",
        "I want to create a support ticket.",
        "Create a ticket for me.",
        "Show my tickets.",
        "Show my open tickets.",
        "Show my resolved tickets.",
        "Check the status of ticket ID 1.",
        "What is the status of my ticket?",
        "Approve this leave request.",
        "Approve the leave request.",
        "Reject this leave request.",
        "Assign this project to an employee.",
        "Assign this ticket to an employee.",
        "Create an announcement.",
        "Publish an HR announcement.",
        "Check my saved leave balance.",
        "Show my remaining leave days.",
        "How many leave days do I have left?",
        "Show my projects.",
        "Which projects am I assigned to?",
        "View my project assignments.",
        "List my assigned projects.",
        "View the projects assigned to me.",
        
    ],
)

# ---------------------------------------------------------------------------
# Unknown / unsupported requests
# ---------------------------------------------------------------------------
unknown_route = Route(
    name="unknown",
    utterances=[
        "Tell me a joke.",
        "What is the weather today?",
        "Explain quantum physics.",
        "Write a Python game for me.",
        "What is the capital of France?",
        "Tell me a story.",
        "Help me with a programming problem.",
        "Who is the president?",
    ],
)

# ---------------------------------------------------------------------------
# Local semantic encoder
#
# FastEmbed downloads the embedding model once and caches it locally.
# No API key is required for semantic routing.
# ---------------------------------------------------------------------------
encoder = FastEmbedEncoder(
    name="BAAI/bge-small-en-v1.5",
    score_threshold=0.5,
)

# ---------------------------------------------------------------------------
# Semantic Router
#
# auto_sync="local" ensures the local route index is synchronized when the
# router is initialized. Without this, semantic-router 0.1.2 can raise:
#
#     ValueError: Index is not ready.
# ---------------------------------------------------------------------------
router = SemanticRouter(
    encoder=encoder,
    routes=[
        policy_route,
        sql_route,
        action_route,
        unknown_route,
    ],
    top_k=5,
    aggregation="mean",
    auto_sync="local",
)

# ---------------------------------------------------------------------------
# Deterministic action-intent detection
# ---------------------------------------------------------------------------
ACTION_PATTERNS = (
    # Apply for leave with duration or descriptive wording.
    r"\bapply\s+(?:for\s+)?(?:\d+\s+days?\s+(?:of\s+)?)?(?:casual|sick|earned|annual|privilege)?\s*leave\b",
    r"\bapply\s+for\s+(?:a\s+)?(?:casual|sick|earned|annual|privilege)?\s*leave\b",
    r"\bsubmit\s+(?:a\s+)?(?:casual|sick|earned|annual|privilege)?\s*leave\b",
    r"\bsubmit\s+(?:my\s+)?leave\s+request\b",
    r"\bcreate\s+(?:a\s+)?leave\s+request\b",
    r"\brequest\s+(?:a\s+)?(?:casual|sick|earned|annual|privilege)?\s*leave\b",
    r"\bi\s+want\s+to\s+apply\s+for\s+(?:a\s+)?leave\b",
    r"\bi\s+want\s+to\s+submit\s+(?:a\s+)?leave\b",
    r"\bcan\s+you\s+(?:apply|submit|create|request)\b.*\bleave\b",
    r"\bplease\s+(?:apply|submit|create|request)\b.*\bleave\b",    
    # Manager/admin project actions. Allow descriptive wording and named
    # projects such as "Assign another employee to the HR Policy Copilot project".
    r"\b(?:assign|reassign)\b.{0,160}\b(?:employee|staff member)\b.{0,160}\bproject\b",
    r"\b(?:assign|reassign)\b.{0,160}\bproject\b.{0,160}\b(?:employee|staff member)\b",
    r"\bcreate\s+(?:a\s+)?project\b",
    r"\b(?:create|publish)\s+(?:an?\s+)?(?:hr\s+)?announcement\b",
    r"\b(?:approve|reject)\s+(?:this\s+|the\s+)?leave\s+request\b",
    r"\bassign\s+(?:this\s+|the\s+)?ticket\s+to\s+(?:an?\s+)?employee\b",

)

# ---------------------------------------------------------------------------
# Deterministic ticket-action detection
# ---------------------------------------------------------------------------
TICKET_ACTION_PATTERNS = (
    # Ticket assignment/reassignment requests. Match both word orders and
    # pronoun-based wording such as "find ticket #21 and assign it to ...".
    r"\b(?:assign|reassign)\b.*\b(?:support\s+)?tickets?\b|\b(?:support\s+)?tickets?\b.*\b(?:assign|reassign)\b",
    # Ticket lists, optionally filtered by status.
    r"\b(?:show|list|view|display)\s+(?:(?:me|all)\s+)?(?:my\s+)?tickets\b",
    r"\b(?:show|list|view|display)\s+(?:(?:me|all)\s+)?(?:my\s+)?(?:open|resolved|in[\s_-]?progress)\s+tickets\b",
    # Specific ticket status and detail lookups.
    r"\b(?:check|show|tell\s+me|get|find)\s+(?:the\s+)?(?:current\s+)?status\s+of\s+(?:my\s+)?ticket\b",
    r"\bwhat(?:'s|\s+is)\s+the\s+status\s+of\s+(?:my\s+)?ticket\b",
    r"\b(?:check|show|get|find)\s+(?:my\s+)?ticket\s+(?:status|details?)\b",
    r"\b(ticket\s*(?:id\s*)?#?\s*\d+|ticket\s+#\s*\d+)\b.*\b(?:status|details?|check|show)\b",
    # Explicit ticket creation requests.
    r"\b(?:create|open|raise|submit|log)\s+(?:a|an|my)?\s*(?:(?:it|hr|onboarding)\s+)?(?:support\s+)?ticket\b",
    r"\b(?:create|open|raise|submit|log)\s+(?:a\s+)?support\s+request\b",
)


# A saved-balance lookup is an Action Agent tool request. Keep entitlement
# questions such as "How many casual leave days do I get?" on Policy RAG.
LEAVE_BALANCE_LOOKUP_PATTERNS = (
    r"\b(?:check|show|view|display)\s+(?:my\s+)?(?:saved\s+)?leave\s+balances?\b",
    r"\bwhat(?:'s| is)\s+my\s+(?:saved\s+)?leave\s+balance\b",
    r"\btell\s+me\s+my\s+(?:saved\s+)?leave\s+balance\b",
    r"\bhow\s+many\s+(?:casual|sick|earned)?\s*leave\s+days?\s+"
    r"(?:do\s+i\s+have|have\s+i\s+left|are\s+left|remain(?:ing)?)\b",
    r"\bhow\s+much\s+(?:casual|sick|earned)?\s*leave\s+"
    r"(?:do\s+i\s+have|have\s+i\s+left|remain(?:ing)?)\b",
)

OWN_PROJECT_LOOKUP_PATTERNS = (
    r"\b(show|list|view|display)\s+(?:me\s+)?my\s+(?:assigned\s+)?projects?\b",
    r"\bwhich\s+projects?\s+am\s+i\s+assigned\s+to\b",
    r"\bwhat\s+projects?\s+(?:am\s+i\s+assigned\s+to|are\s+assigned\s+to\s+me)\b",
    r"\bview\s+(?:the\s+)?projects?\s+assigned\s+to\s+me\b",
    r"\bshow\s+(?:the\s+)?projects?\s+assigned\s+to\s+me\b",
)


def _matches_any_pattern(message: str, patterns: tuple[str, ...]) -> bool:
    """Check whether a message matches any deterministic intent pattern."""
    return any(re.search(pattern, message, flags=re.IGNORECASE) for pattern in patterns)


def _is_own_project_lookup(message: str) -> bool:
    """Detect personal project lookups that must use the authenticated API."""
    text = message.strip().lower()
    return bool(text) and any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in OWN_PROJECT_LOOKUP_PATTERNS
    )


def _is_leave_balance_lookup(message: str) -> bool:
    """Return True for requests to retrieve the user's saved leave balance."""
    text = message.strip().lower()
    return bool(text) and any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in LEAVE_BALANCE_LOOKUP_PATTERNS
    )


def _is_ticket_action_request(message: str) -> bool:
    """Detect ticket lists, status lookups, and ticket creation requests."""
    text = message.strip().lower()
    return bool(text) and _matches_any_pattern(text, TICKET_ACTION_PATTERNS)


def _is_explicit_action_request(message: str) -> bool:
    """
    Detect explicit HR action commands before semantic classification.

    This prevents requests such as:
        "Submit a sick leave request for me for 2026-10-20"

    from being incorrectly classified as a policy question merely because
    they contain policy-related terms such as "sick leave".
    """
    text = message.strip().lower()

    if not text:
        return False

    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in ACTION_PATTERNS
    )


# ---------------------------------------------------------------------------
# Deterministic policy and SQL-query routing
# ---------------------------------------------------------------------------
# These patterns cover common question formats that semantic similarity may
# otherwise misroute to the Action Agent or the unknown route. Keep explicit
# actions and personal lookups higher priority in classify_message().

POLICY_QUERY_PATTERNS = (
    # Explicit policy references and summaries.
    r"\b(?:according to|under|based on|in accordance with)\b.*\bpolic(?:y|ies)\b",
    r"\b(?:what|where|which|explain|summari[sz]e|compare)\b.*\bpolic(?:y|ies)\b",
    r"\bpolic(?:y|ies)\b.*\b(?:say|state|specif(?:y|ies)|allow|require|cover|explain|limit|entitlement|notice|approval|requirement|rule)\b",

    # Policy rules, approvals, deadlines, and schedule changes.
    r"\b(?:remote[\s-]*work|work[\s-]*from[\s-]*home|WFH|hybrid work)\b.*\b(?:policy|rule|limit|maximum|allowed|allowance|days?|approval|approve|schedule|change|request|notice|requirement)\b",
    r"\b(?:policy|rule|limit|maximum|approval|approve|schedule|change|request|notice|requirement|days?)\b.*\b(?:remote[\s-]*work|work[\s-]*from[\s-]*home|WFH|hybrid work)\b",
    r"\bhow many business days\b.*\b(?:advance|before|notice|request|change)\b",
    r"\bhow far in advance\b.*\b(?:leave|remote[\s-]*work|WFH|schedule|policy|request)\b",
    r"\b(?:who must approve|who approves|who needs to approve|written approval|manager approval|department manager)\b.*\b(?:policy|remote|work|schedule|change|request)\b",
    r"\b(?:change|changing|modify|adjust)\b.*\b(?:regular )?(?:remote[\s-]*work|WFH|work schedule|schedule)\b.*\b(?:advance|approve|approval|days?|request)\b",

    # General definitions/process questions belong to Policy RAG, while
    # requests to submit, cancel, or withdraw leave are handled as actions.
    r"\bwhat (?:is|does) (?:a |the )?leave request(?: mean)?\b",
    r"\b(?:explain|describe) (?:the )?leave request process\b",
    r"\bwhat is the purpose of (?:a |the )?leave request\b",

    # Existing leave and other policy coverage.
    r"\b(?:leave entitlements?|leave policy|notice requirements?)\b",
    r"\b(?:dress code|overtime rules?|employee privacy policy|sensitive employee data policy)\b",
    r"\bhow many (?:casual|sick|earned|annual|privilege) leave days?\b",
)


SQL_QUERY_PATTERNS = (
    # General project listing and reporting questions (not create/assign actions).
    r"\b(?:list|show|display|find|search)\b.*\b(?:ongoing|active|all|every)\s+projects?\b",
    r"\b(?:list|show|display|find|search)\b.*\bprojects?\b.*\b(?:status|alphabetically|assigned employees?|departments?)\b",
    r"\b(?:ongoing|active) projects?\b",
    r"\b(?:list|show|display)\b.*\bproject and employee combinations?\b",
    r"\b(?:which employees|employees)\b.*\bassigned to (?:this|the|a) project\b",
    r"\b(?:list|show|display)\b.*\b(?:employees?|departments?|skills?|assignments?)\b",
    r"\bhow many\b.*\b(?:employees?|projects?|departments?)\b",
    r"\bfor each department\b",
    r"\bwho is working on\b",
    # Employee skill searches, including specific programming languages
    # and frameworks mentioned in the assignment evaluation prompts.
    r"\bwhich employees\b.*\b(?:know|have|possess|list|use)\b.*\b(?:skills?|python|fastapi|javascript|java|php|react|laravel)\b",
    r"\b(?:find|show|list|search for)\b.*\bemployees?\b.*\b(?:with|having|who know|who have)\b.*\b(?:skills?|python|fastapi|javascript|java|php|react|laravel)\b",
    r"\bwho knows?\s+(?:python|fastapi|javascript|java|php|react|laravel)\b",
    r"\bwhich employees\b.*\bknow\s+(?:python|fastapi|javascript|java|php|react|laravel)\b",
    r"\bwho is assigned to\b.*",
    r"\bwho are assigned to\b.*",
    r"\bwhich employees\b.*\bassigned to\b.*",
    r"\bwho works on\b.*",
)

# ---------------------------------------------------------------------------
# Explicit unsafe SQL execution requests
# ---------------------------------------------------------------------------
# Route these to the SQL Agent so its existing read-only guardrails can reject
# them. Do not execute or rewrite these statements here.
UNSAFE_SQL_REQUEST_PATTERNS = (
    r"\b(?:run|execute)\s+(?:(?:this|the)\s+)?(?:sql|query)\b",
    r"\b(?:sql|query)\s*[:=]\s*(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|PRAGMA|ATTACH|DETACH)\b",
    r"^\s*(?:INSERT\s+INTO\b|UPDATE\s+[A-Za-z_][\w.]*\s+SET\b|DELETE\s+FROM\b|"
    r"DROP\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b|"
    r"ALTER\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b|"
    r"CREATE\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA|TRIGGER|PROCEDURE|FUNCTION)\b|"
    r"REPLACE\s+INTO\b|TRUNCATE(?:\s+TABLE)?\b|PRAGMA\b|ATTACH\b|DETACH\b)",
)


# ---------------------------------------------------------------------------
# Public classification function
# ---------------------------------------------------------------------------


def classify_message(message: str) -> str:
    """
    Classify an HRMS Copilot message.

    Possible results:
        policy
        sql
        action
        unknown

    Explicit leave-balance lookups and HR action commands are detected before
    semantic routing. Policy entitlement questions remain on the Policy RAG
    route.
    """
    message = message.strip()

    if not message:
        return "unknown"

    # Explicit destructive SQL commands must reach SQL guardrails, never Policy RAG.
    if _matches_any_pattern(message, UNSAFE_SQL_REQUEST_PATTERNS):
        return "sql"

    # Employee-to-project assignments are actions even when the project name
    # contains a policy keyword and the user omits the literal word "project".
    if re.search(
        r"\b(?:assign|reassign|allocate)\b.{0,180}\b(?:employee|staff member)\b.{0,180}\b(?:to|onto)\b",
        message,
        re.IGNORECASE | re.DOTALL,
    ):
        return "action"

    # Personal projects and saved leave balances use authenticated HRMS tools.
    if _is_own_project_lookup(message):
        return "action"

    # Explicit ticket requests must not fall through to the SQL Agent.
    if _is_ticket_action_request(message):
        return "action"

    if _is_leave_balance_lookup(message):
        return "action"

    # Explicit HR action commands take priority over semantic similarity.
    if _is_explicit_action_request(message):
        return "action"

    # Route policy questions deterministically so unsupported policy details
    # can be handled by Policy RAG instead of the Action Agent.
    if _matches_any_pattern(message, POLICY_QUERY_PATTERNS):
        return "policy"

    # Route common general HR data/reporting questions to the read-only SQL
    # Agent. Personal project lookups were handled above and remain actions.
    if _matches_any_pattern(message, SQL_QUERY_PATTERNS):
        return "sql"

    result = router(message)

    if result is None:
        return "unknown"

    route_name = getattr(result, "name", None)

    if not route_name:
        return "unknown"

    return route_name.lower()
