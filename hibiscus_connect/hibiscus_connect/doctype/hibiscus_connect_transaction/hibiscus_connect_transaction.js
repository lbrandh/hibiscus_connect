// Copyright (c) 2021, itsdave GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hibiscus Connect Transaction', {
	refresh: function(frm) {
		frm.add_custom_button('Zahlung verbuchen', function(){
					frappe.call({ 
						method: 'hibiscus_connect.tools.match_payment', 
						args: {
							hib_trans: frm.doc.name,

						}
						
					})
				})

	}
});
