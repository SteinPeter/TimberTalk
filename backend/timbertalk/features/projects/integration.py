# An dieser Stelle werden ausschließlich öffentliche Services anderer Features benutzt.
# Die Namen für S-03/S-09/S-10 sind vorgegeben; die zusätzliche Bindung ist abzustimmen.
from timbertalk.features.customers import service as customers
from timbertalk.features.drafts import service as drafts


class DependencyUnavailable(RuntimeError):
    pass


def require(module, name):
    function = getattr(module, name, None)
    if not callable(function):
        raise DependencyUnavailable(f"Der gemeinsame Service {name} ist noch nicht verfügbar.")
    return function


def get_customer(session, customer_id):
    return require(customers, "get_customer")(session, customer_id)


def list_customers(session):
    # Vorschlag an F2: Liste mit Objekten, die id und name besitzen.
    return require(customers, "list_customers")(session)


def create_draft(session, name, args, source, original_text):
    return require(drafts, "create_draft")(session, name, args, source, original_text)


def call_tool(session, name, args, source, original_text):
    return require(drafts, "call_tool")(session, name, args, source, original_text)


def readiness():
    required = [
        (customers, "get_customer"),
        (customers, "list_customers"),
        (drafts, "werkzeug"),
        (drafts, "call_tool"),
        (drafts, "create_draft"),
    ]
    missing = [name for module, name in required if not callable(getattr(module, name, None))]
    return {"ready": not missing, "missing": missing}
