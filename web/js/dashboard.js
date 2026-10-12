/* ============================================================
 * dashboard.js —— 工作台：统计 / 图表 / 最近缴费 / 快捷入口
 * 数据来源：/api/v1/dashboard/* 四个专用端点（无需全量缓存）
 * ============================================================ */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('dashboard', false);
  if (!user) return;

  renderWelcome(user);
  const [summary, heat, upcoming, recent] = await Promise.all([
    apiOk(() => api.dashboard.summary(), ''),
    apiOk(() => api.dashboard.heat(), ''),
    apiOk(() => api.dashboard.recentClasses(), ''),
    apiOk(() => api.dashboard.recentPayments(), ''),
  ]);
  if (summary) renderStats(summary);
  if (heat) renderBarChart(heat);
  if (upcoming) renderUpcoming(upcoming);
  if (recent) renderRecentPayments(recent);
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
function renderStats(s) {
  $('#stat-students').textContent = s.students.active;
  $('#stat-students-extra').textContent = `累计学员 ${s.students.total} 人`;
  $('#stat-teachers').textContent = s.teachers.active;
  $('#stat-teachers-extra').textContent = `共 ${s.teachers.total} 名教师`;
  $('#stat-classes').textContent = s.classes.running;
  $('#stat-classes-extra').textContent = s.classes.notStarted ? `另有 ${s.classes.notStarted} 个班级待开班` : '全部班级正常运行';
  $('#stat-income').textContent = money(s.income.month);
  $('#stat-income-extra').textContent = `待确认 ${money(s.income.pending)} · 累计 ${money(s.income.total)}`;
}

/* ---------- 班级报名热度（纯 CSS 条形图） ---------- */
function renderBarChart(list) {
  const max = Math.max(...list.map(c => c.enrolled), 1);
  $('#bar-chart').innerHTML = list.length ? list.map(c => `
    <div class="bar-row">
      <div class="bar-name" title="${esc(c.name)}">${esc(c.name)}</div>
      <div class="bar-track"><span class="bar-fill" style="--w:${(c.enrolled / max).toFixed(3)}"></span></div>
      <div class="bar-value">${c.enrolled}<span style="color:var(--muted);font-weight:400">/${c.capacity}</span></div>
    </div>`).join('') : '<div style="color:var(--muted);text-align:center;padding:20px;">暂无进行中的班级</div>';
}

/* ---------- 近期开班 ---------- */
function renderUpcoming(list) {
  $('#upcoming-classes').innerHTML = list.length ? list.map(c => `
    <div class="overview-item">
      ${avatarHtml((c.courseName || '').slice(0, 2))}
      <div class="overview-main">
        <div class="overview-name">${esc(c.name)}</div>
        <div class="overview-sub">${esc(c.courseName)} · ${esc(c.teacherName)} · ${esc(c.schedule)}</div>
      </div>
      <div style="text-align:right">
        ${badge(c.status)}
        <div class="overview-sub" style="margin-top:4px">${esc(c.startDate)} 开班</div>
      </div>
    </div>`).join('') : '<div style="color:var(--muted);text-align:center;padding:20px;">暂无排班</div>';
}

/* ---------- 最近缴费 ---------- */
function renderRecentPayments(list) {
  $('#recent-payments').innerHTML = list.length ? list.map(p => `
    <tr>
      <td class="td-sub">${esc(p.id)}</td>
      <td style="font-weight:600">${esc(p.studentName)}</td>
      <td><div>${esc(p.className)}</div><div class="td-sub">${esc(p.courseName)}</div></td>
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
