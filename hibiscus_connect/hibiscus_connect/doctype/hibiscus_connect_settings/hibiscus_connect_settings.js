// Copyright (c) 2021, itsdave GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hibiscus Connect Settings', {
	refresh: function(frm) {

		frm.add_custom_button('Konten anlegen', function(){
			frappe.call({ 
				method: 'hibiscus_connect.tools.get_accounts_from_hibiscus_server_for_dialog', 
				callback:function(r){
					let konten_anlegen = new frappe.ui.Dialog({
						title: 'anzulegende Konten auswählen:',
						fields: r.message,
						primary_action_label: 'Submit',
						primary_action(values) {
							frappe.call({ 
								method: 'hibiscus_connect.tools.create_accounts', 
								args: { dialog_accounts: values },
								callback:function(r){
									konten_anlegen.hide();
								}
							})
						}
					});
					konten_anlegen.show();
				}
			})
		});
	}
});
