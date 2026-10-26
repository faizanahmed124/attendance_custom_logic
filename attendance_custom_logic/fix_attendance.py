"""
15-10-2026 (ya di gayi date) ki galat Absent attendance theek karta hai.

Kya karta hai:
  1. Us date ki submitted/draft Attendance jin ka status Absent hai, uthata hai.
  2. Har employee ke us shift-date ke Employee Checkins dekhta hai.
  3. Agar check-out aa chuka hai (2 ya zyada punches), to HRMS ka apna shift logic
     (ShiftType.get_attendance) chala kar naya status nikalta hai: working hours,
     late entry, early exit sab Shift Type ki settings se.
  4. Naya status purane se alag ho to: purani attendance cancel + delete,
     checkins ka link hatata hai, aur HRMS ke mark_attendance_and_link_log se
     nayi attendance bana kar checkins link karta hai.

Pehle hamesha dry run (dry_run=1) chalayein. Wo sirf report dikhata hai.

Chalane ka tareeqa (frappe-bench folder se):
  Dry run:
    bench --site atshr.com execute attendance_custom_logic.fix_attendance.run --kwargs "{'date': '2026-10-15', 'dry_run': 1}"
  Asal fix:
    bench --site atshr.com execute attendance_custom_logic.fix_attendance.run --kwargs "{'date': '2026-10-15', 'dry_run': 0}"
"""
import frappe
from frappe.utils import getdate, add_days

CHECKIN_FIELDS = [
    "name", "employee", "log_type", "time", "shift", "shift_start", "shift_end",
    "shift_actual_start", "shift_actual_end", "device_id", "attendance", "skip_auto_attendance",
]


def _logs_for(employee, day):
    """Is employee ke wo checkins jo is date ki shift ke hain (shift_start ki date se)."""
    nxt = add_days(day, 1)
    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "shift_start": [">=", f"{day} 00:00:00"],
            "time": ["<", f"{add_days(day, 2)} 00:00:00"],
        },
        fields=CHECKIN_FIELDS,
        order_by="time asc",
    )
    logs = [l for l in logs if l.shift_start and getdate(l.shift_start) == getdate(day)]
    if logs:
        return logs
    # shift_start khali ho to us din ke punches
    return frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee, "time": ["between", [f"{day} 00:00:00", f"{nxt} 00:00:00"]]},
        fields=CHECKIN_FIELDS,
        order_by="time asc",
    )


def _evaluate(shift_name, logs):
    st = frappe.get_cached_doc("Shift Type", shift_name)
    status, working_hours, late_entry, early_exit, in_time, out_time = st.get_attendance(logs)
    return {
        "status": status, "working_hours": working_hours, "late_entry": late_entry,
        "early_exit": early_exit, "in_time": in_time, "out_time": out_time,
    }


def run(date="2026-10-15", dry_run=1, statuses=("Absent",)):
    from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

    day = getdate(date)
    dry_run = int(dry_run)
    if isinstance(statuses, str):
        statuses = [statuses]

    atts = frappe.get_all(
        "Attendance",
        filters={"attendance_date": day, "docstatus": ["<", 2], "status": ["in", list(statuses)]},
        fields=["name", "employee", "employee_name", "status", "shift", "docstatus",
                "leave_application", "attendance_request"],
        order_by="employee",
    )

    print(f"\n{'DRY RUN' if dry_run else 'FIX'} for {day}: {len(atts)} attendance ({', '.join(statuses)})\n")
    print(f"{'Employee':<10} {'Naam':<28} {'Shift':<10} {'Punches':>7}  {'Purana':<8} -> {'Naya':<10} {'Hours':>6}  Note")
    print("-" * 110)

    counts = {"fixed": 0, "would_fix": 0, "same": 0, "no_out": 0, "no_shift": 0, "skipped": 0, "error": 0}

    for a in atts:
        name = (a.employee_name or "")[:27]
        try:
            if a.leave_application or a.attendance_request:
                counts["skipped"] += 1
                print(f"{a.employee:<10} {name:<28} {'':<10} {'':>7}  {a.status:<8} -> {'':<10} {'':>6}  skip: leave/attendance request")
                continue

            logs = _logs_for(a.employee, day)
            logs = [l for l in logs if not l.skip_auto_attendance]
            shift = a.shift or next((l.shift for l in logs if l.shift), None)

            if len(logs) < 2:
                counts["no_out"] += 1
                print(f"{a.employee:<10} {name:<28} {shift or '-':<10} {len(logs):>7}  {a.status:<8} -> {'':<10} {'':>6}  check-out nahi, chhor diya")
                continue
            if not shift or not all(l.shift_actual_start for l in logs):
                counts["no_shift"] += 1
                print(f"{a.employee:<10} {name:<28} {shift or '-':<10} {len(logs):>7}  {a.status:<8} -> {'':<10} {'':>6}  checkins par shift nahi, chhor diya")
                continue

            for l in logs:  # sab logs ek hi shift ke hon
                l.shift = shift
            new = _evaluate(shift, logs)
            note = ("late " if new["late_entry"] else "") + ("early-exit" if new["early_exit"] else "")
            hours = f"{(new['working_hours'] or 0):.2f}"

            if new["status"] == a.status:
                counts["same"] += 1
                print(f"{a.employee:<10} {name:<28} {shift:<10} {len(logs):>7}  {a.status:<8} -> {new['status']:<10} {hours:>6}  waisa hi rahega {note}")
                continue

            if dry_run:
                counts["would_fix"] += 1
                print(f"{a.employee:<10} {name:<28} {shift:<10} {len(logs):>7}  {a.status:<8} -> {new['status']:<10} {hours:>6}  BADLEGA {note}")
                continue

            # --- asal fix: purani attendance hatao
            doc = frappe.get_doc("Attendance", a.name)
            if doc.docstatus == 1:
                doc.flags.ignore_permissions = True
                doc.cancel()
            frappe.db.sql("UPDATE `tabEmployee Checkin` SET attendance = NULL WHERE attendance = %s", a.name)
            frappe.delete_doc("Attendance", a.name, ignore_permissions=True, force=True)

            # --- nayi attendance (HRMS ka apna function, logs bhi link karta hai)
            mark_attendance_and_link_log(
                logs, new["status"], day, new["working_hours"], new["late_entry"],
                new["early_exit"], new["in_time"], new["out_time"], shift,
            )
            frappe.db.commit()
            counts["fixed"] += 1
            print(f"{a.employee:<10} {name:<28} {shift:<10} {len(logs):>7}  {a.status:<8} -> {new['status']:<10} {hours:>6}  THEEK HO GAYA {note}")

        except Exception as e:  # noqa: BLE001
            frappe.db.rollback()
            counts["error"] += 1
            print(f"{a.employee:<10} {name:<28} {'':<10} {'':>7}  {a.status:<8} -> {'':<10} {'':>6}  ERROR: {e}")

    print("-" * 110)
    print("Khulasa:", ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    if dry_run:
        print("\nYe sirf dry run tha, kuch nahi badla. Fix ke liye dry_run 0 karke chalayein.")
    return counts
