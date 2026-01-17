import frappe
from frappe.utils import getdate, get_datetime
from datetime import timedelta  # Use timedelta instead of add_hours


def mark_absent_if_no_checkin(attendance_date=None):
    """
    Mark Absent for Permanent employees if:
    - No Attendance exists
    - No valid Check-in exists (same day OR night shift)
    - Day is NOT a Holiday
    """

    if not attendance_date:
        attendance_date = getdate()

    day_start = get_datetime(f"{attendance_date} 00:00:00")
    day_end = get_datetime(f"{attendance_date} 23:59:59")

    # Allow night-shift check-ins (previous 12 hours)
    night_shift_start = day_start - timedelta(hours=12)

    employees = frappe.get_all(
        "Employee",
        filters={
            "employment_type": "Permanent",
            "status": "Active"
        },
        pluck="name"
    )

    for employee in employees:

        # 1️⃣ Skip if attendance already exists
        if frappe.db.exists(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": attendance_date,
                "docstatus": ["!=", 2]
            }
        ):
            continue

        # 2️⃣ Skip if check-in exists (same day OR night shift)
        checkin_exists = frappe.db.exists(
            "Employee Checkin",
            {
                "employee": employee,
                "time": ["between", [night_shift_start, day_end]]
            }
        )

        if checkin_exists:
            continue

        # 3️⃣ Skip if holiday
        if frappe.db.exists(
            "Holiday",
            {"holiday_date": attendance_date}
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
