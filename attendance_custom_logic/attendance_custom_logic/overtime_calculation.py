import frappe
import math


# =====================================================
# DUTY HOURS SLAB LOCK FUNCTION (15 MINUTES)
# =====================================================
def lock_duty_hours_to_slab(doc):

    duty_hours = frappe.db.get_value(
        "Attendance", doc.name, "custom_duty_hours"
    )

    if not duty_hours:
        return

    total_minutes = int(float(duty_hours) * 60)
    remainder = total_minutes % 60

    # 15 minute slab
    if remainder < 15:
        slab_minutes = 0
    elif remainder < 30:
        slab_minutes = 15
    elif remainder < 45:
        slab_minutes = 30
    else:
        slab_minutes = 45

    locked_minutes = (total_minutes // 60) * 60 + slab_minutes
    locked_hours = locked_minutes / 60

    frappe.db.set_value(
        "Attendance",
        doc.name,
        "custom_duty_hours",
        float(f"{locked_hours:.2f}")
    )


# =====================================================
# MAIN FUNCTION
# =====================================================
def calculate_overtime(doc, method=None):

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
        lock_duty_hours_to_slab(doc)
        return

    if not doc.working_hours:
        lock_duty_hours_to_slab(doc)
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
            rounded_minutes = 15 * round(total_minutes / 15)
            overtime_hours = rounded_minutes / 60

            frappe.db.set_value(
                "Attendance",
                doc.name,
                {
                    "custom_duty_hours": 0,
                    "custom_overtime": float(f"{overtime_hours:.2f}")
                }
            )

            lock_duty_hours_to_slab(doc)
            return

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

        lock_duty_hours_to_slab(doc)
        return

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
        lock_duty_hours_to_slab(doc)
        return

    if not (doc.in_time and doc.out_time):
        lock_duty_hours_to_slab(doc)
        return

    # -------------------------
    # OVERTIME CALCULATION
    # -------------------------
    time_diff = doc.out_time - doc.in_time

    total_minutes_worked = (
        time_diff.days * 24 * 60
        + time_diff.seconds // 60
    )

    overtime_minutes = total_minutes_worked - 480

    if overtime_minutes <= 0:
        lock_duty_hours_to_slab(doc)
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
        float(f"{overtime_hours:.2f}")
    )

    # FINAL LOCK
    lock_duty_hours_to_slab(doc)