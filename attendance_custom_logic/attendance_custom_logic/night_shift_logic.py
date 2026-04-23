import frappe
from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts
from datetime import datetime

def run_night_shift_attendance():
    """
    Run auto attendance for NIGHT SHIFTS only
    """
    frappe.logger().info(f"✅ Night Shift Attendance Job Started at {datetime.now()}")

    # Optional: aap filter laga sakte ho sirf night shifts ke liye
    process_auto_attendance_for_all_shifts()  # Or custom logic to filter night shifts

    frappe.logger().info(f"✅ Night Shift Attendance Job Completed at {datetime.now()}")