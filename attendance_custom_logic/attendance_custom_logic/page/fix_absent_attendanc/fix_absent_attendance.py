"""
fix_absent_attendance.py
-------------------------
Place this file inside your app, e.g.:
  attendance_custom_logic/attendance_custom_logic/attendance_custom_logic/fix_absent_attendance.py

WHAT IT DOES
------------
For every "Absent" Attendance record between from_date and to_date:
  1. Looks at ALL active Shift Types (not just the employee's assigned shift).
  2. For each shift, builds that shift's time-window anchored to the
     attendance_date (handles overnight/night shift automatically:
     if end_time <= start_time, the window rolls into the next day).
  3. Night-shift-style (overnight) windows get a +4 hour buffer added
     AFTER the shift's normal end time, so an employee doing up to
     4 hours of overtime is still captured by the checkin search.
  4. Whichever shift actually has a real Employee Checkin landing
     inside its core (non-buffered) window is the shift that "wins" -
     i.e. the shift is decided BY the checkin/checkout, exactly as
     requested ("jis shift ka checkin hoga usi shift ma ayee").
  5. If a match is found: sets shift / in_time / out_time / working_hours
     / duty_hours / status = Present directly via frappe.db.set_value
     (works even though docstatus = 1), then re-runs your existing
     calculate_overtime() and apply_late_deduction() so overtime /
     late-deduction stay consistent with the rest of your app.
  6. If no checkin is found at all, the record is left as Absent and
     reported as such - nothing is changed.

Nothing is deleted or cancelled. Only Absent records are touched;
Present/Half Day/On Leave records are never modified.

HOW TO TEST ON ONE EMPLOYEE FIRST
----------------------------------
bench --site YOUR_SITE console

>>> from attendance_custom_logic.attendance_custom_logic.fix_absent_attendance import test_single_employee
>>> test_single_employee("HR-EMP-0001", "2026-09-01", "2026-09-15")

This only touches that one employee's records in that date range and
prints a result dict per record so you can review before going live.

HOW TO RUN FOR EVERYONE (once you're confident)
------------------------------------------------
>>> from attendance_custom_logic.attendance_custom_logic.fix_absent_attendance import fix_absent_attendance
>>> results = fix_absent_attendance("2026-09-01", "2026-09-15")

STRONGLY RECOMMENDED: take a database backup (or run on a staging/test
site copy) before running this on real data for the first time, since
it force-updates already-submitted Attendance documents.
"""

import frappe
from frappe.utils import getdate, get_datetime
from datetime import timedelta
import json

from attendance_custom_logic.attendance_custom_logic.overtime_calculation import calculate_overtime
from attendance_custom_logic.attendance_custom_logic.attendance import apply_late_deduction
from attendance_custom_logic.attendance_custom_logic.in_time_logic import adjust_in_time


# How many hours after shift START to keep searching for a checkout.
# Wide enough to comfortably cover a full shift + any realistic overtime
# (day shift ~12hrs, night shift ~12hrs + OT), but well under 24 hours so
# it never reaches into the START of the NEXT day's shift for this
# employee (which is what caused an early "IN" the next morning to get
# picked up as if it were today's "out_time").
MAX_SHIFT_SPAN_HOURS = 20

# Small grace window before shift start, in case someone checks in a
# little early (only widens the search - adjust_in_time() itself decides
# the actual in_time value).
GRACE_BEFORE_HOURS = 1

# How far forward to scan just to find out WHICH shift is tagged on this
# day's checkins. This is intentionally wide (covers an overnight shift
# starting in the evening) - it is only used to identify the shift name,
# NOT to decide in_time/out_time (that uses the shift's own window below).
SHIFT_SCAN_HOURS = 36


def fix_absent_attendance(from_date, to_date, employee=None):
    """Main entry point. Loops every Absent Attendance in the date range."""

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    filters = {
        "status": "Absent",
        "docstatus": 1,
        "attendance_date": ["between", [from_date, to_date]],
    }
    if employee:
        filters["employee"] = employee

    absent_records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=["name", "employee", "attendance_date"],
        order_by="attendance_date asc",
    )

    results = []
    for rec in absent_records:
        results.append(_process_single_absent(rec))

    frappe.db.commit()

    for r in results:
        print(r)

    return results


def test_single_employee(employee, from_date, to_date):
    """Convenience wrapper for testing on exactly one employee."""
    return fix_absent_attendance(from_date, to_date, employee=employee)


@frappe.whitelist()
def run_fix_absent_attendance(from_date, to_date, employee=None):
    """
    Kept for console/testing use where a request timeout isn't a concern.
    The front-end Page uses start_fix_absent_attendance() below instead,
    which runs this in the background so a large ("all employees") run
    never hits the web request timeout.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if to_date < from_date:
        frappe.throw("To Date From Date se pehle nahi ho sakti.")

    if (to_date - from_date).days > 4:  # 4 days difference = 5 days inclusive
        frappe.throw("Ek waqt mein zyada se zyada 5 din ki range select karein.")

    if not employee:
        employee = None

    return fix_absent_attendance(from_date, to_date, employee=employee)


@frappe.whitelist()
def start_fix_absent_attendance(from_date, to_date, employee=None):
    """
    Whitelisted entry point for the front-end Page. Queues the actual
    work as a background job (so it can take as long as it needs
    without ever hitting the web request timeout) and immediately
    returns a job_id. The front-end polls get_fix_absent_attendance_status()
    with that job_id until it's done.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if to_date < from_date:
        frappe.throw("To Date From Date se pehle nahi ho sakti.")

    if (to_date - from_date).days > 4:  # 4 days difference = 5 days inclusive
        frappe.throw("Ek waqt mein zyada se zyada 5 din ki range select karein.")

    if not employee:
        employee = None

    job_key = f"fix-absent-attendance-{frappe.generate_hash(length=10)}"

    frappe.cache().set_value(
        job_key,
        json.dumps({"status": "Queued", "results": []}),
        expires_in_sec=3600,
    )

    frappe.enqueue(
        "attendance_custom_logic.attendance_custom_logic.fix_absent_attendance._run_job",
        queue="long",
        timeout=3600,
        job_name=job_key,
        from_date=str(from_date),
        to_date=str(to_date),
        employee=employee,
        job_key=job_key,
    )

    return {"job_id": job_key}


def _run_job(from_date, to_date, employee, job_key):
    """Actual background worker function - runs with no request timeout."""
    try:
        results = fix_absent_attendance(from_date, to_date, employee=employee)
        frappe.cache().set_value(
            job_key,
            json.dumps({"status": "Complete", "results": results}),
            expires_in_sec=3600,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Fix Absent Attendance Job Failed")
        frappe.cache().set_value(
            job_key,
            json.dumps({"status": "Failed", "results": [], "error": frappe.get_traceback()}),
            expires_in_sec=3600,
        )


@frappe.whitelist()
def get_fix_absent_attendance_status(job_id):
    """Polled by the front-end to check progress / fetch final results."""
    raw = frappe.cache().get_value(job_id)
    if not raw:
        return {"status": "Unknown"}
    return json.loads(raw)


def _process_single_absent(rec):
    employee = rec.employee
    attendance_date = rec.attendance_date

    match = _find_matching_shift_and_checkins(employee, attendance_date)

    if not match:
        return {
            "attendance": rec.name,
            "employee": employee,
            "date": str(attendance_date),
            "result": "No checkin found — left as Absent",
        }

    shift_name, _first_checkin, last_checkin = match

    # Step 1: attach the shift + the raw (unrounded) out_time we found.
    # late_entry is explicitly reset to 0 here (rather than left untouched)
    # so adjust_in_time()'s default branch fires: in_time = shift start
    # time. This also undoes any leftover late_entry=1 from a previous
    # run of this tool on the same record.
    frappe.db.set_value(
        "Attendance",
        rec.name,
        {
            "shift": shift_name,
            "out_time": last_checkin,
            "late_entry": 0,
        },
    )

    # Step 2: run YOUR existing in-time logic. It will look up the first
    # checkin within the shift's own window itself, set in_time, round
    # out_time, compute working_hours, and set status = Present.
    doc = frappe.get_doc("Attendance", rec.name)
    adjust_in_time(doc)

    # adjust_in_time() only mutates the in-memory doc - persist the fields
    # it actually changed. (doc.duty_hours is set by that function too, but
    # it is not a real column in this app - custom_duty_hours, set later by
    # calculate_overtime(), is what's actually used - so we don't write it.)
    frappe.db.set_value(
        "Attendance",
        rec.name,
        {
            "in_time": doc.in_time,
            "out_time": doc.out_time,
            "working_hours": doc.working_hours,
            "status": doc.status,
        },
    )

    # Step 3: late minutes (best-effort — tell me if you compute this
    # elsewhere and I'll swap this out for the real source).
    shift_start_time = frappe.db.get_value("Shift Type", shift_name, "start_time")
    shift_start_dt = get_datetime(f"{attendance_date} {shift_start_time}")
    late_minutes = 0
    if doc.in_time and doc.in_time > shift_start_dt:
        late_minutes = int((doc.in_time - shift_start_dt).total_seconds() / 60)
    frappe.db.set_value("Attendance", rec.name, "custom_late_minutes", late_minutes)

    # Step 4: run YOUR existing overtime logic (handles duty hours, slabs,
    # holiday overtime case, everything) - persists itself.
    doc = frappe.get_doc("Attendance", rec.name)
    calculate_overtime(doc)

    # Step 5: run YOUR existing late-deduction logic on top of that.
    doc = frappe.get_doc("Attendance", rec.name)  # reload with fresh custom_overtime
    apply_late_deduction(doc)  # mutates doc.custom_overtime in memory only
    frappe.db.set_value("Attendance", rec.name, "custom_overtime", doc.custom_overtime)

    return {
        "attendance": rec.name,
        "employee": employee,
        "date": str(attendance_date),
        "shift": shift_name,
        "in_time": str(doc.in_time),
        "out_time": str(doc.out_time),
        "working_hours": doc.working_hours,
        "status": doc.status,
        "overtime": doc.custom_overtime,
        "result": "Updated",
    }


def _find_matching_shift_and_checkins(employee, attendance_date):
    """
    Step 1: find WHICH shift is tagged on this day's checkins (Employee
    Checkin's own "shift" field), scanning a wide window so an overnight
    shift starting in the evening is still found.

    Step 2: once the shift is known, search for checkins starting from
    that shift's own start_time (with a small grace period before it)
    up to MAX_SHIFT_SPAN_HOURS later. This window is generous enough to
    catch a normal full shift plus overtime, but stays comfortably under
    24 hours so it can never reach into the START of the employee's
    NEXT shift the following day (which is what caused a day shift to
    wrongly grab tomorrow's first "IN" as if it were today's "out_time").
    """
    scan_start = get_datetime(f"{attendance_date} 00:00:00")
    scan_end = scan_start + timedelta(hours=SHIFT_SCAN_HOURS)

    tagged = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [scan_start, scan_end]],
            "shift": ["is", "set"],
        },
        fields=["shift"],
        order_by="time asc",
        limit_page_length=1,
    )

    if not tagged:
        return None

    shift_name = tagged[0].shift

    shift_start_time = frappe.db.get_value("Shift Type", shift_name, "start_time")
    if not shift_start_time:
        return None

    shift_start_dt = get_datetime(f"{attendance_date} {shift_start_time}")

    search_start = shift_start_dt - timedelta(hours=GRACE_BEFORE_HOURS)
    search_end = shift_start_dt + timedelta(hours=MAX_SHIFT_SPAN_HOURS)

    window_checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "shift": shift_name,
            "time": ["between", [search_start, search_end]],
        },
        fields=["time"],
        order_by="time asc",
    )

    if not window_checkins:
        return None

    return shift_name, window_checkins[0].time, window_checkins[-1].time