"""Tools the agent can call, backed by synthetic data only.

Never put real client data in here. Every record below is made up.
Add a tool by writing a function, then registering it in TOOLS.
"""

import json

ORDERS = {
    "A-1001": {"customer": "Maple Grocers", "total": 84.50, "status": "delivered",
               "items": ["receipt printer paper x10"], "payment": "debit"},
    "A-1002": {"customer": "Harbour Cafe", "total": 1299.00, "status": "delivered",
               "items": ["POS terminal"], "payment": "credit"},
    "A-1003": {"customer": "Northside Books", "total": 42.00, "status": "cancelled",
               "items": ["barcode scanner cable"], "payment": "credit"},
}

KB = [
    {"id": "KB-12", "title": "Card reader shows 'Host unavailable'",
     "body": "The payment processor did not respond. Check the processor status page "
             "before escalating. This is a third-party/integration fault, not a POS defect."},
    {"id": "KB-31", "title": "Receipts print blank",
     "body": "Thermal paper loaded upside down. Flip the roll. Operator error."},
    {"id": "KB-47", "title": "Totals off by one cent on split tenders",
     "body": "Known rounding defect in v4.2 split-tender logic. Fixed in v4.3."},
]


def lookup_order(order_id: str):
    order = ORDERS.get(order_id)
    return order if order else {"error": f"No order {order_id}"}


def calculate_refund(amount: float, percent: float):
    if not 0 <= percent <= 100:
        return {"error": "percent must be between 0 and 100"}
    return {"refund": round(amount * percent / 100, 2)}


def search_kb(query: str):
    words = query.lower().split()
    hits = [a for a in KB if any(w in (a["title"] + a["body"]).lower() for w in words)]
    return hits[:3] or {"result": "no matches"}


TOOLS = {
    "lookup_order": {
        "fn": lookup_order,
        "description": "Look up an order by its ID (format A-0000).",
        "parameters": {"type": "object",
                       "properties": {"order_id": {"type": "string"}},
                       "required": ["order_id"]},
    },
    "calculate_refund": {
        "fn": calculate_refund,
        "description": "Calculate a refund as a percentage of an amount.",
        "parameters": {"type": "object",
                       "properties": {"amount": {"type": "number"},
                                      "percent": {"type": "number"}},
                       "required": ["amount", "percent"]},
    },
    "search_kb": {
        "fn": search_kb,
        "description": "Search the support knowledge base.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]},
    },
}


def specs(names):
    """Tool definitions for the model, limited to the tools a task allows."""
    return [{"name": n, "description": TOOLS[n]["description"],
             "parameters": TOOLS[n]["parameters"]} for n in names]


def call(name, args):
    if name not in TOOLS:
        return json.dumps({"error": f"Unknown tool {name}"})
    try:
        return json.dumps(TOOLS[name]["fn"](**args))
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments: {e}"})
