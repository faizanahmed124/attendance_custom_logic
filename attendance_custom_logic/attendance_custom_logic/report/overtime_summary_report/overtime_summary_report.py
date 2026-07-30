import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 150
        },
        {
            "label": _("Present Days"),
            "fieldname": "present_days",
            "fieldtype": "Int",
            "width": 110
        },
        {
            "label": _("Total Duty Hours"),
            "fieldname": "total_duty_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        },
        {
            "label": _("Total Overtime Hours"),
            "fieldname": "total_overtime",
            "fieldtype": "Float",
            "precision": 2,
            "width": 170
        },
    ]


def get_data(filters):
    if not filters:
        filters = {}

    from_date  = filters.get("from_date")
    to_date    = filters.get("to_date")
    department = filters.get("department")
    employee   = filters.get("employee")

    if not from_date or not to_date:
        frappe.throw(_("Please set From Date and To Date"))

    # ─────────────────────────────────────────────
    # FIX 1: status filter hata diya —
    #         sirf custom_allow_overtime=1 kafi hai
    # ─────────────────────────────────────────────
    emp_filters = {"custom_allow_overtime": 1}
    if department:
        emp_filters["department"] = department
    if employee:
        emp_filters["name"] = employee

    overtime_employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "designation"]
    )

    if not overtime_employees:
        return []

    emp_names = [e["name"] for e in overtime_employees]

    # ── Attendance aggregation (submitted records only) ──
    attendance_data = frappe.db.sql(
        """
        SELECT
            employee,
            COUNT(*)               AS present_days,
            SUM(custom_duty_hours) AS total_duty_hours,
            SUM(custom_overtime)   AS total_overtime
        FROM
            `tabAttendance`
        WHERE
            employee        IN %(employees)s
            AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
            AND status      IN ('Present', 'Half Day')
            AND docstatus   = 1
        GROUP BY
            employee
        """,
        {
            "employees": emp_names,
            "from_date": from_date,
            "to_date":   to_date,
        },
        as_dict=True
    )

    att_map = {row["employee"]: row for row in attendance_data}

    result = []
    for emp in overtime_employees:
        att = att_map.get(emp["name"], {})

        total_duty     = att.get("total_duty_hours") or 0.0
        total_overtime = att.get("total_overtime")   or 0.0
        present_days   = att.get("present_days")     or 0

        # ─────────────────────────────────────────────
        # FIX 2: zero-skip hata diya —
        #         saray 1883 employees show honge,
        #         chahe date range mein attendance ho ya na ho
        # ─────────────────────────────────────────────
        result.append({
            "employee":         emp["name"],
            "employee_name":    emp["employee_name"],
            "department":       emp["department"],
            "designation":      emp["designation"],
            "present_days":     present_days,
            "total_duty_hours": round(float(total_duty),     2),
            "total_overtime":   round(float(total_overtime), 2),
        })

    result.sort(key=lambda x: x["employee_name"] or "")
    return result