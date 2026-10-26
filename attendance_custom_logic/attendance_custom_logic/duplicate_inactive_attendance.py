import frappe
from frappe.utils import nowdate, getdate, add_days


STATUS_PRIORITY = {"Present": 2, "Half Day": 1, "Work From Home": 1}


def remove_duplicate_attendance(date=None):
    """
    Logic 1:
    Saari attendance jobs chalne ke baad check karo ke kisi employee ki
    same date par multiple (duplicate) attendance to nahi (alag alag shifts ki wajah se,
    jaise Shift A mein aaya aur Shift B mein galti se check-in ho gaya).
    Priority (jo rakhni hai):
        1. Present
        2. Half Day / Work From Home
        3. Baaki (Absent, On Leave ...)
        Same priority mein zyada working hours wali, phir pehle bani hui.
    Baaki sab delete.
    """
    # Baaki jobs (absent / holiday) bhi kal ki date par chalti hain
    date = getdate(date) if date else add_days(getdate(), -1)

    # Un employees ki list nikalo jinki is date ki 1 se zyada attendance hai
    duplicates = frappe.db.sql("""
        SELECT employee, COUNT(name) as cnt
        FROM `tabAttendance`
        WHERE attendance_date = %s
        AND docstatus < 2
        GROUP BY employee
        HAVING cnt > 1
    """, (date,), as_dict=True)

    for row in duplicates:
        employee = row.employee

        records = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee,
                "attendance_date": date,
                "docstatus": ["<", 2],
            },
            fields=["name", "status", "shift", "docstatus", "working_hours"],
            order_by="creation asc",
        )

        if len(records) <= 1:
            continue

        # records creation asc hain, max barabari par pehli wali deta hai
        keep = max(
            records,
            key=lambda r: (STATUS_PRIORITY.get(r.status, 0), r.working_hours or 0),
        )
        to_delete = [r for r in records if r.name != keep.name]

        for rec in to_delete:
            try:
                doc = frappe.get_doc("Attendance", rec.name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Attendance", rec.name, force=True, ignore_permissions=True)

                frappe.logger().info(
                    f"[Duplicate Attendance Removed] Employee: {employee}, "
                    f"Date: {date}, Deleted: {rec.name}, Kept: {keep.name}"
                )
            except Exception:
                frappe.log_error(
                    title="Error Deleting Duplicate Attendance",
                    message=frappe.get_traceback(),
                )

    frappe.db.commit()


def mark_inactive_employee_attendance():
    """
    Logic 2:
    Jitne bhi Inactive employees hain, unki daily attendance
    Absent mark karo — sirf date aur status, check-in/check-out kuch nahi.
    """
    date = nowdate()

    inactive_employees = frappe.get_all(
        "Employee",
        filters={"status": "Inactive"},
        fields=["name", "employee_name", "company"],
    )

    for emp in inactive_employees:
        # Agar already attendance mark ho chuki hai to skip karo
        already_marked = frappe.db.exists(
            "Attendance",
            {
                "employee": emp.name,
                "attendance_date": date,
                "docstatus": ["<", 2],
            },
        )
        if already_marked:
            continue

        try:
            doc = frappe.new_doc("Attendance")
            doc.employee = emp.name
            doc.employee_name = emp.employee_name
            doc.attendance_date = date
            doc.status = "Absent"
            doc.company = emp.company
            doc.insert(ignore_permissions=True)
            doc.submit()
        except Exception:
            frappe.log_error(
                title="Error Marking Inactive Employee Attendance",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()