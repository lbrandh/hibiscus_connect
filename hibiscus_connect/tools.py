from cmath import sin
from pydoc import doc
import frappe
from hibiscus_connect.hibclient import Hibiscus
import json
from pprint import pprint
from datetime import datetime as dt
from datetime import date, timedelta
from frappe.model.naming import set_name_by_naming_series, get_default_naming_series
import re

@frappe.whitelist()

def get_accounts_from_hibiscus_server():
    #Liefert ungefiltert alle Konten mit sämmtlichen Paramatern zurück
    settings = frappe.get_single("Hibiscus Connect Settings")
    hib = Hibiscus(settings.server, settings.port, settings.master_password, settings.ignore_cert)
    return hib.get_accounts()

@frappe.whitelist()

def get_accounts_from_hibiscus_server_for_dialog():
    #Liefert alle Konten zurück, formatiert für die Anzeige des Dialogs "Konten anlegen"
    accounts = get_accounts_from_hibiscus_server()
    fields = []
    for account in accounts:

        account_dict = {
            "label": str(account["bezeichnung"] + ", " + account["name"] + ", IBAN:" + account["iban"]),
            "fieldname": str(account["iban"]),
            "fieldtype": "Check"
        }
        fields.append(account_dict)
    return fields


@frappe.whitelist()

def create_accounts(dialog_accounts):
    hibiscus_accounts = get_accounts_from_hibiscus_server()
    dialog_accounts_dict = json.loads(dialog_accounts)
    for key in dialog_accounts_dict:
        if dialog_accounts_dict[key] == 1:
            iban_account_to_create = key
            for hib_acc in hibiscus_accounts:
                if hib_acc["iban"] == iban_account_to_create:
                    create_hibiscus_connect_bank_account(hib_acc)

def create_hibiscus_connect_bank_account(hib_acc):
    hib_acc["doctype"] = "Hibiscus Connect Bank Account"
    hib_acc["name1"] = hib_acc.pop("name")
    hib_acc["saldo_available"] = float(str(hib_acc["saldo_available"]).replace(".","").replace(",","."))
    hib_acc["saldo"] = float(str(hib_acc["saldo"]).replace(".","").replace(",","."))
    hib_acc_doc = frappe.get_doc(hib_acc)
    hib_acc_doc.save()

@frappe.whitelist()

def get_transactions_for_account(id, von = str(date.today()-timedelta(30)), bis = str(date.today())):
    settings = frappe.get_single("Hibiscus Connect Settings")
    hib = Hibiscus(settings.server, settings.port, settings.master_password, settings.ignore_cert)
    
    
    
    von_dt = dt.strptime (von,"%Y-%m-%d")
    bis_dt = dt.strptime (bis,"%Y-%m-%d")
        
   
    transactions = hib.get_transactions(id, von_dt,bis_dt)
    check_trans_id = frappe.get_all("Hibiscus Connect Transaction", fields = "id")
    check_trans_id_list = [ x["id"] for x in check_trans_id]
    
    for hib_trans in transactions:
        if hib_trans["id"] not in check_trans_id_list: 
            create_hibiscus_connect_transaction(hib_trans)
        
    pprint(transactions[len(transactions)-1])
    pprint(transactions[len(transactions)-2])
    pprint(transactions[len(transactions)-3])
    pprint(transactions[len(transactions)-16])
    print(von)
    print(bis)
 


def create_hibiscus_connect_transaction(hib_trans):
    
    hib_trans["doctype"] = "Hibiscus Connect Transaction"
    hib_trans["saldo"] = float(str(hib_trans["saldo"]))
    hib_trans["betrag"] = float(str(hib_trans["betrag"]).replace(".","").replace(",","."))
    hib_trans["zweck_raw"] = hib_trans["zweck"]
    hib_trans_doc = frappe.get_doc(hib_trans)
    hib_trans_doc.save()

@frappe.whitelist()
def match_payment(hib_trans):
    hib_trans_doc = frappe.get_doc("Hibiscus Connect Transaction", hib_trans)
    matching_list = {} 
    #Kriterien, die zum verbuchen herangezogen werden:
    #1.) Zweck enthällt eine Rechnungsnummer im vollständigen format
    matching_list["sinvs"] = _get_sinv_names(hib_trans_doc.zweck)
    if matching_list["sinvs"]:
        print(matching_list["sinvs"])
        print(_get_outstanding_amounts(matching_list["sinvs"]))
        print(_get_grand_totals(matching_list["sinvs"]))
        
def _get_sinv_names(zweck):
    naming_series = get_default_naming_series("Sales Invoice")
    if "#" not in naming_series:
        naming_series += "######"
    regex_naming_series = str(naming_series).replace(".","").replace("#","\d")
    match_regex_naming_series =re.findall(regex_naming_series, zweck)
    sinv_name_list = []
    if match_regex_naming_series:
        for m in match_regex_naming_series:
            sinv_name_list.append(m)
    return sinv_name_list

def _get_outstanding_amounts(sinv_list):
    outstanding_amount_sum = 0.0
    for sinv in sinv_list:
        sinv_doc = frappe.get_doc("Sales Invoice", sinv)
        outstanding_amount_sum += sinv_doc.outstanding_amount
    return outstanding_amount_sum

def _get_grand_totals(sinv_list):
    grand_total_sum = 0.0
    for sinv in sinv_list:
        sinv_doc = frappe.get_doc("Sales Invoice", sinv)
        grand_total_sum += sinv_doc.grand_total
    return grand_total_sum

def make_payment_entry():
    pe_doc = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",

    })



