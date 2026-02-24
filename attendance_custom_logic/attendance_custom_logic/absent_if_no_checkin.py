import frappe
from frappe.utils import getdate, get_datetime
from datetime import timedelta


def mark_absent_if_no_checkin():
    """
    Run NEXT DAY.
    Marks ABSENT for PREVIOUS DAY attendance
    - Permanent employees: skip if holiday
    - Daily Wages employees: mark absent even if holiday
    """

    attendance_date = getdate() - timedelta(days=1)

    day_start = get_datetime(f"{attendance_date} 00:00:00")
    day_end = get_datetime(f"{attendance_date} 23:59:59")

    # night shift window (previous evening)
    night_shift_start = day_start - timedelta(hours=12)

    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active"
        },
        pluck="name"
    )

    for employee in employees:

        # Get employment type
        employment_type = frappe.db.get_value("Employee", employee, "employment_type")

        # 1️⃣ Already submitted attendance?
        if frappe.db.exists(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": attendance_date,
                "docstatus": 1
            }
        ):
            continue

        # 2️⃣ Any check-in for that shift window?
        if frappe.db.exists(
            "Employee Checkin",
            {
                "employee": employee,
                "time": ["between", [night_shift_start, day_end]]
            }
        ):
            continue

        # 3️⃣ Holiday check (only for Permanent employees)
        if employment_type == "Permanent":
            holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
            if holiday_list and frappe.db.exists(
                "Holiday",
                {
                    "holiday_list": holiday_list,
                    "holiday_date": attendance_date
                }
            ):
                continue

        # 4️⃣ Mark Absent
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": "Absent"
        })

        attendance.insert(ignore_permissions=True)
        attendance.submit()
