# attendance_custom_logic/attendance_custom_logic/attendance_custom_logic/in_time_logic.py

import frappe
from frappe.utils import get_datetime, add_days, cint
import traceback


def adjust_in_time(doc, method=None):
    """
    Adjust Attendance in_time based on late entry checkbox.
    - If late_entry = 1 → in_time = first checkin
    - Else → in_time = shift start time
    - Round out_time minutes to :00 if minutes < 30
    - Calculate working hours, duty hours
    - Mark Present if working_hours > 0
    """

    try:
        frappe.log_error(
            f"🔵 adjust_in_time started for {doc.employee} on {doc.attendance_date}",
            "In Time Debug"
        )

        if not doc.employee or not doc.shift:
            frappe.log_error("❌ No employee or shift", "In Time Debug")
            return

        # -----------------------------
        # Fetch shift info
        # -----------------------------
        shift_start_time, shift_end_time = frappe.db.get_value(
            "Shift Type",
            doc.shift,
            ["start_time", "end_time"]
        )

        if not shift_start_time or not shift_end_time:
            frappe.log_error(f"❌ Shift not configured: {doc.shift}", "In Time Debug")
            return

        # -----------------------------
        # Build shift datetime
        # -----------------------------
        shift_start_dt = get_datetime(f"{doc.attendance_date} {shift_start_time}")
        shift_end_dt = get_datetime(f"{doc.attendance_date} {shift_end_time}")

        # Overnight shift handling
        if shift_end_dt <= shift_start_dt:
            shift_end_dt = add_days(shift_end_dt, 1)

        frappe.log_error(
            f"🕒 Shift: {shift_start_dt} → {shift_end_dt}",
            "In Time Debug"
        )

        # -----------------------------
        # Get first check-in
        # -----------------------------
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": doc.employee,
                "time": ["between", [shift_start_dt, shift_end_dt]]
            },
            fields=["time"],
            order_by="time asc",
            limit_page_length=1
        )

        first_checkin = checkins[0].time if checkins else shift_start_dt

        late_entry_marked = cint(doc.get("late_entry"))

        frappe.log_error(
            f"🔍 Late Entry: {late_entry_marked}, First Checkin: {first_checkin}",
            "In Time Debug"
        )

        # -----------------------------
        # Set In Time
        # -----------------------------
        old_in_time = doc.in_time

        if late_entry_marked:
            doc.in_time = first_checkin
        else:
            doc.in_time = shift_start_dt

        # -----------------------------
        # Out Time Rounding Logic
        # -----------------------------
        old_out_time = doc.out_time

        if doc.out_time:
            if doc.out_time.minute < 30:
                doc.out_time = doc.out_time.replace(
                    minute=0, second=0, microsecond=0
                )

        # -----------------------------
        # Working Hours Calculation
        # -----------------------------
        if doc.in_time and doc.out_time:
            time_diff = doc.out_time - doc.in_time
            working_hours = time_diff.total_seconds() / 3600

            if working_hours < 0:
                working_hours = 0

            doc.working_hours = round(working_hours, 2)
            doc.duty_hours = min(doc.working_hours, 8)

            if doc.working_hours > 0:
                doc.status = "Present"

            frappe.log_error(
                f"🟢 Working Hours: {doc.working_hours}, Duty Hours: {doc.duty_hours}",
                "In Time Debug"
            )

        # -----------------------------
        # User message (optional)
        # -----------------------------
        if old_in_time != doc.in_time or old_out_time != doc.out_time:
            frappe.msgprint(
                f"In Time: {doc.in_time}<br>Out Time: {doc.out_time}",
                title="Attendance Updated",
                indicator="green"
            )

        frappe.log_error("✅ adjust_in_time completed", "In Time Debug")

    except Exception as e:
        frappe.log_error(
            f"❌ Error in adjust_in_time\n{str(e)}\n{traceback.format_exc()}",
            "In Time Error"
        )
