# -*- coding: utf-8 -*-
"""
applist.py
Employee Task Scheduler - Hệ thống phân công công việc nhân viên
"""

import os
from datetime import datetime, timedelta, date

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "employee-task-scheduler-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "scheduler.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

CA_LAM_VIEC = {"Sáng": "07:30 - 11:30", "Chiều": "13:00 - 17:00"}
THU_TRONG_TUAN = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"]
DO_UU_TIEN_LIST = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
TRINH_DO_LIST = ["Cơ bản", "Khá", "Thành thạo", "Chuyên gia"]

VI_TRI_MAP = {
    "Kỹ thuật": ["Kỹ sư", "Kỹ thuật viên", "Trưởng phòng Kỹ thuật", "Phó phòng Kỹ thuật"],
    "Kinh doanh": ["Nhân viên Kinh doanh", "Trưởng phòng Kinh doanh", "Chuyên viên Kinh doanh"],
    "Kế toán": ["Kế toán viên", "Kế toán trưởng", "Kế toán tổng hợp"],
    "Hành chính": ["Nhân viên Hành chính", "Trưởng phòng Hành chính", "Thư ký"],
    "IT Support": ["Nhân viên IT", "Trưởng nhóm IT", "Chuyên viên IT"],
    "Nhân sự": ["Nhân viên Nhân sự", "Trưởng phòng Nhân sự", "Chuyên viên Nhân sự"],
    "Marketing": ["Nhân viên Marketing", "Trưởng phòng Marketing", "Chuyên viên Marketing"],
}


class Employee(db.Model):
    __tablename__ = "employee"
    id = db.Column(db.Integer, primary_key=True)
    ma_nv = db.Column(db.String(20), unique=True, nullable=False)
    ho_ten = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    bo_phan = db.Column(db.String(80))
    vi_tri = db.Column(db.String(80))
    trinh_do = db.Column(db.String(20), default="Cơ bản")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    schedules = db.relationship("Schedule", backref="employee", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "ma_nv": self.ma_nv,
            "ho_ten": self.ho_ten,
            "email": self.email,
            "bo_phan": self.bo_phan,
            "vi_tri": self.vi_tri,
            "trinh_do": self.trinh_do,
        }


class Task(db.Model):
    __tablename__ = "task"
    id = db.Column(db.Integer, primary_key=True)
    ma_cv = db.Column(db.String(20), unique=True, nullable=False)
    ten_cv = db.Column(db.String(150), nullable=False)
    ghi_chu = db.Column(db.Text)
    do_uu_tien = db.Column(db.String(20), default="Trung bình")
    ngay_gio = db.Column(db.DateTime)
    bo_phan = db.Column(db.String(80))
    so_luong_nv = db.Column(db.Integer, default=1)
    thoi_luong = db.Column(db.Float, default=1.0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    schedules = db.relationship("Schedule", backref="task", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "ma_cv": self.ma_cv,
            "ten_cv": self.ten_cv,
            "ghi_chu": self.ghi_chu,
            "do_uu_tien": self.do_uu_tien,
            "ngay_gio": self.ngay_gio.strftime("%Y-%m-%d") if self.ngay_gio else "",
            "bo_phan": self.bo_phan,
            "so_luong_nv": self.so_luong_nv,
            "thoi_luong": self.thoi_luong,
        }


class Schedule(db.Model):
    __tablename__ = "schedule"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    ngay_lam_viec = db.Column(db.Date, nullable=False)
    ca = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("employee_id", "ngay_lam_viec", "ca", name="uq_emp_day_ca"),)


class Page(db.Model):
    __tablename__ = "page"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    tieu_de = db.Column(db.String(200), nullable=False)
    noi_dung = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def parse_date(value, default=None):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default or date.today()


def get_week_start(d):
    return d - timedelta(days=d.weekday())


def check_trung_ca(employee_id, ngay_lam_viec, ca, exclude_id=None):
    query = Schedule.query.filter_by(employee_id=employee_id, ngay_lam_viec=ngay_lam_viec, ca=ca)
    if exclude_id:
        query = query.filter(Schedule.id != exclude_id)
    return query.first()


DO_UU_TIEN_COLORS = {
    "Khẩn cấp": "#ef4444",
    "Cao": "#f59e0b",
    "Trung bình": "#3b82f6",
    "Thấp": "#94a3b8",
}

DO_UU_TIEN_BG = {
    "Khẩn cấp": "rgba(239,68,68,0.18)",
    "Cao": "rgba(245,158,11,0.18)",
    "Trung bình": "rgba(59,130,246,0.18)",
    "Thấp": "rgba(148,163,184,0.18)",
}

TRINH_DO_ORDER = {"Cơ bản": 1, "Khá": 2, "Thành thạo": 3, "Chuyên gia": 4}


@app.route("/")
def index():
    return redirect(url_for("lich_trinh"))


@app.route("/lich-trinh")
def lich_trinh():
    start_param = request.args.get("start")
    if start_param:
        anchor = parse_date(start_param)
    else:
        anchor = date.today()
    week_start = get_week_start(anchor)
    week_dates = [week_start + timedelta(days=i) for i in range(6)]

    schedules = (
        db.session.query(Schedule, Task)
        .join(Task, Schedule.task_id == Task.id)
        .filter(Schedule.ngay_lam_viec.in_(week_dates), Task.completed == False)
        .order_by(Schedule.ngay_lam_viec, Schedule.ca)
        .all()
    )
    timetable = {}
    for s, task in schedules:
        key = (s.ngay_lam_viec, s.ca)
        if key not in timetable:
            timetable[key] = {}
        timetable[key][task.id] = task

    seen = set()
    week_tasks = []
    for s, task in schedules:
        if task.id not in seen:
            seen.add(task.id)
            week_tasks.append({"task": task, "date": s.ngay_lam_viec, "ca": s.ca})

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    total_employees = Employee.query.count()

    return render_template(
        "lich_trinh.html",
        week_start=week_start,
        week_dates=week_dates,
        thu_list=THU_TRONG_TUAN,
        timetable=timetable,
        week_tasks=week_tasks,
        prev_week=prev_week.strftime("%Y-%m-%d"),
        next_week=next_week.strftime("%Y-%m-%d"),
        today_str=date.today().strftime("%Y-%m-%d"),
        total_employees=total_employees,
        do_uu_tien_colors=DO_UU_TIEN_COLORS,
        do_uu_tien_bg=DO_UU_TIEN_BG,
    )


@app.route("/employees")
def employees_page():
    q = request.args.get("q", "").strip()
    query = Employee.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Employee.ma_nv.ilike(like),
                Employee.ho_ten.ilike(like),
                Employee.email.ilike(like),
                Employee.bo_phan.ilike(like),
                Employee.vi_tri.ilike(like),
                Employee.trinh_do.ilike(like),
            )
        )
    employees = query.order_by(Employee.id.desc()).all()
    return render_template("employees.html", employees=employees, q=q, vi_tri_map=VI_TRI_MAP, trinh_do_list=TRINH_DO_LIST)


@app.route("/employees/add", methods=["POST"])
def employee_add():
    ma_nv = request.form.get("ma_nv", "").strip()
    ho_ten = request.form.get("ho_ten", "").strip()
    email = request.form.get("email", "").strip()
    bo_phan = request.form.get("bo_phan", "").strip()
    vi_tri = request.form.get("vi_tri", "").strip()
    trinh_do = request.form.get("trinh_do", "Cơ bản")
    if not ma_nv or not ho_ten:
        flash("Mã nhân viên và Họ tên là bắt buộc.", "danger")
        return redirect(url_for("employees_page"))
    if Employee.query.filter_by(ma_nv=ma_nv).first():
        flash(f"Mã nhân viên '{ma_nv}' đã tồn tại.", "danger")
        return redirect(url_for("employees_page"))
    emp = Employee(ma_nv=ma_nv, ho_ten=ho_ten, email=email, bo_phan=bo_phan, vi_tri=vi_tri, trinh_do=trinh_do)
    db.session.add(emp)
    db.session.commit()
    flash(f"Đã thêm nhân viên '{ho_ten}' thành công.", "success")
    return redirect(url_for("employees_page"))


@app.route("/employees/edit/<int:emp_id>", methods=["POST"])
def employee_edit(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    ma_nv = request.form.get("ma_nv", "").strip()
    trung = Employee.query.filter(Employee.ma_nv == ma_nv, Employee.id != emp_id).first()
    if trung:
        flash(f"Mã nhân viên '{ma_nv}' đã được sử dụng.", "danger")
        return redirect(url_for("employees_page"))
    emp.ma_nv = ma_nv
    emp.ho_ten = request.form.get("ho_ten", "").strip()
    emp.email = request.form.get("email", "").strip()
    emp.bo_phan = request.form.get("bo_phan", "").strip()
    emp.vi_tri = request.form.get("vi_tri", "").strip()
    emp.trinh_do = request.form.get("trinh_do", "Cơ bản")
    db.session.commit()
    flash("Đã cập nhật thông tin nhân viên.", "success")
    return redirect(url_for("employees_page"))


@app.route("/employees/delete/<int:emp_id>", methods=["POST"])
def employee_delete(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    db.session.delete(emp)
    db.session.commit()
    flash(f"Đã xóa nhân viên '{emp.ho_ten}'.", "success")
    return redirect(url_for("employees_page"))


@app.route("/tasks")
def tasks_page():
    q = request.args.get("q", "").strip()
    detail_id = request.args.get("detail", type=int)
    query = Task.query.filter_by(completed=False)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Task.ma_cv.ilike(like), Task.ten_cv.ilike(like), Task.ghi_chu.ilike(like)))
    tasks = query.order_by(Task.id.desc()).all()
    detail_task = None
    detail_assignments = []
    if detail_id:
        detail_task = Task.query.get(detail_id)
        if detail_task:
            detail_assignments = (
                db.session.query(Schedule, Employee)
                .join(Employee, Schedule.employee_id == Employee.id)
                .filter(Schedule.task_id == detail_id)
                .order_by(Schedule.ngay_lam_viec, Schedule.ca)
                .all()
            )
    return render_template(
        "tasks.html", tasks=tasks, q=q, do_uu_tien_list=DO_UU_TIEN_LIST,
        vi_tri_map=VI_TRI_MAP, trinh_do_list=TRINH_DO_LIST,
        do_uu_tien_colors=DO_UU_TIEN_COLORS, do_uu_tien_bg=DO_UU_TIEN_BG,
        detail_task=detail_task, detail_assignments=detail_assignments
    )


@app.route("/tasks/add", methods=["POST"])
def task_add():
    ma_cv = request.form.get("ma_cv", "").strip()
    ten_cv = request.form.get("ten_cv", "").strip()
    ghi_chu = request.form.get("ghi_chu", "").strip()
    do_uu_tien = request.form.get("do_uu_tien", "Trung bình")
    ngay_gio_str = request.form.get("ngay_gio", "").strip()
    bo_phan = request.form.get("bo_phan", "").strip()
    so_luong_nv = request.form.get("so_luong_nv", "1")
    thoi_luong = request.form.get("thoi_luong", "1")
    if not ma_cv or not ten_cv:
        flash("Mã công việc và Tên công việc là bắt buộc.", "danger")
        return redirect(url_for("tasks_page"))
    if Task.query.filter_by(ma_cv=ma_cv).first():
        flash(f"Mã công việc '{ma_cv}' đã tồn tại.", "danger")
        return redirect(url_for("tasks_page"))
    try:
        ngay_gio = datetime.strptime(ngay_gio_str, "%Y-%m-%d") if ngay_gio_str else None
    except ValueError:
        ngay_gio = None
    try:
        so_luong_nv_i = int(so_luong_nv)
    except ValueError:
        so_luong_nv_i = 1
    try:
        thoi_luong_f = float(thoi_luong)
    except ValueError:
        thoi_luong_f = 1.0
    task = Task(
        ma_cv=ma_cv, ten_cv=ten_cv, ghi_chu=ghi_chu,
        do_uu_tien=do_uu_tien, ngay_gio=ngay_gio,
        bo_phan=bo_phan, so_luong_nv=so_luong_nv_i,
        thoi_luong=thoi_luong_f,
    )
    db.session.add(task)
    db.session.commit()
    flash(f"Đã thêm công việc '{ten_cv}' thành công.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/edit/<int:task_id>", methods=["POST"])
def task_edit(task_id):
    task = Task.query.get_or_404(task_id)
    ma_cv = request.form.get("ma_cv", "").strip()
    trung = Task.query.filter(Task.ma_cv == ma_cv, Task.id != task_id).first()
    if trung:
        flash(f"Mã công việc '{ma_cv}' đã được sử dụng.", "danger")
        return redirect(url_for("tasks_page"))
    task.ma_cv = ma_cv
    task.ten_cv = request.form.get("ten_cv", "").strip()
    task.ghi_chu = request.form.get("ghi_chu", "").strip()
    task.do_uu_tien = request.form.get("do_uu_tien", "Trung bình")
    ngay_gio_str = request.form.get("ngay_gio", "").strip()
    try:
        task.ngay_gio = datetime.strptime(ngay_gio_str, "%Y-%m-%d") if ngay_gio_str else None
    except ValueError:
        pass
    task.bo_phan = request.form.get("bo_phan", "").strip()
    try:
        task.so_luong_nv = int(request.form.get("so_luong_nv", "1"))
    except ValueError:
        task.so_luong_nv = 1
    try:
        task.thoi_luong = float(request.form.get("thoi_luong", "1"))
    except ValueError:
        task.thoi_luong = 1.0
    db.session.commit()
    flash("Đã cập nhật công việc.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/delete/<int:task_id>", methods=["POST"])
def task_delete(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash(f"Đã xóa công việc '{task.ten_cv}'.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/complete/<int:task_id>", methods=["POST"])
def task_complete(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = True
    task.completed_at = datetime.utcnow()
    db.session.commit()
    flash(f"Đã đánh dấu công việc '{task.ten_cv}' hoàn thành.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/history")
def task_history():
    q = request.args.get("q", "").strip()
    detail_id = request.args.get("detail", type=int)
    query = Task.query.filter_by(completed=True)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Task.ma_cv.ilike(like), Task.ten_cv.ilike(like), Task.ghi_chu.ilike(like)))
    tasks = query.order_by(Task.completed_at.desc()).all()
    detail_task = None
    detail_assignments = []
    if detail_id:
        detail_task = Task.query.get(detail_id)
        if detail_task:
            detail_assignments = (
                db.session.query(Schedule, Employee)
                .join(Employee, Schedule.employee_id == Employee.id)
                .filter(Schedule.task_id == detail_id)
                .order_by(Schedule.ngay_lam_viec, Schedule.ca)
                .all()
            )
    return render_template(
        "task_history.html", tasks=tasks, q=q, do_uu_tien_list=DO_UU_TIEN_LIST,
        vi_tri_map=VI_TRI_MAP, trinh_do_list=TRINH_DO_LIST,
        do_uu_tien_colors=DO_UU_TIEN_COLORS, do_uu_tien_bg=DO_UU_TIEN_BG,
        detail_task=detail_task, detail_assignments=detail_assignments
    )


@app.route("/tasks/assign")
def task_assign():
    tasks = Task.query.filter_by(completed=False).order_by(Task.id.desc()).all()
    employees = Employee.query.order_by(Employee.ho_ten).all()
    recent = (
        db.session.query(Schedule, Employee, Task)
        .join(Employee, Schedule.employee_id == Employee.id)
        .join(Task, Schedule.task_id == Task.id)
        .order_by(Schedule.id.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "task_assign.html",
        tasks=tasks, employees=employees, recent=recent,
        today_str=date.today().strftime("%Y-%m-%d"),
        do_uu_tien_colors=DO_UU_TIEN_COLORS,
        do_uu_tien_bg=DO_UU_TIEN_BG,
        trinh_do_list=TRINH_DO_LIST,
        vi_tri_map=VI_TRI_MAP,
    )


@app.route("/tasks/assign/get-employees", methods=["POST"])
def assign_get_employees():
    data = request.get_json()
    task_id = data.get("task_id")
    vi_tri_filter = data.get("vi_tri", "")
    trinh_do_filter = data.get("trinh_do", "")
    ca = data.get("ca", "Sáng")
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    query = Employee.query
    if task.bo_phan:
        query = query.filter(Employee.bo_phan == task.bo_phan)
    if vi_tri_filter:
        query = query.filter(Employee.vi_tri == vi_tri_filter)
    if trinh_do_filter:
        query = query.filter(Employee.trinh_do == trinh_do_filter)

    employees = query.all()

    result = []
    task_date = task.ngay_gio.date() if task.ngay_gio else None
    for emp in employees:
        available = True
        msg = ""
        if task_date:
            existing = check_trung_ca(emp.id, task_date, ca)
            if existing:
                available = False
                msg = f"Đã có lịch '{existing.task.ten_cv}' ca {ca}"
        result.append({
            "id": emp.id,
            "ma_nv": emp.ma_nv,
            "ho_ten": emp.ho_ten,
            "email": emp.email,
            "bo_phan": emp.bo_phan,
            "vi_tri": emp.vi_tri,
            "trinh_do": emp.trinh_do,
            "available": available,
            "msg": msg,
        })
    return jsonify(result)


@app.route("/tasks/assign/ai-suggest", methods=["POST"])
def assign_ai_suggest():
    data = request.get_json()
    task_id = data.get("task_id")
    ca = data.get("ca", "Sáng")
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    query = Employee.query
    if task.bo_phan:
        query = query.filter(Employee.bo_phan == task.bo_phan)
    employees = query.all()

    task_date = task.ngay_gio.date() if task.ngay_gio else None
    scored = []
    for emp in employees:
        score = 0
        if emp.trinh_do == "Chuyên gia":
            score += 40
        elif emp.trinh_do == "Thành thạo":
            score += 30
        elif emp.trinh_do == "Khá":
            score += 20
        elif emp.trinh_do == "Cơ bản":
            score += 10

        available = True
        if task_date:
            existing = check_trung_ca(emp.id, task_date, ca)
            if existing:
                available = False
                score -= 100

        total_assigned = Schedule.query.filter_by(employee_id=emp.id).count()
        score -= total_assigned * 2

        scored.append({
            "id": emp.id,
            "ma_nv": emp.ma_nv,
            "ho_ten": emp.ho_ten,
            "bo_phan": emp.bo_phan,
            "vi_tri": emp.vi_tri,
            "trinh_do": emp.trinh_do,
            "score": max(score, 0) if available else 0,
            "available": available,
            "recommended": available and score > 20,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(scored[:task.so_luong_nv * 3])


@app.route("/tasks/assign/save", methods=["POST"])
def assign_save():
    data = request.get_json()
    task_id = data.get("task_id")
    employee_ids = data.get("employee_ids", [])
    ca = data.get("ca", "Sáng")
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if not task.ngay_gio:
        return jsonify({"error": "Task has no date set"}), 400

    ngay = task.ngay_gio.date()
    assigned = []
    errors = []
    for eid in employee_ids:
        trung = check_trung_ca(eid, ngay, ca)
        if trung:
            emp = Employee.query.get(eid)
            errors.append(f"Nhân viên '{emp.ho_ten}' đã có lịch ca {ca}")
            continue
        sch = Schedule(employee_id=eid, task_id=task_id, ngay_lam_viec=ngay, ca=ca)
        db.session.add(sch)
        assigned.append(eid)
    db.session.commit()
    return jsonify({"assigned": len(assigned), "errors": errors})


@app.route("/schedule/delete/<int:sch_id>", methods=["POST"])
def schedule_delete(sch_id):
    sch = Schedule.query.get_or_404(sch_id)
    db.session.delete(sch)
    db.session.commit()
    flash("Đã xóa lịch phân công.", "success")
    return redirect(request.referrer or url_for("lich_trinh"))


@app.route("/reports")
def reports_page():
    employees = Employee.query.order_by(Employee.ho_ten).all()
    stats = []
    for emp in employees:
        count = Schedule.query.filter_by(employee_id=emp.id).count()
        total_hours = (
            db.session.query(db.func.sum(Task.thoi_luong))
            .join(Schedule, Schedule.task_id == Task.id)
            .filter(Schedule.employee_id == emp.id)
            .scalar() or 0
        )
        stats.append({"employee": emp, "so_luong_ca": count, "tong_gio": round(total_hours, 1)})
    stats.sort(key=lambda x: x["so_luong_ca"], reverse=True)
    tong_lich = Schedule.query.count()
    tong_nv_co_lich = db.session.query(Schedule.employee_id).distinct().count()
    bo_phan_stats = {}
    for emp in employees:
        bp = emp.bo_phan or "Chưa phân loại"
        bo_phan_stats[bp] = bo_phan_stats.get(bp, 0) + Schedule.query.filter_by(employee_id=emp.id).count()
    return render_template("reports.html", stats=stats, tong_lich=tong_lich, tong_nv_co_lich=tong_nv_co_lich, bo_phan_stats=bo_phan_stats)


@app.route("/api/check_conflict")
def api_check_conflict():
    employee_id = request.args.get("employee_id", type=int)
    ngay_str = request.args.get("ngay_lam_viec")
    ca = request.args.get("ca")
    if not employee_id or not ngay_str or not ca:
        return jsonify({"conflict": False})
    ngay = parse_date(ngay_str)
    trung = check_trung_ca(employee_id, ngay, ca)
    if trung:
        return jsonify({"conflict": True, "task_name": trung.task.ten_cv})
    return jsonify({"conflict": False})


@app.route("/p/<path:slug>")
def dynamic_page(slug):
    page = Page.query.filter_by(slug=slug).first()
    if not page:
        return "Trang không tồn tại (404)", 404
    return render_template("dynamic_page.html", page=page)


@app.route("/pages/add", methods=["POST"])
def page_add():
    slug = request.form.get("slug", "").strip()
    tieu_de = request.form.get("tieu_de", "").strip()
    noi_dung = request.form.get("noi_dung", "").strip()
    if not slug or not tieu_de:
        flash("Slug và Tiêu đề là bắt buộc.", "danger")
        return redirect(url_for("lich_trinh"))
    if Page.query.filter_by(slug=slug).first():
        flash(f"Đường dẫn '/p/{slug}' đã tồn tại!", "danger")
        return redirect(url_for("lich_trinh"))
    new_page = Page(slug=slug, tieu_de=tieu_de, noi_dung=noi_dung)
    db.session.add(new_page)
    db.session.commit()
    flash(f"Đã tạo đường dẫn mới: /p/{slug}", "success")
    return redirect(url_for("dynamic_page", slug=slug))


def seed_data():
    pass


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
