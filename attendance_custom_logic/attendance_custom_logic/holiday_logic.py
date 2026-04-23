import frappe
from frappe.utils import getdate, add_days, now_datetime


def mark_holiday_attendance():

    # 🔹 Always check PREVIOUS DATE
    attendance_date = add_days(getdate(), -1)

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "holiday_list"]
    )

    for emp in employees:

        if not emp.holiday_list:
            continue

        # 🔹 Check holiday in employee holiday list
        is_holiday = frappe.db.exists(
            "Holiday",
            {
                "parent": emp.holiday_list,
                "holiday_date": attendance_date
            }
        )

        if not is_holiday:
            continue

        # 🔹 Skip if attendance already exists
        if frappe.db.exists(
            "Attendance",
            {
                "employee": emp.name,
                "attendance_date": attendance_date
            }
        ):
            continue

        try:
            attendance = frappe.new_doc("Attendance")
            attendance.employee = emp.name
            attendance.attendance_date = attendance_date
            attendance.status = "Holiday"

            attendance.insert(ignore_permissions=True)
            attendance.submit()

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Holiday Attendance Auto Submit Failed"
            )