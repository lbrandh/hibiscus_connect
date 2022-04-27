from cmath import sin
from pydoc import doc
from bs4 import Doctype
import frappe
from hibiscus_connect.hibclient import Hibiscus
import json
from pprint import pprint
from datetime import datetime as dt
from datetime import date, timedelta
from frappe.model.naming import set_name_by_naming_series, get_default_naming_series
import re
from pprint import pprint
from numpy import append

from razorpay import Payment

@frappe.whitelist()

def get_accounts_from_hibiscus_server():
    #Liefert ungefiltert alle Konten mit sämmtlichen Paramatern zurück
    settings = frappe.get_single("Hibiscus Connect Settings")
    hib = Hibiscus(settings.server, settings.port, settings.get_password("hibiscus_master_password") , settings.ignore_cert)
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

def get_transactions_for_account(account, von = str(date.today()-timedelta(30)), bis = str(date.today())):
    settings = frappe.get_single("Hibiscus Connect Settings")
    hib = Hibiscus(settings.server, settings.port, settings.get_password("hibiscus_master_password"), settings.ignore_cert)

    account_doc = frappe.get_doc("Hibiscus Connect Bank Account", account)
    if not account_doc.erpnext_bankkonto:
        frappe.throw("Bitte Hibiscus Connect Bank Account mit ERPNext Bankkonto verknüpfen.")
    
    von_dt = dt.strptime (von,"%Y-%m-%d")
    bis_dt = dt.strptime (bis,"%Y-%m-%d")
        
    transactions = hib.get_transactions(account_doc.id, von_dt,bis_dt)
    check_trans_id = frappe.get_all("Hibiscus Connect Transaction", fields = "id")
    check_trans_id_list = [ x["id"] for x in check_trans_id]
    
    for hib_trans in transactions:
        if hib_trans["id"] not in check_trans_id_list: 
            create_hibiscus_connect_transaction(hib_trans, account)


def create_hibiscus_connect_transaction(hib_trans, account):
    
    hib_trans["doctype"] = "Hibiscus Connect Transaction"
    hib_trans["saldo"] = float(str(hib_trans["saldo"]))
    hib_trans["betrag"] = float(str(hib_trans["betrag"]).replace(".","").replace(",","."))
    hib_trans["zweck_raw"] = hib_trans["zweck"]
    hib_trans_doc = frappe.get_doc(hib_trans)
    hib_trans_doc.konto = account
    hib_trans_doc.save()

@frappe.whitelist()
def match_hibiscus_transaction(hib_trans):
    result = match_payment(hib_trans)
    if result["sinvs_matched_strict"]:
        make_payment_entry(result)
        return "Erfolgreich verbucht strict"
    if result["sinvs_matched_loose"]:
        make_payment_entry(result)
        return "Erfolgreich verbucht loose"
    frappe.throw("Zahlung konnte nicht automatisiert verbucht werden.")
    

def match_payment(hib_trans, sinvs=None):
    hib_trans_doc = frappe.get_doc("Hibiscus Connect Transaction", hib_trans)
    matching_list = {
        "sinvs_matched_strict": False,
        "sinvs_matched_loose": False,
        "totals_matched": False,
        "betrag": hib_trans_doc.betrag,
        "zweck": hib_trans_doc.zweck,
        "account": hib_trans_doc.konto,
        "erpnext_bankkonto": frappe.get_doc("Hibiscus Connect Bank Account", hib_trans_doc.konto),
        "hib_trans_doc": hib_trans_doc,
        "sinvs": [],
        "sinvs_loose": []
        }
    if not sinvs:
        sinvs = _get_unpaid_sinv_numbers()
    #Kriterien, die zum verbuchen herangezogen werden:
    #1.) Zweck enthällt mindesten eine Rechnungsnummer im vollständigen format
    matching_list["sinvs"] = _get_sinv_names(hib_trans_doc.zweck, sinvs)
    if matching_list["sinvs"]:
        matching_list["totals"] = _get_grand_totals(matching_list["sinvs"])
        #1.1) Wenn zusätzlich der Betrag übereinstimmt, können wir verbuchen
        if hib_trans_doc.betrag == matching_list["totals"]:
            matching_list["sinvs_matched_strict"] = True
            matching_list["totals_matched"] = True
            return matching_list
    matching_list["sinvs_loose"] = _advanced_si_match(hib_trans_doc.zweck, sinvs)
    if matching_list["sinvs_loose"]:
        matching_list["totals"] = _get_grand_totals(matching_list["sinvs_loose"])
        if hib_trans_doc.betrag == matching_list["totals"]:
            matching_list["sinvs_matched_loose"] = True
            matching_list["totals_matched"] = True
            return matching_list
    return matching_list

    
    

def match_all_payments(von = str(date.today()-timedelta(30)), bis = str(date.today())):
    stats = {
        "sinvs_matched_strict": 0,
        "sinvs_matched_loose": 0,
        "totals_matched": 0,
        "payments_processed": 0
        }
    payments = frappe.get_all("Hibiscus Connect Transaction", filters={
        "status": "neu",
        "betrag": [">", 0]
    })

    unpaid_sinvs = _get_unpaid_sinv_numbers()
    payments_list = []

    for p in payments:
        payments_list.append(p)
        result = match_payment(p.name, sinvs=unpaid_sinvs)
        
        stats["payments_processed"] += 1
        if result["sinvs_matched_strict"]:
            stats["sinvs_matched_strict"] += 1
            make_payment_entry(result)
        if result["sinvs_matched_loose"]:
            stats["sinvs_matched_loose"] += 1
            make_payment_entry(result)
        if result["totals_matched"]:
            stats["totals_matched"] += 1
        else:
            debug_data(result)
    
    pprint(stats)

def debug_data(result):
    print("--------------------")
    print(result["zweck"])
    print(result["betrag"])
   

def _advanced_si_match(zweck, sinvs):
    si_list = []
    regex = "|".join(sinvs)
    zweck = zweck.replace(" ","")
    match_regex_naming_series =re.findall(regex, zweck)
    if match_regex_naming_series:
        for m in match_regex_naming_series:
            sinv_name = "SINV-" + str(m)
            if sinv_name not in si_list:
                si_list.append(sinv_name)
    return si_list

def _get_unpaid_sinv_numbers():
    sinv_numbers = []
    sinvs = frappe.get_all("Sales Invoice", filters={
        "status": ["not in", ["Paid", "Return", "Partly Paid"]]
        })
    sinvs = frappe.get_all("Sales Invoice", filters={
        "status": ["not in", ["Return"]],
        "name": ["not like", "SINV-RET-%"]
        })
    for si in sinvs:
        sinv_numbers.append(str(si["name"]).split("-")[1])
    return sinv_numbers

        
def _get_sinv_names(zweck, sinvs=None, extended_matching=True):
    naming_series = get_default_naming_series("Sales Invoice")
    if "#" not in naming_series:
        naming_series += "######"
    regex_naming_series = str(naming_series).replace(".","").replace("#","\\d")
    match_regex_naming_series =re.findall(regex_naming_series, zweck)
    sinv_name_list = []
    if match_regex_naming_series:
        for m in match_regex_naming_series:
            if m not in sinv_name_list:
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
    return round(grand_total_sum,2)

def make_payment_entry(matching_list, settings=None):
    print(matching_list)
    if not settings:
        settings = frappe.get_single("Hibiscus Connect Settings")

    pe_doc = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": "", #erstmal leer, wird später anhand vorliegender Rechnungen befüllt
        "party_name": "",
        "paid_from": "",
        "paid_to":  matching_list["erpnext_bankkonto"].erpnext_bankkonto,
        "paid_amount": matching_list["betrag"],
        "received_amount": matching_list["betrag"],
        "source_exchange_rate": 1,
        "target_exchange_rate": 1,
        "reference_no": matching_list["hib_trans_doc"].name,
        "reference_date": matching_list["hib_trans_doc"].datum,
        "hibiscus_connect_transaction": matching_list["hib_trans_doc"].name,
        "referneces": []
    })

    todo = list(matching_list["sinvs"])
    todo.extend(x for x in matching_list["sinvs_loose"] if x not in todo)

    for sinv in todo:
        reference_doc_response = _get_payment_entry_reference(sinv)
       
        #Kundennummer setzen wenn bisher leer
        if pe_doc.party == "":
            pe_doc.party = reference_doc_response["sinv_doc"].customer
            pe_doc.party_name = frappe.get_value(doctype="Customer", filters={"name": pe_doc.party}, fieldname="customer_name"),
        #Fehler, wenn eine bereits befüllte Kundenummer verändert werden soll
        if pe_doc.party != reference_doc_response["sinv_doc"].customer:
            frappe.throw("Verschiedene Kundenummern in automatisiert zugeordneten Rechnungen.")

        #Debitoren Konte anhand Rechnungskonto setzen
        if pe_doc.paid_from == "":
            pe_doc.paid_from = reference_doc_response["sinv_doc"].debit_to
        #Fehler, wenn mehrere Debitoren Konten in einem PE angesprochen werden würden
        if pe_doc.paid_from != reference_doc_response["sinv_doc"].debit_to:
            frappe.throw("Verschiedene debitoren Konten in einem Payment Entry. Das wird nicht unterstützt. Zahlung muss manuell in mehreren Payment Entries verbucht werden.")


        pe_doc.append("references", reference_doc_response["reference_doc"])
    
    pe_doc.save()
    
    if settings.submit_pe:
        pe_doc.submit()
        matching_list["hib_trans_doc"].status = "automatisch verbucht"
        matching_list["hib_trans_doc"].save()


def _get_payment_entry_reference(sinv):
    sinv_doc = frappe.get_doc("Sales Invoice", sinv)
    reference_doc = frappe.get_doc({ 
        "doctype": "Payment Entry Reference",
        "reference_doctype": "Sales Invoice",
        "reference_name": sinv,
        "due_date": sinv_doc.due_date,
        "total_amount": sinv_doc.grand_total,
        "outstanding_amount": sinv_doc.outstanding_amount,
        "allocated_amount": sinv_doc.outstanding_amount
    })
    return {"reference_doc": reference_doc, "sinv_doc": sinv_doc}



###### einmal-methoden für inbetreibnahme

def set_lagacy_verbucht():
    hib_transactions = frappe.get_all("Hibiscus Connect Transaction", filters={
        "status": "neu"
    })
    for ht in hib_transactions:
        ht_doc= frappe.get_doc("Hibiscus Connect Transaction", ht["name"])
        regex = "PE-\\d\\d\\d\\d\\d"
        result = re.findall(regex, ht_doc.kommentar)
        
        if result:
            print(ht_doc.kommentar)
            ht_doc.status = "legacy verbucht"
            ht_doc.save()
    frappe.db.commit()