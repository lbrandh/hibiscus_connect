# Copyright (c) 2021, itsdave GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import xmlrpc.client as xc
import ssl
from hibiscus_connect.hibclient import Hibiscus


class HibiscusConnectSettings(Document):
	@frappe.whitelist()
	def test_connection(self):
		hibiscus = Hibiscus(self.server, self.port, self.get_password("hibiscus_master_password"), self.ignore_cert)
		konto_list = hibiscus.get_accounts()
		frappe.msgprint(str(konto_list))
		
