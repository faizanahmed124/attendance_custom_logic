import frappe

STANDARD_DUTY_HOURS = 8.0


def validate_leave_application(doc, method=None):

    if not doc.employee or not doc.from_date:
        return

    hours = getattr(doc, 'hours', 0)
    if not hours or hours <= 0:
        return

    # ----------------------------------
    # Validation: only one checkbox
    # ----------------------------------
    if doc.custom_deduct_from_overtime and doc.custom_deduct_from_salary:
        frappe.throw(
            "Please select only one: Deduct From Overtime OR Deduct From Salary"
        )

    # ----------------------------------
    # CASE 1: Deduct From Overtime
    # ----------------------------------
    if doc.custom_deduct_from_overtime:
        apply_overtime_deduction(
            doc.employee,
            doc.from_date,
            hours
        )

    # ----------------------------------
    # CASE 2: Deduct From Salary
    # ----------------------------------
    # Attendance untouched
    # Salary slip logic will handle later
    if doc.custom_deduct_from_salary:
        return


def apply_overtime_deduction(employee, date, hours):

    remaining_hours = STANDARD_DUTY_HOURS - float(hours)
    if remaining_hours <= 0:
        return

    attendance_name = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": date
        },
        "name"
    )

    if not attendance_name:
        return

    att = frappe.get_doc("Attendance", attendance_name)

    # ----------------------------------
    # Cancel if already submitted
    # ----------------------------------
    if att.docstatus == 1:
        att.cancel()

    # ----------------------------------
    # Apply short leave logic
    # ----------------------------------
    att.working_hours = float(hours)
    att.custom_overtime = -remaining_hours

    att.flags.ignore_validate = True
    att.flags.ignore_mandatory = True

    att.save(ignore_permissions=True)
    att.submit()
