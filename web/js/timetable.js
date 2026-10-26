/* ============================================================
 * timetable.js —— 员工课表（周视图）
 * - 按周查看全部班级课次，可按班级 / 教师筛选
 * - 点击课次编辑主题与状态；「补齐课表」按班级排课规则生成课次
 * 数据来源：/api/v1/sessions（员工）
 * ============================================================ */

const TT_DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

let weekStart = null;
let ttSessions = [];
let filterClass = '';
let filterTeacher = '';
let editingSession = null;
let canWriteTimetable = false;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('timetable');
  if (!user) return;
  canWriteTimetable = canManageAcademic(user);

  $('#tt-page-head').innerHTML = pageHead(
    '课表',
    canWriteTimetable
      ? '按周查看班级课次，点击课次可维护授课主题与状态'
      : '按周查看班级课次（只读）',
    ''
  );
  if (!canWriteTimetable) $('#tt-generate').style.display = 'none';
  fillTtFilters();
  weekStart = mondayOf(new Date());
  bindTtEvents();
  await loadWeek();
});

/* ---------- 日期工具 ---------- */

function fmtDate(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function mondayOf(d) {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const offset = (copy.getDay() + 6) % 7;   // 周一 = 0
  copy.setDate(copy.getDate() - offset);
  return copy;
}

function addDays(d, n) {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  copy.setDate(copy.getDate() + n);
  return copy;
}

/* ---------- 筛选 ---------- */

function fillTtFilters() {
  const classOpts = ['<option value="">全部班级</option>']
    .concat(DB.classes.map(c => `<option value="${c.id}">${esc(c.name)}</option>`)).join('');
  const teacherOpts = ['<option value="">全部教师</option>']
    .concat(DB.teachers.map(t => `<option value="${t.id}">${esc(t.name)}</option>`)).join('');
  $('#tt-class').innerHTML = classOpts;
  $('#tt-teacher').innerHTML = teacherOpts;
}

function bindTtEvents() {
  $('#tt-prev').addEventListener('click', () => { weekStart = addDays(weekStart, -7); loadWeek(); });
  $('#tt-next').addEventListener('click', () => { weekStart = addDays(weekStart, 7); loadWeek(); });
  $('#tt-today').addEventListener('click', () => { weekStart = mondayOf(new Date()); loadWeek(); });
  $('#tt-class').addEventListener('change', e => { filterClass = e.target.value; renderWeek(); });
  $('#tt-teacher').addEventListener('change', e => { filterTeacher = e.target.value; renderWeek(); });
  $('#tt-generate').addEventListener('click', openGenerateModal);
  $('#tt-week').addEventListener('click', e => {
    const card = e.target.closest('[data-session]');
    if (!card) return;
    const session = ttSessions.find(s => s.id === card.dataset.session);
    if (!session) return;
    if (canWriteTimetable) openSessionEditor(session);
    else openSessionView(session);
  });
}

/* ---------- 数据 ---------- */

async function loadWeek() {
  const start = fmtDate(weekStart);
  const end = fmtDate(addDays(weekStart, 6));
  $('#tt-range').textContent = `${start} ~ ${end}`;
  try {
    ttSessions = await api.sessions(start, end);
  } catch (e) {
    ttSessions = [];
    showToast(e.message, 'error');
  }
  renderWeek();
}

function filteredSessions() {
  return ttSessions.filter(s =>
    (!filterClass || s.classId === filterClass) &&
    (!filterTeacher || s.teacherId === filterTeacher)
  );
}

/* ---------- 周视图 ---------- */

function renderWeek() {
  const list = filteredSessions();
  const todayStr = fmtDate(new Date());
  const cols = [];
  for (let i = 0; i < 7; i++) {
    const day = addDays(weekStart, i);
    const key = fmtDate(day);
    const daySessions = list.filter(s => (s.date || s.sessionDate) === key)
      .sort((a, b) => (a.startTime || '').localeCompare(b.startTime || ''));
    const cards = daySessions.map(sessionCard).join('') || '<div class="tt-empty">无课次</div>';
    cols.push(`
      <div class="tt-day ${key === todayStr ? 'today' : ''}">
        <div class="tt-day-head">
          <span>${TT_DAY_NAMES[i]}</span><b>${key.slice(5)}</b>
        </div>
        <div class="tt-day-body">${cards}</div>
      </div>`);
  }
  $('#tt-week').innerHTML = cols.join('');
}

function sessionCard(s) {
  const topic = s.topic ? esc(s.topic) : '<span style="color:var(--muted)">未填写主题</span>';
  const status = s.displayStatus || s.status || '待上课';
  const cls = status === '已取消' ? 'cancelled' : status === '已上课' ? 'done' : '';
  return `
    <div class="tt-session ${cls}" data-session="${s.id}" title="点击维护课次">
      <div class="tt-time">${esc(s.startTime)}-${esc(s.endTime)}</div>
      <div class="tt-name">${esc(s.className)}</div>
      <div class="tt-sub">${esc(s.teacherName || '')}${s.classroom ? ' · ' + esc(s.classroom) : ''}</div>
      <div class="tt-sub">${topic}</div>
      <div class="tt-foot">${badge(status)}${s.attendanceSaved ? '<span class="tt-hw">已考勤</span>' : ''}</div>
    </div>`;
}

/* ---------- 课次编辑 ---------- */

function openSessionEditor(s) {
  editingSession = s;
  const body = `
    <div class="form-grid">
      <div class="form-item full">
        <label>课次信息</label>
        <div class="input" style="height:auto;background:var(--bg-soft)">
          ${esc(s.date)} ${esc(s.startTime)}-${esc(s.endTime)} · ${esc(s.className)} · ${esc(s.teacherName || '')}${s.classroom ? ' · ' + esc(s.classroom) : ''}
        </div>
      </div>
      <div class="form-item full">
        <label>授课主题</label>
        <input class="input" id="ts-topic" maxlength="128" value="${esc(s.topic || '')}" placeholder="如：第 5 讲 循环结构">
      </div>
      <div class="form-item">
        <label>课次状态</label>
        <select class="select" id="ts-status">
          ${['待上课', '已上课', '已取消'].map(st => `<option ${st === s.status ? 'selected' : ''}>${st}</option>`).join('')}
        </select>
      </div>
    </div>`;
  openTtModal('维护课次', body, '保 存', async () => {
    const ok = await apiOk(
      () => api.updateSession(s.id, { topic: $('#ts-topic').value.trim(), status: $('#ts-status').value }),
      '课次已更新'
    );
    if (!ok) return false;
    await loadWeek();
    return true;
  });
}

function openSessionView(s) {
  const att = s.attendance || {};
  const body = `
    <div class="tt-detail">
      <div><div class="k">班级</div><div class="v">${esc(s.className)}</div></div>
      <div><div class="k">课程</div><div class="v">${esc(s.courseName || '–')}</div></div>
      <div><div class="k">日期</div><div class="v">${esc(s.date)}</div></div>
      <div><div class="k">时间</div><div class="v">${esc(s.startTime)}-${esc(s.endTime)}</div></div>
      <div><div class="k">教师</div><div class="v">${esc(s.teacherName || '–')}</div></div>
      <div><div class="k">教室</div><div class="v">${esc(s.classroom || '–')}</div></div>
      <div><div class="k">状态</div><div class="v">${badge(s.displayStatus || s.status)}</div></div>
      <div><div class="k">授课主题</div><div class="v">${esc(s.topic || '未填写')}</div></div>
      <div><div class="k">考勤</div><div class="v">${s.attendanceSaved ? `出勤 ${att['出勤']} / 迟到 ${att['迟到']} / 请假 ${att['请假']} / 缺勤 ${att['缺勤']}` : '尚未录入'}</div></div>
    </div>`;
  openTtModal('课次详情（只读）', body, '', async () => true);
}

/* ---------- 补齐课表 ---------- */

function openGenerateModal() {
  const options = DB.classes.map(c =>
    `<option value="${c.id}">${esc(c.name)}（${esc(c.schedule || '未设置上课时间')}）</option>`
  ).join('');
  const body = `
    <div class="form-grid">
      <div class="form-item full">
        <label>班级<span class="req">*</span></label>
        <select class="select" id="tg-class">${options || '<option value="">暂无班级</option>'}</select>
      </div>
      <div class="form-item">
        <label>从哪天开始生成</label>
        <input class="input" type="date" id="tg-from" value="${todayStr()}">
      </div>
      <div class="form-item full">
        <div class="td-sub">按班级「上课时间」（如 周六 09:00-10:30）与开班/结课日期展开课次；已存在的课次不会重复生成。</div>
      </div>
    </div>`;
  openTtModal('补齐课表', body, '生 成', async () => {
    const classId = $('#tg-class').value;
    if (!classId) { showToast('请先创建班级', 'error'); return false; }
    const rec = await apiOk(() => api.generateSessions(classId, $('#tg-from').value), '');
    if (!rec) return false;
    showToast(`已生成 ${rec.created} 个课次`);
    await loadWeek();
    return true;
  });
}

/* ---------- 弹窗 ---------- */

function openTtModal(title, bodyHtml, submitText, onSubmit) {
  $('#ttm-title').textContent = title;
  $('#ttm-body').innerHTML = bodyHtml;
  const btn = $('#ttm-submit');
  btn.textContent = submitText || '';
  btn.style.display = submitText ? '' : 'none';
  btn.onclick = async () => {
    btn.disabled = true;
    try {
      const keep = await onSubmit();
      if (keep !== false) closeModal('tt-modal');
    } finally {
      btn.disabled = false;
    }
  };
  openModal('tt-modal');
}
