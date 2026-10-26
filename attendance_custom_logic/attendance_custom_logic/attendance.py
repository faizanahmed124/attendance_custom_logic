# import frappe


# def validate_attendance(doc, method=None):
#     """
#     Entry point for Attendance validation.
#     This file ONLY handles late-related rules.
#     """

#     if not doc.employee or not doc.attendance_date:
#         return

#     # Only employees allowed for overtime adjustments
#     allow_ot = frappe.db.get_value(
#         "Employee",
#         doc.employee,
#         "custom_allow_overtime"
#     )

#     if not allow_ot:
#         return

#     # Only late deduction logic here
#     apply_late_deduction(doc)


# # ---------------------------------------------------
# # Late Coming → Deduct from Overtime
# # ---------------------------------------------------
# def apply_late_deduction(doc):

#     # No overtime → nothing to deduct
#     if not doc.custom_overtime or doc.custom_overtime <= 0:
#         return

#     late_minutes = doc.custom_late_minutes or 0

#     # Less than 5 minutes → ignore
#     if late_minutes < 5:
#         return

#     # Late slabs
#     if 5 <= late_minutes <= 14:
#         deduction_minutes = 15
#     elif 15 <= late_minutes <= 29:
#         deduction_minutes = 30
#     elif 30 <= late_minutes <= 44:
#         deduction_minutes = 45
#     else:  # 45+
#         deduction_minutes = 60

#     deduction_hours = deduction_minutes / 60

#     # Deduct from overtime (never below zero)
#     doc.custom_overtime = max(
#         0,
#         doc.custom_overtime - deduction_hours
#     )


def validate_attendance(doc, method=None):
    pass
