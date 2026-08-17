app_name = "attendance_custom_logic"
app_title = "Attendance Custom Logic"
app_publisher = "Faizan"
app_description = "Custom attendance rules and validation"
app_email = "Faizanahmed1295@gmail.com"
app_license = "mit"

# -------------------------
# Scheduler Events
# -------------------------
scheduler_events = {
    "cron": {
        # NIGHT SHIFT - Process early morning checkouts
        "0 9 * * *": [
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],

        "30 9 * * *": [
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],

        # Holiday attendance
        "0 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.holiday_logic.mark_holiday_attendance",
        ],

        # Absent if no check-in
        "15 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.absent_if_no_checkin.mark_absent_if_no_checkin"
        ],

        # Remove duplicate attendance (saari jobs ke baad)
        "30 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.duplicate_inactive_attendance.remove_duplicate_attendance"
        ],

        # Mark Absent attendance for Inactive employees
        "45 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.duplicate_inactive_attendance.mark_inactive_employee_attendance"
        ],

        # WEEKLY SANDWICH CHECK - Har Tuesday 2:00 AM ko chalega
        "0 2 * * 2": [
            "attendance_custom_logic.attendance_custom_logic.sandwich.weekly_sandwich_check"
        ],
    }
}

# -------------------------
# Document Events
# -------------------------
doc_events = {
    "Attendance": {
        "validate": [
            "attendance_custom_logic.attendance_custom_logic.attendance.validate_attendance",
            "attendance_custom_logic.attendance_custom_logic.in_time_logic.adjust_in_time"
        ],
        "on_submit": [
            "attendance_custom_logic.attendance_custom_logic.sandwich.apply_minimum_working_hours_rule",
            "attendance_custom_logic.attendance_custom_logic.overtime_calculation.calculate_overtime",
            "attendance_custom_logic.attendance_custom_logic.sandwich.apply_sandwich_leave",
        ],
        "on_cancel": [
            "attendance_custom_logic.attendance_custom_logic.overtime_calculation.calculate_overtime",
        ],
    },

    "Leave Application": {
        "validate": "attendance_custom_logic.attendance_custom_logic.leave.validate_leave_application"
    }
}