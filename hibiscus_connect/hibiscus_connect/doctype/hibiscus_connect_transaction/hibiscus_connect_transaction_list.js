frappe.listview_settings['Hibiscus Connect Transaction'] = {
	hide_name_column: true,
    add_fields: ["status", "name"],
    	
	get_indicator: function (doc) {
		if (doc.status === "neu") {
			return [__("neu"), "orange", "status,=,neu"];
		} else if (doc.status === "automatisch verbucht") {
			return [__("automatisch verbucht"), "green", "status,=,automatisch verbucht"];
        } else if (doc.status === "manuell verbucht") {
			return [__("manuell verbucht"), "green", "status,=,manuell verbucht"];
        }
    }

}