import xmlrpc.client as xc
import ssl
from datetime import datetime, timedelta

  
class Hibiscus():

    def __init__(self, server, port, master_password, ignore_cert = 0):
        if ignore_cert == 1:
            self.client = xc.Server("https://admin:" + master_password + "@" + server + ":" + port + "/xmlrpc", context=ssl._create_unverified_context())
        else:
            self.client = xc.Server("https://admin:" + master_password + "@" + server + ":" + port + "/xmlrpc")
    
    def get_accounts(self):
        accounts = self.client.hibiscus.xmlrpc.konto.find()
        return accounts

    def get_transactions(self, id, datum_min=False, datum_max=False):
        params = {
            "konto_id": id
            }
        if datum_min:
            params["datum:min"] = datum_min.strftime("%d.%m.%Y")
        if datum_max:
            params["datum:max"] = datum_max.strftime("%d.%m.%Y")
        #Falls kein Datumsbereich ausgewählt wurde, laden wir die letzten 30 Tage
        if not datum_min and not datum_max:
            datum_min = datetime.now() - timedelta(days=30)
            params["datum:min"] = datum_min.strftime("%d.%m.%Y")
        transactions = self.client.hibiscus.xmlrpc.umsatz.list(params)
        return transactions



            

