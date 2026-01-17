import frappe
from frappe.utils import get_datetime


def validate_attendance(doc, method=None):

    if not doc.employee or not doc.attendance_date:
        return

    # ✅ Only employees with overtime allowed
    allow_ot = frappe.db.get_value(
        "Employee",
        doc.employee,
        "allow_overtime"
    )

    if not allow_ot:
        return

    apply_late_deduction(doc)
    apply_early_exit_ot_rounding(doc)
    apply_holiday_overtime(doc)


# ---------------------------------------------------
# Late Coming → Deduct from OT based on slabs
# ---------------------------------------------------
def apply_late_deduction(doc):

    if not doc.shift or not doc.in_time or not doc.working_hours:
        return

    shift = frappe.get_value(
        "Shift Type",
        doc.shift,
        ["start_time", "late_entry_grace_period"],
        as_dict=True
    )

    if not shift or not shift.start_time:
        return

    shift_start_dt = get_datetime(
        f"{doc.attendance_date} {shift.start_time}"
    )

    in_time = get_datetime(doc.in_time)

    late_minutes = max(
        0,
        int((in_time - shift_start_dt).total_seconds() // 60)
    )

    grace = shift.late_entry_grace_period or 0

    if late_minutes <= grace:
        return

    # ✅ SLAB-BASED LATE DEDUCTION
    if late_minutes >= 45:
        deduction_minutes = 60
    elif late_minutes >= 30:
        deduction_minutes = 45
    elif late_minutes >= 15:
        deduction_minutes = 30
    elif late_minutes >= 5:
        deduction_minutes = 15
    else:
        deduction_minutes = 0

    deduction_hours = deduction_minutes / 60

    doc.working_hours = max(
        0,
        doc.working_hours - deduction_hours
    )


# ---------------------------------------------------
# Early Exit / Overtime Rounding Policy
# ---------------------------------------------------
def apply_early_exit_ot_rounding(doc):

    if not doc.working_hours or doc.working_hours <= 0:
        return

    # OT rounding only for employees with allow_overtime
    allow_ot = frappe.db.get_value(
        "Employee",
        doc.employee,
        "allow_overtime"
    )

    if not allow_ot:
        return

    # Convert hours → minutes
    total_minutes = int(doc.working_hours * 60)

    # Floor to 30-minute slabs
    payable_minutes = (total_minutes // 30) * 30

    # Convert back to hours
    doc.working_hours = payable_minutes / 60


# ---------------------------------------------------
# Holiday Overtime
# ---------------------------------------------------
def apply_holiday_overtime(doc):

    if not doc.working_hours or doc.working_hours <= 0:
        return

    holiday = frappe.db.exists(
        "Holiday",
        {
            "holiday_date": doc.attendance_date
        }
    )

    if not holiday:
        return

    doc.custom_overtime = doc.working_hours
