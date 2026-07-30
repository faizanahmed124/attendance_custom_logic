import frappe

def test_employee_attendance(employee_id, from_date=None, to_date=None, dry_run=True):
    """
    Ek employee ke Attendance records pe logic re-run karta hai.
    
    from_date, to_date -> optional. Agar nahi diye to saare records process honge.
    dry_run=True  -> sirf print karega, save nahi karega
    dry_run=False -> actual save karega
    """
    from attendance_custom_logic.attendance_custom_logic.overtime_calculation import calculate_overtime
    from attendance_custom_logic.attendance_custom_logic.sandwich import (
        apply_minimum_working_hours_rule,
        apply_sandwich_leave,
    )

    filters = {"employee": employee_id, "docstatus": 1}

    if from_date and to_date:
        filters["attendance_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["attendance_date"] = [">=", from_date]
    elif to_date:
        filters["attendance_date"] = ["<=", to_date]

    records = frappe.get_all(
        "Attendance",
        filters=filters,
        order_by="attendance_date asc",
        fields=["name", "attendance_date", "status", "working_hours"]
    )

    print(f"\nDate range: {from_date or 'start'} to {to_date or 'end'}")
    print(f"Total records found: {len(records)}\n")

    for r in records:
        doc = frappe.get_doc("Attendance", r.name)
        before_status = doc.status
        before_hours = doc.working_hours

        apply_minimum_working_hours_rule(doc)
        calculate_overtime(doc)
        apply_sandwich_leave(doc)

        doc.reload()

        print(
            f"{doc.attendance_date} | "
            f"Before: {before_status} ({before_hours}h) -> "
            f"After: {doc.status} | "
            f"Duty: {doc.custom_duty_hours} | "
            f"OT: {doc.custom_overtime} | "
            f"Less Duty: {doc.custom_less_duty_hour}"
        )

    if dry_run:
        frappe.db.rollback()
        print("\n✅ DRY RUN complete — koi changes save nahi hue.")
    else:
        frappe.db.commit()
        print("\n✅ Changes saved to database.")
