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
        # =====================================================
# WEEKLY SANDWICH CHECK (Har Tuesday chalega)
# Pichle Saturday aur Monday ki Absent attendance check
# karega, aur beech ke Sunday holiday ko bhi Absent
# mark karega agar dono taraf Absent mile.
# =====================================================
def weekly_sandwich_check():
    from frappe.utils import add_days, getdate

    today = getdate()
    saturday_date = add_days(today, -3)   # Tuesday se 3 din pehle = Saturday
    monday_date = add_days(today, -1)     # Tuesday se 1 din pehle = Monday

    frappe.logger().info(
        f"[Sandwich Weekly Check] Running for Saturday={saturday_date}, Monday={monday_date}"
    )

    # Monday ke Absent records dhoondhein — inhi se backward check hoga
    monday_absent_records = frappe.get_all(
        "Attendance",
        filters={
            "status": "Absent",
            "docstatus": 1,
            "attendance_date": monday_date
        },
        fields=["name", "employee"]
    )

    processed = 0

    for rec in monday_absent_records:
        doc = frappe.get_doc("Attendance", rec.name)
        apply_sandwich_leave(doc)
        processed += 1

    frappe.db.commit()

    frappe.logger().info(
        f"[Sandwich Weekly Check] Done. Monday Absent records processed: {processed}"
    )
    
#     manually testing ka lia console ma run karna hoga, ya phir frappe scheduler ke zariye Tuesday ko automatically run hoga.
# import frappe
# from attendance_custom_logic.attendance_custom_logic.sandwich import weekly_sandwich_check

# weekly_sandwich_check()