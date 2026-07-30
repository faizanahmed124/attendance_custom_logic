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
        # Holiday attendance at 12:00 AM (recommended time)
        "10 14 * * *": [
            "attendance_custom_logic.attendance_custom_logic.holiday_logic.mark_holiday_attendance",
        ],

        # NIGHT SHIFT - Process early morning checkouts (6 AM - 8 AM)
        "0 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],

        "30 11 * * *": [
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],

        "0 13 * * * ": [
            "attendance_custom_logic.attendance_custom_logic.absent_if_no_checkin.mark_absent_if_no_checkin"
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