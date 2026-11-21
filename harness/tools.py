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

STATUS_DEF = {
    "Green" : "No Problems at site, all systems operational",
    "Yellow" : "Site is experiencing an inhibiting issue. Operations will be delayed. Help Desk will need to be notified.",
    "Red" : "Site is in critcal condition. All operations have been halted. Immediate Support is required.",
    "White" : "Site was previously in 'Red' Status but is currently under maintenance by our technicians. Will return to 'Green' Status shortly.",
    "Black" : "Site is out of commision and/or permanently closed. No consideration required."
}

SITES = [
    {"id": "US-0001", "address": "123 Seasame Street", "Status": "Green"},
    {"id": "US-0003", "address": "456 Muppet Road", "Status": "Yellow"},
    {"id": "US-0011", "address": "789 Learning Crescent", "Status": "White"},
    {"id": "CA-0001", "address": "111 Maple Avenue", "Status": "Red"},
    {"id": "CA-0007", "address": "222 Moose Boulevard", "Status": "Black"},
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


def search_sites(query: str):
    words = query.lower().split()
    hits = [s for s in SITES
            if any(w in " ".join(str(v) for v in s.values()).lower() for w in words)]
    return hits or {"result": "no matches"}


def lookup_status(color: str):
    for name, meaning in STATUS_DEF.items():
        if name.lower() == color.strip().lower():
            return {"status": name, "meaning": meaning}
    return {"error": f"Unknown status {color}. Valid: {', '.join(STATUS_DEF)}"}


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
    "search_sites": {
        "fn": search_sites,
        "description": "Search sites by any field (site ID like US-0001, address, or status color).",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]},
    },
    "lookup_status": {
        "fn": lookup_status,
        "description": "Explain what a site status color code means (Green, Yellow, Red, White, Black).",
        "parameters": {"type": "object",
                       "properties": {"color": {"type": "string"}},
                       "required": ["color"]},
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
