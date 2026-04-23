import frappe
from frappe.utils import getdate, get_datetime
from datetime import timedelta


def mark_absent_if_no_checkin():
    """
    FINAL RULE:
    - If Attendance already exists → Skip (just "OK")
    - If Attendance doesn't exist and employee is Active → Mark Absent
    """

    attendance_date = getdate() - timedelta(days=1)

    # 12 PM previous day se 12 PM next day tak check
    day_start = get_datetime(f"{attendance_date} 12:00:00") - timedelta(hours=12)
    day_end = day_start + timedelta(hours=24)

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        pluck="name"
    )

    for employee in employees:

        # Step 1: Check if attendance already created for the previous day
        if frappe.db.exists(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": attendance_date,
                "docstatus": 1
            }
        ):
            continue  # Skip if attendance is already created

        # Step 2: If no attendance is created, mark as Absent (for active employee)
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": "Absent"
        })

        attendance.insert(ignore_permissions=True)
        attendance.submit()