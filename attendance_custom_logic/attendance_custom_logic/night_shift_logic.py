import frappe
from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts

def run_night_shift_attendance():
    """
    Run auto attendance after overnight shifts are closed
    """

    frappe.logger().info("✅ Night Shift Attendance Job Started")

    process_auto_attendance_for_all_shifts()

    frappe.logger().info("✅ Night Shift Attendance Job Completed")