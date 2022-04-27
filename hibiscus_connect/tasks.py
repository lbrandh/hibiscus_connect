import frappe
from hibiscus_connect.tools import get_transactions_for_account

def fetch_transactions_from_active_accounts():
    accounts = frappe.get_all("Hibiscus Connect Bank Account", filters={
        "fetch_periodically": 1
    })
    if accounts:
        for account in accounts:
            get_transactions_for_account(account["name"])
