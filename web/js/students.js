/* ============================================================
 * students.js —— 学生管理：列表 / 筛选 / 新增编辑 / 删除
 * 数据来源：/api/v1/students（boot 后缓存于 DB.students）
 * ============================================================ */

let currentEditId = null;
let canWrite = false;   // 写操作（报名 / 修改）仅超管 / 教务 / 前台（与后端 require_roles 一致）

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('students');
  if (!user) return;

  canWrite = canEnrollStudent(user);
  if (!canWrite) $('#btn-add').style.display = 'none';

  // 班级下拉（工具栏筛选 + 编辑表单共用渲染）
  const classOptions = () => {
    const opts = DB.classes
      .filter(c => c.status !== '已结课')
      .map(c => `<option value="${c.id}">${esc(c.name)}（${esc(courseName(c.courseId))}）</option>`)
      .join('');
    $('#f-class').innerHTML = `<option value="">全部班级</option>` + opts;
    $('#f-class-edit').innerHTML = opts || '<option value="">暂无可选班级</option>';
  };
  classOptions();

  $('#kw').addEventListener('input', renderTable);
  $('#f-class').addEventListener('change', renderTable);
  $('#f-status').addEventListener('change', renderTable);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#tbody').addEventListener('click', onTableClick);

  renderTable();
});

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  const cls = $('#f-class').value;
  const st = $('#f-status').value;
  return DB.students.filter(s =>
    (!kw || s.name.toLowerCase().includes(kw) || s.id.toLowerCase().includes(kw) || (s.parentPhone || '').includes(kw)) &&
    (!cls || s.classId === cls) &&
    (!st || s.status === st)
  );
}

function renderTable() {
  const list = getFiltered();
  $('#count').textContent = list.length;
  $('#tbody').innerHTML = list.length ? list.map(s => {
    const cls = byId(DB.classes, s.classId);
    return `
    <tr>
      <td>
        <div class="cell-user">
          ${avatarHtml(s.name)}
          <div>
            <div class="cell-main">${esc(s.name)}</div>
            <div class="td-sub">${esc(s.id)}</div>
          </div>
        </div>
      </td>
      <td>${esc(s.gender)}</td>
      <td>${esc(s.grade)}</td>
      <td>${esc(s.parent || '—')}</td>
      <td>${esc(s.parentPhone || '—')}</td>
      <td>${cls ? esc(cls.name) : '未分班'}</td>
      <td class="td-sub">${cls ? esc(courseName(cls.courseId)) : '—'}</td>
      <td class="td-sub">${esc(s.enrollDate)}</td>
      <td>${badge(s.status)}</td>
      <td class="td-actions">
        ${canWrite ? `
        <button class="btn-link" data-act="edit" data-id="${s.id}">${ICONS.edit}编辑</button>
        <button class="btn-link danger" data-act="del" data-id="${s.id}">${ICONS.trash}删除</button>` : ''}
      </td>
    </tr>`;
  }).join('') : emptyRow(10, '没有符合条件的学员');
}

/* ---------- 行操作 ---------- */
function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const s = byId(DB.students, id);
  if (!s) return;

  if (act === 'edit') {
    openEditor(s);
  } else if (act === 'del') {
    // 缴费记录由后端级联删除；本地计数仅用于确认提示文案
    const paid = DB.payments.filter(p => p.studentId === id).length;
    askConfirm('删除学员', `确定删除学员「${s.name}」吗？${paid ? `该学员有 ${paid} 条缴费记录，将一并删除。` : ''}删除后不可恢复。`, async () => {
      if (!await apiOk(() => api.remove('students', id))) return;
      await hydrate(); renderTable();
      showToast('学员已删除');
    });
  }
}

/* ---------- 新增 / 编辑 ---------- */
function openEditor(s) {
  currentEditId = s ? s.id : null;
  $('#modal-title').textContent = s ? '编辑学员' : '新增学员';
  $('#f-name').value = s ? s.name : '';
  $('#f-gender').value = s ? s.gender : '女';
  $('#f-grade').value = s ? s.grade : '三年级';
  $('#f-parent').value = s ? (s.parent || '') : '';
  $('#f-parent-phone').value = s ? (s.parentPhone || '') : '';
  $('#f-class-edit').value = s ? s.classId : ($('#f-class-edit').value || '');
  $('#f-enrolldate').value = s ? s.enrollDate : todayStr();
  // 新学员默认状态跟随「系统设置」
  $('#f-status-edit').value = s ? s.status : (DB.settings.newStudentStatus || '在读');
  openModal('editor-modal');
  $('#f-name').focus();
}

async function submitForm() {
  const name = $('#f-name');
  const parent = $('#f-parent');
  const parentPhone = $('#f-parent-phone');
  const classId = $('#f-class-edit').value;
  const enrollDate = $('#f-enrolldate');
  if (!valid([[name, '学员姓名'], [parent, '家长姓名'], [parentPhone, '家长电话'], [enrollDate, '报名日期']])) return;
  if (!classId) { showToast('请先创建班级，再新增学员', 'error'); return; }
  if (!/^\d{11}$/.test(parentPhone.value.trim())) { showToast('请输入 11 位手机号', 'error'); parentPhone.focus(); return; }

  const isEdit = !!currentEditId;
  const data = {
    name: name.value.trim(),
    gender: $('#f-gender').value,
    grade: $('#f-grade').value,
    parent: parent.value.trim(),
    parentPhone: parentPhone.value.trim(),
    classId,
    enrollDate: enrollDate.value,
    status: $('#f-status-edit').value
  };

  if (!await apiOk(() => isEdit ? api.update('students', currentEditId, data) : api.create('students', data))) return;
  await hydrate();
  closeModal('editor-modal');
  renderTable();
  showToast(isEdit ? '学员信息已更新' : `学员「${data.name}」报名成功`);
}
