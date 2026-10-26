/* ============================================================
 * schedule.js —— 班级排课管理（规则维护 + 课次生成 / 取消 / 调课）
 * 依赖：api.js / common.js（页面为 classes.html）
 * 数据来源：/api/v1/classes/{code}/schedules、/classes/{code}/sessions
 * ============================================================ */

const SCH = { cls: null, canWrite: false, rules: [], sessions: [] };

function schIso(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function schAddDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return schIso(d);
}

function ensureScheduleModal() {
  if ($('#schedule-modal')) return;
  const wrap = document.createElement('div');
  wrap.className = 'modal';
  wrap.id = 'schedule-modal';
  wrap.innerHTML = `
    <div class="modal-mask"></div>
    <div class="modal-box modal-lg">
      <div class="modal-head">
        <h3 id="sch-title">排课管理</h3>
        <button class="modal-x" data-close><span data-icon="x"></span></button>
      </div>
      <div class="modal-body">
        <div class="section-label">排课规则</div>
        <div class="table-wrap"><table>
          <thead><tr><th>星期</th><th>时间</th><th>生效区间</th><th>教室</th><th style="width:90px">操作</th></tr></thead>
          <tbody id="sch-rules"></tbody>
        </table></div>
        <div class="form-grid" style="margin-top:12px" id="sch-rule-form">
          <div class="form-item">
            <label>星期<span class="req">*</span></label>
            <select class="select" id="sch-weekday">
              <option value="1">周一</option><option value="2">周二</option><option value="3">周三</option>
              <option value="4">周四</option><option value="5">周五</option><option value="6" selected>周六</option>
              <option value="7">周日</option>
            </select>
          </div>
          <div class="form-item">
            <label>教室</label>
            <input class="input" id="sch-room" placeholder="如：A101">
          </div>
          <div class="form-item">
            <label>开始时间<span class="req">*</span></label>
            <input class="input" type="time" id="sch-start" value="09:00">
          </div>
          <div class="form-item">
            <label>结束时间<span class="req">*</span></label>
            <input class="input" type="time" id="sch-end" value="10:30">
          </div>
          <div class="form-item">
            <label>生效日期</label>
            <input class="input" type="date" id="sch-from">
          </div>
          <div class="form-item">
            <label>失效日期</label>
            <input class="input" type="date" id="sch-to">
          </div>
        </div>
        <div class="toolbar" style="padding:12px 0">
          <button class="btn btn-outline" id="sch-add"><span data-icon="plus"></span> 添加规则</button>
          <div class="toolbar-spacer"></div>
          <span class="td-sub" id="sch-hint"></span>
        </div>
        <div class="section-label">课次（未来 8 周）</div>
        <div class="toolbar" style="padding:0 0 10px">
          <span class="td-sub" id="sch-range"></span>
          <div class="toolbar-spacer"></div>
          <button class="btn btn-ghost btn-sm" id="sch-gen">按规则补齐课次</button>
        </div>
        <div class="table-wrap"><table>
          <thead><tr><th>日期</th><th>星期</th><th>时间</th><th>教室</th><th>状态</th><th>作业</th><th style="width:130px">操作</th></tr></thead>
          <tbody id="sch-sessions"></tbody>
        </table></div>
      </div>
      <div class="modal-foot"><button class="btn btn-ghost" data-close>关 闭</button></div>
    </div>`;
  document.body.appendChild(wrap);
  mountIcons(wrap);

  $('#sch-add').addEventListener('click', addScheduleRule);
  $('#sch-rules').addEventListener('click', onRuleAction);
  $('#sch-sessions').addEventListener('click', onSessionAction);
  $('#sch-gen').addEventListener('click', generateSessions);
}

async function openScheduleManager(cls, canWrite) {
  ensureScheduleModal();
  SCH.cls = cls;
  SCH.canWrite = !!canWrite;
  $('#sch-title').textContent = `排课管理 · ${cls.name}`;
  $('#sch-hint').textContent = canWrite ? '' : '只读：仅超级管理员 / 教务可修改排课';
  $('#sch-add').style.display = canWrite ? '' : 'none';
  $('#sch-gen').style.display = canWrite ? '' : 'none';
  $('#sch-rule-form').style.display = canWrite ? '' : 'none';
  $('#sch-weekday').value = '6';
  $('#sch-room').value = cls.classroom || '';
  $('#sch-from').value = cls.startDate || todayStr();
  $('#sch-to').value = cls.endDate || '';
  openModal('schedule-modal');
  await reloadSchedule();
}

async function reloadSchedule() {
  if (!SCH.cls) return;
  const from = todayStr();
  const to = schAddDays(56);
  $('#sch-range').textContent = `${from} ~ ${to}`;
  try {
    const [rules, sessions] = await Promise.all([
      api.classSchedules(SCH.cls.id),
      api.classSessions(SCH.cls.id, { from, to }),
    ]);
    SCH.rules = rules || [];
    SCH.sessions = sessions || [];
  } catch (e) {
    SCH.rules = [];
    SCH.sessions = [];
    showToast(e.message, 'error');
  }
  renderScheduleRules();
  renderScheduleSessions();
}

function renderScheduleRules() {
  const canWrite = SCH.canWrite;
  $('#sch-rules').innerHTML = SCH.rules.length ? SCH.rules.map(r => `
    <tr>
      <td>${esc(r.weekdayLabel || '')}</td>
      <td class="td-sub">${esc(r.startTime)}-${esc(r.endTime)}</td>
      <td class="td-sub">${esc(r.effectiveFrom || '–')} ~ ${esc(r.effectiveTo || '长期')}</td>
      <td>${esc(r.classroom || '–')}</td>
      <td>${canWrite ? `<button class="btn-link danger" data-rule="${r.id}">${ICONS.trash}删除</button>` : ''}</td>
    </tr>`).join('') : emptyRow(5, '尚未配置排课规则，可解析班级「上课时间」自动补建');
}

function renderScheduleSessions() {
  const canWrite = SCH.canWrite;
  $('#sch-sessions').innerHTML = SCH.sessions.length ? SCH.sessions.map(s => `
    <tr>
      <td>${esc(s.sessionDate)}</td>
      <td class="td-sub">${esc(s.weekdayLabel || '')}</td>
      <td class="td-sub">${esc(s.startTime)}-${esc(s.endTime)}</td>
      <td>${esc(s.classroom || '–')}</td>
      <td>${badge(s.status)}${s.originalDate ? `<div class="td-sub">原 ${esc(s.originalDate)}</div>` : ''}</td>
      <td class="td-sub">${s.homeworkCount || 0}</td>
      <td class="td-actions">
        ${canWrite && s.status === '待上课' ? `
          <button class="btn-link" data-resched="${s.id}">${ICONS.refresh}调课</button>
          <button class="btn-link danger" data-cancel="${s.id}">${ICONS.x}取消</button>` : ''}
      </td>
    </tr>`).join('') : emptyRow(7, '该区间暂无课次，可点击「按规则补齐课次」');
}

async function addScheduleRule() {
  const payload = {
    weekday: Number($('#sch-weekday').value),
    startTime: $('#sch-start').value,
    endTime: $('#sch-end').value,
    effectiveFrom: $('#sch-from').value || null,
    effectiveTo: $('#sch-to').value || null,
    classroom: $('#sch-room').value.trim(),
  };
  if (!payload.startTime || !payload.endTime) { showToast('请填写上课时间', 'error'); return; }
  const ok = await apiOk(() => api.createSchedule(SCH.cls.id, payload), '排课规则已保存');
  if (!ok) return;
  await reloadSchedule();
  await hydrate();
}

function onRuleAction(e) {
  const btn = e.target.closest('button[data-rule]');
  if (!btn) return;
  const rule = SCH.rules.find(r => r.id === btn.dataset.rule);
  askConfirm('删除排课规则', `确定删除「${rule ? rule.weekdayLabel + ' ' + rule.startTime : ''}」这条规则吗？未来未上课的课次会同步回收。`, async () => {
    if (!await apiOk(() => api.deleteSchedule(btn.dataset.rule), '规则已删除')) return;
    await reloadSchedule();
    await hydrate();
  });
}

function onSessionAction(e) {
  const cancelBtn = e.target.closest('button[data-cancel]');
  if (cancelBtn) {
    const s = SCH.sessions.find(x => x.id === cancelBtn.dataset.cancel);
    askConfirm('取消课次', `确定取消 ${s ? s.sessionDate + ' ' + s.startTime : ''} 的课次吗？学员 / 家长课表会显示「已取消」。`, async () => {
      if (!await apiOk(() => api.cancelSession(cancelBtn.dataset.cancel), '课次已取消')) return;
      await reloadSchedule();
    });
    return;
  }
  const reschedBtn = e.target.closest('button[data-resched]');
  if (reschedBtn) {
    const s = SCH.sessions.find(x => x.id === reschedBtn.dataset.resched);
    if (s) openRescheduleForm(s);
  }
}

async function generateSessions() {
  const ok = await apiOk(() => api.generateSessions(SCH.cls.id, {}), '课次已补齐');
  if (!ok) return;
  await reloadSchedule();
}

function openRescheduleForm(s) {
  $('#reschedule-modal')?.remove();
  const wrap = document.createElement('div');
  wrap.className = 'modal';
  wrap.id = 'reschedule-modal';
  wrap.innerHTML = `
    <div class="modal-mask"></div>
    <div class="modal-box modal-sm">
      <div class="modal-head">
        <h3>调课 · ${esc(s.sessionDate)}</h3>
        <button class="modal-x" data-close><span data-icon="x"></span></button>
      </div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-item full">
            <label>新日期<span class="req">*</span></label>
            <input class="input" type="date" id="rs-date" value="${esc(s.sessionDate)}">
          </div>
          <div class="form-item">
            <label>开始时间</label>
            <input class="input" type="time" id="rs-start" value="${esc(s.startTime)}">
          </div>
          <div class="form-item">
            <label>结束时间</label>
            <input class="input" type="time" id="rs-end" value="${esc(s.endTime)}">
          </div>
          <div class="form-item full">
            <label>教室</label>
            <input class="input" id="rs-room" value="${esc(s.classroom || '')}">
          </div>
        </div>
        <div class="td-sub" style="margin-top:10px">原课次将保留并标记「已调课」，学员端显示「原时间 → 新时间」。</div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" data-close>取 消</button>
        <button class="btn" id="rs-ok">确认调课</button>
      </div>
    </div>`;
  document.body.appendChild(wrap);
  mountIcons(wrap);
  requestAnimationFrame(() => wrap.classList.add('show'));
  $('#rs-ok').addEventListener('click', async () => {
    const ok = await apiOk(() => api.rescheduleSession(s.id, {
      sessionDate: $('#rs-date').value,
      startTime: $('#rs-start').value,
      endTime: $('#rs-end').value,
      classroom: $('#rs-room').value.trim(),
    }), '调课成功');
    if (!ok) return;
    wrap.remove();
    await reloadSchedule();
  });
}
