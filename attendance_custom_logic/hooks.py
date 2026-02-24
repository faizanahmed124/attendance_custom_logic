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
        # Holiday attendance at 11:00 AM (recommended time)
        "0 12 * * *": [
            "attendance_custom_logic.attendance_custom_logic.holiday_logic.mark_holiday_attendance",
        ],

        # NIGHT SHIFT - Process early morning checkouts (6 AM - 8 AM)
        "30 9 * * *": [  # Runs at 9:30 AM
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],
        
        # SECOND RUN - For late checkouts or missed entries
        "0 11 * * *": [  # Runs at 11:00 PM
            "attendance_custom_logic.attendance_custom_logic.night_shift_logic.run_night_shift_attendance"
        ],

        # Mark absent if no check-in (run at end of day)
       "0 10 * * *": [
            "attendance_custom_logic.attendance_custom_logic.absent_if_no_checkin.mark_absent_if_no_checkin"
        ],
    }
}

# -------------------------
# -------------------------
# Document Events
# -------------------------
doc_events = {
    "Attendance": {
        "validate": [
            "attendance_custom_logic.attendance_custom_logic.attendance.validate_attendance",
            "attendance_custom_logic.attendance_custom_logic.in_time_logic.adjust_in_time"
        ],
        "on_submit": "attendance_custom_logic.attendance_custom_logic.overtime_calculation.calculate_overtime",
        # "before_save": "attendance_custom_logic.attendance_custom_logic.in_time_logic.adjust_in_time"  # isko hata do ya comment kar do
    },
    
    "Leave Application": {
        "validate": "attendance_custom_logic.attendance_custom_logic.leave.validate_leave_application"
    }
}