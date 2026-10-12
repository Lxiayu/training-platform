/* ============================================================
 * resources.js —— 课件资源：资源库卡片 / 筛选 / 上传编辑删除 / 模拟下载
 * ============================================================ */

let currentEditId = null;

const TYPE_META = {
  '课件PPT':  { icon: 'filetext', cls: 'res-icon-ppt' },
  '教学视频': { icon: 'video',    cls: 'res-icon-video' },
  '习题册':   { icon: 'book',     cls: 'res-icon-exercise' },
  '素材包':   { icon: 'package',  cls: 'res-icon-material' }
};

document.addEventListener('DOMContentLoaded', () => {
  if (!renderLayout('resources')) return;

  // 课程筛选下拉（动态生成）
  $('#f-course').innerHTML = '<option value="">全部课程</option>' +
    DB.courses.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');

  $('#kw').addEventListener('input', renderGrid);
  $('#f-type').addEventListener('change', renderGrid);
  $('#f-course').addEventListener('change', renderGrid);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#res-grid').addEventListener('click', onGridClick);

  renderGrid();
});

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  const type = $('#f-type').value;
  const courseId = $('#f-course').value;
  return DB.resources.filter(r =>
    (!kw || r.title.toLowerCase().includes(kw)) &&
    (!type || r.type === type) &&
    (!courseId || r.courseId === courseId)
  );
}

function renderGrid() {
  const list = getFiltered();
  $('#res-grid').innerHTML = list.length ? list.map(r => {
    const meta = TYPE_META[r.type] || TYPE_META['课件PPT'];
    return `
    <div class="res-card">
      <div class="res-card-head ${meta.cls}">${ICONS[meta.icon]}</div>
      <div class="res-card-body">
        <div class="res-title clamp-2" title="${esc(r.title)}">${esc(r.title)}</div>
        <div class="res-course">${esc(courseName(r.courseId))} · ${esc(teacherName(r.teacherId))}</div>
        <div class="res-meta">
          <span>${ICONS.folder}${esc(r.size)}</span>
          ${r.duration ? `<span>${ICONS.clock}${esc(r.duration)}</span>` : ''}
          <span>${ICONS.calendar}${esc(r.date)}</span>
        </div>
      </div>
      <div class="res-card-foot">
        <span class="res-downloads">${ICONS.download}${r.downloads || 0} 次下载</span>
        <div class="res-actions">
          <button class="icon-btn sm" data-act="view" data-id="${r.id}" title="预览">${ICONS.eye}</button>
          <button class="icon-btn sm" data-act="down" data-id="${r.id}" title="下载">${ICONS.download}</button>
          <button class="icon-btn sm" data-act="edit" data-id="${r.id}" title="编辑">${ICONS.edit}</button>
          <button class="icon-btn sm danger" data-act="del" data-id="${r.id}" title="删除">${ICONS.trash}</button>
        </div>
      </div>
    </div>`;
  }).join('') : `
    <div class="card" style="grid-column:1/-1;padding:44px;text-align:center;color:var(--muted)">
      ${ICONS.empty}<div style="margin-top:8px">暂无课件资源，点击右上角「上传资源」添加第一个吧</div>
    </div>`;
}

/* ---------- 卡片操作 ---------- */
function onGridClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const r = byId(DB.resources, id);
  if (!r) return;

  if (act === 'view') {
    showToast(r.type === '教学视频' ? '演示版暂不支持在线播放，可下载后查看' : '演示版暂不支持在线预览，可直接下载查看', 'info');
  } else if (act === 'down') {
    r.downloads = (r.downloads || 0) + 1;
    saveDB(); renderGrid();
    showToast(`已开始下载「${r.title}」（模拟）`);
  } else if (act === 'edit') {
    openEditor(r);
  } else if (act === 'del') {
    askConfirm('删除资源', `确定删除「${r.title}」吗？删除后不可恢复。`, () => {
      DB.resources = DB.resources.filter(x => x.id !== id);
      saveDB(); renderGrid();
      showToast('资源已删除');
    });
  }
}

/* ---------- 上传 / 编辑 ---------- */
function openEditor(r) {
  currentEditId = r ? r.id : null;
  $('#modal-title').textContent = r ? '编辑资源' : '上传资源';
  // 下拉选项动态生成
  $('#f-course-edit').innerHTML = DB.courses.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
  $('#f-teacher-edit').innerHTML = DB.teachers.filter(t => t.status === '在职')
    .map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join('');

  $('#f-title').value = r ? r.title : '';
  $('#f-type-edit').value = r ? r.type : '课件PPT';
  $('#f-course-edit').value = r ? r.courseId : ((DB.courses[0] || {}).id || '');
  $('#f-teacher-edit').value = r ? r.teacherId : '';
  $('#f-size').value = r ? r.size : '';
  $('#f-duration').value = r ? (r.duration || '') : '';
  $('#f-date').value = r ? r.date : todayStr();
  $('#f-status-edit').value = r ? r.status : '已发布';
  openModal('editor-modal');
  $('#f-title').focus();
}

function submitForm() {
  const title = $('#f-title');
  const size = $('#f-size');
  const date = $('#f-date');
  if (!valid([[title, '资源名称'], [size, '文件大小'], [date, '上传日期']])) return;
  if (!$('#f-course-edit').value || !$('#f-teacher-edit').value) {
    showToast('请选择所属课程与上传教师', 'error'); return;
  }

  const isEdit = !!currentEditId;
  const data = {
    title: title.value.trim(),
    type: $('#f-type-edit').value,
    courseId: $('#f-course-edit').value,
    teacherId: $('#f-teacher-edit').value,
    size: size.value.trim(),
    duration: $('#f-duration').value.trim(),
    date: date.value,
    status: $('#f-status-edit').value
  };

  if (isEdit) {
    const idx = DB.resources.findIndex(x => x.id === currentEditId);
    if (idx > -1) DB.resources[idx] = { ...DB.resources[idx], ...data };
  } else {
    DB.resources.push({ id: nextId('ZY', DB.resources), downloads: 0, ...data });
  }
  saveDB();
  closeModal('editor-modal');
  renderGrid();
  showToast(isEdit ? '资源信息已更新' : '资源上传成功（模拟）');
}

