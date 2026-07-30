import frappe
from frappe.utils import getdate, add_days


# =====================================================
# SANDWICH LEAVE RULE
# Agar holiday se 1 din pehle Absent aur holiday ke
# 1 din baad bhi Absent, to darmiyan wale holiday
# din(s) bhi Absent mark honge.
# =====================================================
def apply_sandwich_leave(doc, method=None):

    if doc.status != "Absent":
        return

    employee = doc.employee
    attendance_date = getdate(doc.attendance_date)

    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
    if not holiday_list:
        return

    # holiday(s) is absent ke baad, phir dobara absent
    check_and_mark_sandwich(employee, attendance_date, holiday_list, direction="forward")

    # holiday(s) is absent se pehle, us se pehle bhi absent
    check_and_mark_sandwich(employee, attendance_date, holiday_list, direction="backward")


def check_and_mark_sandwich(employee, base_date, holiday_list, direction):
    step = 1 if direction == "forward" else -1
    holiday_dates = []

    cursor = add_days(base_date, step)

    # consecutive holidays collect karo
    while frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": cursor}):
        holiday_dates.append(cursor)
        cursor = add_days(cursor, step)

    if not holiday_dates:
        return

    # cursor ab holiday block ke turant baad wala din hai
    other_side_status = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": cursor, "docstatus": 1},
        "status"
    )

    if other_side_status == "Absent":
        for hdate in holiday_dates:
            mark_day_absent(employee, hdate)


def mark_day_absent(employee, date):
    existing = frappe.db.exists(
        "Attendance",
        {"employee": employee, "attendance_date": date, "docstatus": ["!=", 2]}
    )

    if existing:
        frappe.db.set_value("Attendance", existing, "status", "Absent")
    else:
        att = frappe.new_doc("Attendance")
        att.employee = employee
        att.attendance_date = date
        att.status = "Absent"
        att.company = frappe.db.get_value("Employee", employee, "company")
        att.insert(ignore_permissions=True)
        att.submit()


# =====================================================
# MINIMUM WORKING HOURS RULE
# Overtime-allowed employee : working_hours < 2  -> Absent
# Non-overtime employee     : working_hours < 4  -> Absent
# =====================================================
def apply_minimum_working_hours_rule(doc, method=None):

    if doc.status not in ("Present", "Half Day"):
        return

    if not doc.working_hours:
        return

    working_hours = float(doc.working_hours)

    allow_overtime = frappe.db.get_value(
        "Employee", doc.employee, "custom_allow_overtime"
    )

    min_hours = 2 if allow_overtime else 4

    if working_hours < min_hours:
        frappe.db.set_value(
            "Attendance",
            doc.name,
            {
                "status": "Absent",
                "custom_duty_hours": 0,
                "custom_overtime": 0,
                "custom_less_duty_hour": 0
            }
        )