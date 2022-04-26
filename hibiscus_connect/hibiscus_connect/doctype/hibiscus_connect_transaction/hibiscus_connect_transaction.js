// Copyright (c) 2021, itsdave GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hibiscus Connect Transaction', {
	refresh: function(frm) {
		frm.add_custom_button('Zahlung verbuchen', function(){
					frappe.call({ 
						method: 'hibiscus_connect.tools.match_hibiscus_transaction', 
						args: {
							hib_trans: frm.doc.name,
						},
						callback:function(r){
							frappe.msgprint({
								title: __('Notification'),
								indicator: 'green',
								message: __(r.message)
							});
							frappe.set_route('List', 'Hibiscus Connect Transaction', {
								'status': 'neu',
								'betrag': ['>', 0]});
						}
					})
				})
	}
});
