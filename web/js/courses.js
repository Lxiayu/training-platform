/* ============================================================
 * courses.js —— 课程管理：列表 / 搜索筛选 / 新增编辑 / 上下架 / 删除
 * ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  if (!renderLayout('courses')) return;

  $('#kw').addEventListener('input', renderTable);
  $('#f-category').addEventListener('change', renderTable);
  $('#f-status').addEventListener('change', renderTable);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#tbody').addEventListener('click', onTableClick);

  renderTable();
});

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  const cat = $('#f-category').value;
  const st = $('#f-status').value;
  return DB.courses.filter(c =>
    (!kw || c.name.toLowerCase().includes(kw) || c.id.toLowerCase().includes(kw)) &&
    (!cat || c.category === cat) &&
    (!st || c.status === st)
  );
}

function renderTable() {
  const list = getFiltered();
  $('#count').textContent = list.length;
  $('#tbody').innerHTML = list.length ? list.map(c => `
    <tr>
      <td class="td-sub">${esc(c.id)}</td>
      <td>
        <div class="cell-main">${esc(c.name)}</div>
        <div class="td-sub">${esc(c.target || '')}</div>
      </td>
      <td>${esc(c.category)}</td>
      <td>${esc(c.level)}</td>
      <td>${c.hours} 课时</td>
      <td style="font-weight:600;color:var(--primary)">${money(c.price)}</td>
      <td>${badge(c.status)}</td>
      <td class="td-actions">
        <button class="btn-link" data-act="edit" data-id="${c.id}">${ICONS.edit}编辑</button>
        <button class="btn-link ${c.status === '在售' ? 'danger' : 'success'}" data-act="toggle" data-id="${c.id}">
          ${c.status === '在售' ? '停售' : '上架'}
        </button>
        <button class="btn-link danger" data-act="del" data-id="${c.id}">${ICONS.trash}删除</button>
      </td>
    </tr>`).join('') : emptyRow(8, '没有符合条件的课程');
}

/* ---------- 行操作 ---------- */
function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const c = byId(DB.courses, id);
  if (!c) return;

  if (act === 'edit') {
    openEditor(c);
  } else if (act === 'toggle') {
    c.status = c.status === '在售' ? '停售' : '在售';
    saveDB(); renderTable();
    showToast(c.status === '在售' ? `课程「${c.name}」已上架` : `课程「${c.name}」已停售`);
  } else if (act === 'del') {
    const used = DB.classes.filter(b => b.courseId === id).length;
    if (used) { showToast(`该课程下还有 ${used} 个班级在使用，无法删除`, 'error'); return; }
    askConfirm('删除课程', `确定删除课程「${c.name}」吗？删除后不可恢复。`, () => {
      DB.courses = DB.courses.filter(x => x.id !== id);
      saveDB(); renderTable();
      showToast('课程已删除');
    });
  }
}

/* ---------- 新增 / 编辑 ---------- */
let currentEditId = null;

function openEditor(c) {
  currentEditId = c ? c.id : null;
  $('#modal-title').textContent = c ? '编辑课程' : '新增课程';
  $('#f-name').value = c ? c.name : '';
  $('#f-cat').value = c ? c.category : 'Scratch';
  $('#f-level').value = c ? c.level : '入门';
  $('#f-hours').value = c ? c.hours : '';
  $('#f-price').value = c ? c.price : '';
  $('#f-target').value = c ? (c.target || '') : '';
  $('#f-status-edit').value = c ? c.status : '在售';
  $('#f-desc').value = c ? (c.desc || '') : '';
  openModal('editor-modal');
  $('#f-name').focus();
}

function submitForm() {
  const name = $('#f-name');
  const hours = $('#f-hours');
  const price = $('#f-price');
  if (!valid([[name, '课程名称'], [hours, '课时数'], [price, '学费']])) return;
  if (Number(hours.value) <= 0 || Number(price.value) < 0) { showToast('请输入正确的课时与学费', 'error'); return; }

  const isEdit = !!currentEditId;
  const data = {
    name: name.value.trim(),
    category: $('#f-cat').value,
    level: $('#f-level').value,
    hours: Number(hours.value),
    price: Number(price.value),
    target: $('#f-target').value.trim(),
    status: $('#f-status-edit').value,
    desc: $('#f-desc').value.trim()
  };

  if (isEdit) {
    const idx = DB.courses.findIndex(c => c.id === currentEditId);
    if (idx > -1) DB.courses[idx] = { ...DB.courses[idx], ...data };
  } else {
    DB.courses.push({ id: nextId('KC', DB.courses), ...data });
  }
  saveDB();
  closeModal('editor-modal');
  renderTable();
  showToast(isEdit ? '课程信息已更新' : `课程「${data.name}」创建成功`);
}
