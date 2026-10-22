/* ============================================================
 * courses.js —— 课程管理：列表 / 搜索筛选 / 新增编辑 / 上下架 / 删除
 * 数据来源：/api/v1/courses（boot 后缓存于 DB.courses）
 * ============================================================ */

let currentEditId = null;
let canWrite = false;   // 写操作仅超管 / 教务（与后端 require_roles 一致）

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('courses');
  if (!user) return;

  canWrite = canManageAcademic(user);
  if (!canWrite) $('#btn-add').style.display = 'none';

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
        ${canWrite ? `
        <button class="btn-link" data-act="edit" data-id="${c.id}">${ICONS.edit}编辑</button>
        <button class="btn-link ${c.status === '在售' ? 'danger' : 'success'}" data-act="toggle" data-id="${c.id}">
          ${c.status === '在售' ? '停售' : '上架'}
        </button>
        <button class="btn-link danger" data-act="del" data-id="${c.id}">${ICONS.trash}删除</button>` : ''}
      </td>
    </tr>`).join('') : emptyRow(8, '没有符合条件的课程');
}

/* ---------- 行操作 ---------- */
async function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const c = byId(DB.courses, id);
  if (!c) return;

  if (act === 'edit') {
    openEditor(c);
  } else if (act === 'toggle') {
    const next = c.status === '在售' ? '停售' : '在售';
    if (!await apiOk(() => api.update('courses', id, { status: next }))) return;
    await hydrate(); renderTable();
    showToast(next === '在售' ? `课程「${c.name}」已上架` : `课程「${c.name}」已停售`);
  } else if (act === 'del') {
    // 是否被班级使用等业务校验由后端执行（冲突返回 409 并提示原因）
    askConfirm('删除课程', `确定删除课程「${c.name}」吗？删除后不可恢复。`, async () => {
      if (!await apiOk(() => api.remove('courses', id))) return;
      await hydrate(); renderTable();
      showToast('课程已删除');
    });
  }
}

/* ---------- 新增 / 编辑 ---------- */

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

async function submitForm() {
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

  if (!await apiOk(() => isEdit ? api.update('courses', currentEditId, data) : api.create('courses', data))) return;
  await hydrate();
  closeModal('editor-modal');
  renderTable();
  showToast(isEdit ? '课程信息已更新' : `课程「${data.name}」创建成功`);
}
