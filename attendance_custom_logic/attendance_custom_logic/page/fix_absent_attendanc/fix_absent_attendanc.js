frappe.pages['fix-absent-attendanc'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Fix Incorrect Attendance',
		single_column: true
	});

	// Max days allowed in one run (inclusive). Keep this in sync with the
	// server-side check in run_fix_absent_attendance() - the server check
	// is the real guard, this is just so the user gets instant feedback.
	var MAX_DAYS = 5;

	page.main.html(`
		<div class="fix-absent-attendance-form" style="max-width: 480px;">
			<div class="form-group">
				<label>From Date</label>
				<input type="date" class="form-control" data-fieldname="from_date">
			</div>
			<div class="form-group">
				<label>To Date</label>
				<input type="date" class="form-control" data-fieldname="to_date">
			</div>
			<div class="form-group">
				<label>Employee <span class="text-muted">(optional — blank = all employees)</span></label>
				<input type="text" class="form-control" data-fieldname="employee" placeholder="e.g. 1031">
			</div>
			<button class="btn btn-primary btn-run">Run</button>
			<p class="text-muted small" style="margin-top: 8px;">
				Server load na badhe is liye ek waqt mein zyada se zyada
				${MAX_DAYS} din ki range select ki ja sakti hai.
			</p>
		</div>
		<div class="fix-absent-attendance-results" style="margin-top: 24px;"></div>
	`);

	var $form = page.main.find('.fix-absent-attendance-form');
	var $results = page.main.find('.fix-absent-attendance-results');

	$form.find('.btn-run').on('click', function () {
		var from_date = $form.find('[data-fieldname="from_date"]').val();
		var to_date = $form.find('[data-fieldname="to_date"]').val();
		var employee = $form.find('[data-fieldname="employee"]').val();

		if (!from_date || !to_date) {
			frappe.msgprint(__('Please select both From Date and To Date.'));
			return;
		}

		var days_diff = frappe.datetime.get_diff(to_date, from_date);

		if (days_diff < 0) {
			frappe.msgprint(__('To Date, From Date se pehle nahi ho sakti.'));
			return;
		}

		if (days_diff > MAX_DAYS - 1) {
			frappe.msgprint(
				__('Zyada se zyada {0} din ki range select karein.', [MAX_DAYS])
			);
			return;
		}

		$results.html('');
		frappe.dom.freeze(__('Attendance process ho rahi hai... intezaar karein'));

		frappe.call({
			method: 'attendance_custom_logic.attendance_custom_logic.fix_absent_attendance.run_fix_absent_attendance',
			args: {
				from_date: from_date,
				to_date: to_date,
				employee: employee || null
			},
			callback: function (r) {
				frappe.dom.unfreeze();
				render_results(r.message || []);
			},
			error: function () {
				frappe.dom.unfreeze();
			}
		});
	});

	function render_results(rows) {
		if (!rows.length) {
			$results.html('<div class="text-muted">Is range mein koi Absent record nahi mila.</div>');
			return;
		}

		var updated = rows.filter(function (r) { return r.result === 'Updated'; }).length;
		var skipped = rows.length - updated;

		var html = `
			<div style="margin-bottom: 10px;">
				<b>${rows.length}</b> Absent record(s) check kiye —
				<span style="color: #2e7d32;"><b>${updated}</b> update hue</span>,
				<span style="color: #888;"><b>${skipped}</b> Absent hi rahe (koi checkin nahi mila)</span>
			</div>
			<div style="overflow-x: auto;">
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th>Employee</th>
						<th>Date</th>
						<th>Shift</th>
						<th>In Time</th>
						<th>Out Time</th>
						<th>Working Hrs</th>
						<th>Status</th>
						<th>Overtime</th>
						<th>Result</th>
					</tr>
				</thead>
				<tbody>
					${rows.map(function (row) {
						return `
						<tr>
							<td>${row.employee || ''}</td>
							<td>${row.date || ''}</td>
							<td>${row.shift || ''}</td>
							<td>${row.in_time || ''}</td>
							<td>${row.out_time || ''}</td>
							<td>${row.working_hours != null ? row.working_hours : ''}</td>
							<td>${row.status || 'Absent'}</td>
							<td>${row.overtime != null ? row.overtime : ''}</td>
							<td>${row.result}</td>
						</tr>`;
					}).join('')}
				</tbody>
			</table>
			</div>
		`;
		$results.html(html);
	}
};s