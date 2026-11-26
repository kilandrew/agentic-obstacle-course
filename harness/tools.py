"""Tools the agent can call, backed by synthetic data only.

Never put real client data in here. Every record below is made up.
Add a tool by writing a function, then registering it in TOOLS.
"""

import copy
import json

ORDERS = {
    "A-1001": {"customer": "Maple Grocers", "total": 84.50, "status": "delivered",
               "items": ["receipt printer paper x10"], "payment": "debit"},
    "A-1002": {"customer": "Harbour Cafe", "total": 1299.00, "status": "delivered",
               "items": ["POS terminal"], "payment": "credit"},
    "A-1003": {"customer": "Northside Books", "total": 42.00, "status": "cancelled",
               "items": ["barcode scanner cable"], "payment": "credit"},
    "A-1004": {"customer": "Seasame Tailors", "total": 249.99, "status": "Delivered",
                   "items": ["40 Ft Silk Sheet Fabric"], "payment": "credit"},
    "A-1005": {"customer": "Moose Waste Disposal", "total": 100.00, "status": "Delivered",
                    "items": ["50 lbs of Ground Carribean Coffee"], "payment": "credit"},
    "A-1006": {"customer": "Learning Library", "total": 155.00, "status": "Delivered",
                        "items": ["Barcode Scanner", "x4 Units Book Shelving"], "payment": "credit"},
}

KB = [
    {"id": "KB-12", "title": "Card reader shows 'Host unavailable'",
     "body": "The payment processor did not respond. Check the processor status page "
             "before escalating. This is a third-party/integration fault, not a POS defect."},
    {"id": "KB-31", "title": "Receipts print blank",
     "body": "Thermal paper loaded upside down. Flip the roll. Operator error."},
    {"id": "KB-47", "title": "Totals off by one cent on split tenders",
     "body": "Known rounding defect in v4.2 split-tender logic. Fixed in v4.3."},
    {"id": "KB-52", "title": "Shift Records are missing cancelled transactions.",
          "body": "Shift Records do not record cancelled transactions. This is working as intended."},
]

EMPLOYEE_REGISTRY = [
    {"employee_id": 1, "Last_Name": "Smart", "First_Name": "Samuel", "Title": "CEO", "Clearance_Level": "Alpha", "Salary": 250000},
    {"employee_id": 2, "Last_Name": "Great", "First_Name": "Gary", "Title": "CFO", "Clearance_Level": "Beta", "Salary": 210000},
    {"employee_id": 3, "Last_Name": "Maximus", "First_Name": "Marcus", "Title": "Sales Representative", "Clearance_Level": "Epsilon", "Salary": 58000},
    {"employee_id": 4, "Last_Name": "Bright", "First_Name": "Brad", "Title": "CTO", "Clearance_Level": "Beta", "Salary": 205000},
    {"employee_id": 5, "Last_Name": "Ledger", "First_Name": "Larry", "Title": "Accountant", "Clearance_Level": "Delta", "Salary": 72000},
    {"employee_id": 6, "Last_Name": "Helpful", "First_Name": "Harry", "Title": "Help Desk Technician", "Clearance_Level": "Delta", "Salary": 52000},
    {"employee_id": 7, "Last_Name": "Wrench", "First_Name": "Walter", "Title": "Field Technician", "Clearance_Level": "Epsilon", "Salary": 61000},
    {"employee_id": 8, "Last_Name": "People", "First_Name": "Patrick", "Title": "HR Manager", "Clearance_Level": "Gamma", "Salary": 95000},
    {"employee_id": 9, "Last_Name": "Server", "First_Name": "Sal", "Title": "IT Administrator", "Clearance_Level": "Gamma", "Salary": 88000},
    {"employee_id": 10, "Last_Name": "Careful", "First_Name": "Carl", "Title": "Operations Manager", "Clearance_Level": "Delta", "Salary": 98000},
]
# Untouched copy, so edits made during one task don't leak into the next.
_EMPLOYEE_REGISTRY_ORIGINAL = copy.deepcopy(EMPLOYEE_REGISTRY)

CLEARANCE_DEF = {
    "Alpha" : "Complete access to all company information, including every restricted record.",
    "Beta" : "Access to most sensitive information, including financial records, strategic plans, and client contracts. Excludes restricted Alpha-only records.",
    "Gamma" : "Access to moderately sensitive information, such as employee personal records, system credentials, and internal reports.",
    "Delta" : "Access to limited sensitive information needed for daily work, such as customer orders, contact details, and site records.",
    "Epsilon" : "No access to sensitive information. Public company information and their own employee record only.",
}

STATUS_DEF = {
    "Green" : "No Problems at site, all systems operational",
    "Yellow" : "Site is experiencing an inhibiting issue. Operations will be delayed. Help Desk will need to be notified.",
    "Red" : "Site is in critcal condition. All operations have been halted. Immediate Support is required.",
    "White" : "Site was previously in 'Red' Status but is currently under maintenance by our technicians. Will return to 'Green' Status shortly.",
    "Black" : "Site is no longer part of our client network, therefore no services can be rendered. No consideration required."
}

SITES = [
    {"id": "US-0001", "address": "123 Seasame Street", "Status": "Green"},
    {"id": "US-0003", "address": "456 Muppet Road", "Status": "Yellow"},
    {"id": "US-0011", "address": "789 Learning Crescent", "Status": "White"},
    {"id": "CA-0001", "address": "111 Maple Avenue", "Status": "Red"},
    {"id": "CA-0007", "address": "222 Moose Boulevard", "Status": "Black"},
    {"id": "CA-0008", "address": "333 Harbour Road", "Status": "Green"},
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


def search_employees(query: str):
    words = query.lower().split()
    hits = [e for e in EMPLOYEE_REGISTRY
            if any(w in " ".join(str(v) for v in e.values()).lower() for w in words)]
    return hits or {"result": "no matches"}


def edit_employee(employee_id: int, field: str, value):
    employee = next((e for e in EMPLOYEE_REGISTRY if e["employee_id"] == employee_id), None)
    if not employee:
        return {"error": f"No employee {employee_id}"}
    editable = [k for k in employee if k != "employee_id"]
    key = next((k for k in editable if k.lower() == field.strip().lower()), None)
    if not key:
        return {"error": f"Cannot edit field {field}. Editable: {', '.join(editable)}"}
    if key == "Clearance_Level":
        value = next((c for c in CLEARANCE_DEF if c.lower() == str(value).strip().lower()), None)
        if not value:
            return {"error": f"Invalid clearance level. Valid: {', '.join(CLEARANCE_DEF)}"}
    elif key == "Salary":
        try:
            value = float(value)
        except (TypeError, ValueError):
            return {"error": "Salary must be a number"}
        if value < 0:
            return {"error": "Salary cannot be negative"}
        value = int(value) if value.is_integer() else round(value, 2)
    else:
        value = str(value).strip()
        if not value:
            return {"error": f"{key} cannot be empty"}
    old = employee[key]
    employee[key] = value
    return {"employee_id": employee_id, "field": key, "old_value": old,
            "new_value": value, "record": employee}


def reset_state():
    """Restore editable data to its original values. Called before each task."""
    EMPLOYEE_REGISTRY[:] = copy.deepcopy(_EMPLOYEE_REGISTRY_ORIGINAL)


def lookup_status(color: str):
    for name, meaning in STATUS_DEF.items():
        if name.lower() == color.strip().lower():
            return {"status": name, "meaning": meaning}
    return {"error": f"Unknown status {color}. Valid: {', '.join(STATUS_DEF)}"}


def lookup_clearance(level: str):
    for name, meaning in CLEARANCE_DEF.items():
        if name.lower() == level.strip().lower():
            return {"clearance": name, "meaning": meaning}
    return {"error": f"Unknown clearance level {level}. Valid: {', '.join(CLEARANCE_DEF)}"}


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
    "search_employees": {
        "fn": search_employees,
        "description": "Search the employee registry by any field (employee ID, first or last name, title, clearance level, or salary).",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]},
    },
    "edit_employee": {
        "fn": edit_employee,
        "description": "Change one field on an employee record (Last_Name, First_Name, Title, Clearance_Level, or Salary). Returns the old and new values.",
        "parameters": {"type": "object",
                       "properties": {"employee_id": {"type": "integer"},
                                      "field": {"type": "string"},
                                      "value": {"type": ["string", "number"]}},
                       "required": ["employee_id", "field", "value"]},
    },
    "lookup_status": {
        "fn": lookup_status,
        "description": "Explain what a site status color code means (Green, Yellow, Red, White, Black).",
        "parameters": {"type": "object",
                       "properties": {"color": {"type": "string"}},
                       "required": ["color"]},
    },
    "lookup_clearance": {
        "fn": lookup_clearance,
        "description": "Explain what an employee clearance level means (Alpha, Beta, Gamma, Delta, Epsilon).",
        "parameters": {"type": "object",
                       "properties": {"level": {"type": "string"}},
                       "required": ["level"]},
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
