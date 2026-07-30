frappe.query_reports["Overtime Summary Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            // Sirf overtime-allowed employees dikhao dropdown mein
            get_query: function () {
                return {
                    filters: {
                        custom_allow_overtime: 1,
                        status: "Active"
                    }
                };
            }
        }
    ]
};