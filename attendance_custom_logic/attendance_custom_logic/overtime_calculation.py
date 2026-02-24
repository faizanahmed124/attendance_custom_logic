import frappe
import math

def calculate_overtime(doc, method=None):
    """
    Duty hours & overtime logic:

    NORMAL DAY
    - working_hours < 8  → duty = working_hours
    - working_hours >= 8 → duty = 8
    - overtime only if allow_overtime = 1
    - late minutes slab logic applied

    HOLIDAY
    - Permanent + Holiday + allow_overtime = 1
        → pure working hours = overtime (rounded to 15 min)
    - Holiday but overtime NOT allowed
        → behaves like normal day (NO special overtime)
    """

    # -------------------------
    # RESET VALUES
    # -------------------------
    frappe.db.set_value(
        "Attendance",
        doc.name,
        {
            "custom_duty_hours": 0,
            "custom_overtime": 0
        }
    )

    if doc.status not in ("Present", "Half Day"):
        return

    if not doc.working_hours:
        return

    working_hours = float(doc.working_hours)

    # -------------------------
    # EMPLOYEE INFO
    # -------------------------
    employment_type = frappe.db.get_value(
        "Employee", doc.employee, "employment_type"
    )
    holiday_list = frappe.db.get_value(
        "Employee", doc.employee, "holiday_list"
    )
    allow_overtime = frappe.db.get_value(
        "Employee", doc.employee, "custom_allow_overtime"
    )

    # -------------------------
    # HOLIDAY SPECIAL CASE
    # -------------------------
    if employment_type == "Permanent" and holiday_list:
        is_holiday = frappe.db.exists(
            "Holiday",
            {
                "parent": holiday_list,
                "holiday_date": doc.attendance_date
            }
        )

        # ✅ Holiday + overtime allowed
        if is_holiday and doc.status == "Present" and allow_overtime:
            total_minutes = int(working_hours * 60)

            # round to nearest 15 minutes
            rounded_minutes = 15 * round(total_minutes / 15)
            overtime_hours = rounded_minutes / 60

            frappe.db.set_value(
                "Attendance",
                doc.name,
                {
                    "custom_duty_hours": 0,
                    "custom_overtime": round(overtime_hours, 2)
                }
            )
            return
        # ❌ Holiday but overtime NOT allowed
        # → normal flow continues (no return)

    # -------------------------
    # DUTY HOURS LOGIC
    # -------------------------
    if working_hours < 8:
        frappe.db.set_value(
            "Attendance",
            doc.name,
            "custom_duty_hours",
            round(working_hours, 2)
        )
        return  # ❗ no overtime possible

    # working_hours >= 8
    frappe.db.set_value(
        "Attendance",
        doc.name,
        "custom_duty_hours",
        8.0
    )

    # -------------------------
    # OVERTIME ELIGIBILITY
    # -------------------------
    if not allow_overtime or working_hours <= 8:
        return

    if not (doc.in_time and doc.out_time):
        return

    # -------------------------
    # OVERTIME CALCULATION
    # -------------------------
    time_diff = doc.out_time - doc.in_time
    total_minutes_worked = (
        time_diff.days * 24 * 60
        + time_diff.seconds // 60
    )

    overtime_minutes = total_minutes_worked - 480  # 8 hours

    if overtime_minutes <= 0:
        return

    late_minutes = doc.custom_late_minutes or 0

    # -------------------------
    # SLAB LOGIC (UNCHANGED)
    # -------------------------
    if late_minutes == 0:
        rounded_minutes = (overtime_minutes // 30) * 30
    else:
        if overtime_minutes < 15:
            rounded_minutes = 0
        elif overtime_minutes < 30:
            rounded_minutes = 15
        elif overtime_minutes < 45:
            rounded_minutes = 30
        elif overtime_minutes < 70:
            rounded_minutes = 45
        else:
            rounded_minutes = (overtime_minutes // 15) * 15

    overtime_hours = rounded_minutes / 60

    frappe.db.set_value(
        "Attendance",
        doc.name,
        "custom_overtime",
        round(overtime_hours, 2)
    )