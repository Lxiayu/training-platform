/* ============================================================
 * dashboard.js —— 工作台：统计 / 图表 / 最近缴费 / 快捷入口
 * ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const user = renderLayout('dashboard');
  if (!user) return;
  renderWelcome(user);
  renderStats();
  renderBarChart();
  renderUpcoming();
  renderRecentPayments();
  renderQuickGrid(user);
});

/* ---------- 欢迎横幅 ---------- */
function renderWelcome(user) {
  const h = new Date().getHours();
  const hello = h < 6 ? '凌晨好' : h < 9 ? '早上好' : h < 12 ? '上午好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好';
  const dateStr = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
  $('#welcome-title').textContent = `${hello}，${user.name}！`;
  $('#welcome-sub').textContent = `今天是 ${dateStr}，祝您工作顺利。`;
}

/* ---------- 统计卡片 ---------- */
function renderStats() {
  const students = DB.students.filter(s => s.status === '在读').length;
  const totalStudents = DB.students.length;
  const teachers = DB.teachers.filter(t => t.status === '在职').length;
  const runningClasses = DB.classes.filter(c => c.status === '进行中').length;
  const notStarted = DB.classes.filter(c => c.status === '未开班').length;

  const now = new Date();
  const ym = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
  const paid = DB.payments.filter(p => p.status === '已支付' && p.date.startsWith(ym));
  const pending = DB.payments.filter(p => p.status === '待确认');
  const monthIncome = paid.reduce((s, p) => s + p.amount, 0);
  const totalIncome = DB.payments.filter(p => p.status === '已支付').reduce((s, p) => s + p.amount, 0);

  $('#stat-students').textContent = students;
  $('#stat-students-extra').textContent = `累计学员 ${totalStudents} 人`;
  $('#stat-teachers').textContent = teachers;
  $('#stat-teachers-extra').textContent = `共 ${DB.teachers.length} 名教师`;
  $('#stat-classes').textContent = runningClasses;
  $('#stat-classes-extra').textContent = notStarted ? `另有 ${notStarted} 个班级待开班` : '全部班级正常运行';
  $('#stat-income').textContent = money(monthIncome);
  $('#stat-income-extra').textContent = `待确认 ${money(pending.reduce((s, p) => s + p.amount, 0))} · 累计 ${money(totalIncome)}`;
}

/* ---------- 班级报名热度（纯 CSS 条形图） ---------- */
function renderBarChart() {
  const list = DB.classes
    .filter(c => c.status === '进行中')
    .map(c => ({ ...c, enrolled: classEnrolled(c.id) }))
    .sort((a, b) => b.enrolled - a.enrolled);
  const max = Math.max(...list.map(c => c.enrolled), 1);

  $('#bar-chart').innerHTML = list.length ? list.map(c => `
    <div class="bar-row">
      <div class="bar-name" title="${esc(c.name)}">${esc(c.name)}</div>
      <div class="bar-track"><span class="bar-fill" style="width:${Math.round(c.enrolled / max * 100)}%"></span></div>
      <div class="bar-value">${c.enrolled}<span style="color:var(--muted);font-weight:400">/${c.capacity}</span></div>
    </div>`).join('') : '<div style="color:var(--muted);text-align:center;padding:20px;">暂无进行中的班级</div>';
}

/* ---------- 近期开班 ---------- */
function renderUpcoming() {
  const list = [...DB.classes]
    .filter(c => c.status !== '已结课')
    .sort((a, b) => a.startDate.localeCompare(b.startDate))
    .slice(0, 4);

  $('#upcoming-classes').innerHTML = list.length ? list.map(c => `
    <div class="overview-item">
      ${avatarHtml(courseName(c.courseId).slice(0, 2))}
      <div class="overview-main">
        <div class="overview-name">${esc(c.name)}</div>
        <div class="overview-sub">${esc(courseName(c.courseId))} · ${esc(teacherName(c.teacherId))} · ${esc(c.schedule)}</div>
      </div>
      <div style="text-align:right">
        ${badge(c.status)}
        <div class="overview-sub" style="margin-top:4px">${esc(c.startDate)} 开班</div>
      </div>
    </div>`).join('') : '<div style="color:var(--muted);text-align:center;padding:20px;">暂无排班</div>';
}

/* ---------- 最近缴费 ---------- */
function renderRecentPayments() {
  const list = [...DB.payments].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id)).slice(0, 6);
  $('#recent-payments').innerHTML = list.length ? list.map(p => `
    <tr>
      <td class="td-sub">${esc(p.id)}</td>
      <td style="font-weight:600">${esc(studentName(p.studentId))}</td>
      <td><div>${esc(className(p.classId))}</div><div class="td-sub">${esc(courseName((byId(DB.classes, p.classId) || {}).courseId))}</div></td>
      <td style="font-weight:600;color:var(--primary)">${money(p.amount)}</td>
      <td>${esc(p.method)}</td>
      <td class="td-sub">${esc(p.date)}</td>
      <td>${badge(p.status)}</td>
    </tr>`).join('') : emptyRow(7);
}

/* ---------- 快捷入口 ---------- */
function renderQuickGrid(user) {
  const colors = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316'];
  $('#quick-grid').innerHTML = NAV_GROUPS
    .flatMap(g => g.items.filter(i => i.key !== 'dashboard' && (!i.adminOnly || isAdmin(user))))
    .map((it, i) => `
      <a class="quick-item" href="${it.href}" style="color:${colors[i % colors.length]}">
        ${ICONS[it.icon]}<span style="color:var(--text)">${it.label}</span>
      </a>`).join('');
}
