/* ============================================================
 * payments.js —— 缴费管理：统计 / 记录 / 登记 / 确认 / 作废
 * 数据来源：/api/v1/payments（统计走 /payments/stats 专用端点）
 * ============================================================ */

let currentEditId = null;
let canWrite = false;   // 写操作（登记 / 确认 / 作废 / 删除）仅超管 / 财务（与后端 require_roles 一致）

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('payments');
  if (!user) return;

  canWrite = canManageFinance(user);
  if (!canWrite) $('#btn-add').style.display = 'none';

  // 选择学员后，班级自动切换到该学员所在班级并带出课程价格
  $('#f-student').addEventListener('change', () => {
    const s = byId(DB.students, $('#f-student').value);
    if (!s) return;
    if (s.classId) $('#f-class').value = s.classId;
    syncAmount();
  });
  $('#f-class').addEventListener('change', syncAmount);

  $('#kw').addEventListener('input', renderTable);
  $('#f-status').addEventListener('change', renderTable);
  $('#f-method').addEventListener('change', renderTable);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#tbody').addEventListener('click', onTableClick);

  await renderStats();
  renderTable();
});

/* ---------- 下拉与联动 ---------- */
function fillStudentSelect(selected) {
  const opts = DB.students.map(s => {
    const cls = byId(DB.classes, s.classId);
    return `<option value="${s.id}">${esc(s.name)}（${esc(s.grade)} · ${cls ? esc(cls.name) : '未分班'}）</option>`;
  }).join('');
  $('#f-student').innerHTML = opts || '<option value="">暂无学员</option>';
  if (selected) $('#f-student').value = selected;
}

function fillClassSelect(selected) {
  const opts = DB.classes.map(c => `<option value="${c.id}">${esc(c.name)}（${esc(courseName(c.courseId))}）</option>`).join('');
  $('#f-class').innerHTML = opts || '<option value="">暂无班级</option>';
  if (selected) $('#f-class').value = selected;
}

function syncAmount() {
  const cls = byId(DB.classes, $('#f-class').value);
  if (cls && !currentEditId) {
    const course = byId(DB.courses, cls.courseId);
    if (course) $('#f-amount').value = course.price;
  }
}

/* ---------- 统计（后端 /payments/stats 口径：仅「已支付」计入收入） ---------- */
async function renderStats() {
  const st = await apiOk(() => api.paymentStats(), '');
  if (!st) return;
  $('#stat-month').textContent = money(st.monthIncome);
  $('#stat-pending').textContent = st.pendingCount + ' 笔 · ' + money(st.pendingAmount);
  $('#stat-total').textContent = money(st.totalIncome);
}

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  const st = $('#f-status').value;
  const md = $('#f-method').value;
  return DB.payments.filter(p =>
    (!kw || p.id.toLowerCase().includes(kw) || studentName(p.studentId).toLowerCase().includes(kw)) &&
    (!st || p.status === st) &&
    (!md || p.method === md)
  );
}

function renderTable() {
  const list = [...getFiltered()].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  $('#count').textContent = list.length;
  $('#tbody').innerHTML = list.length ? list.map(p => {
    const cls = byId(DB.classes, p.classId);
    return `
    <tr>
      <td class="td-sub">${esc(p.id)}</td>
      <td style="font-weight:600">${esc(studentName(p.studentId))}</td>
      <td>
        <div>${cls ? esc(cls.name) : '—'}</div>
        <div class="td-sub">${cls ? esc(courseName(cls.courseId)) : ''}</div>
      </td>
      <td style="font-weight:600;color:var(--primary)">${money(p.amount)}</td>
      <td>${esc(p.method)}</td>
      <td class="td-sub">${esc(p.date)}</td>
      <td class="td-sub">${esc(p.note || '—')}</td>
      <td>${badge(p.status)}</td>
      <td class="td-actions">
        ${canWrite ? `
        <button class="btn-link" data-act="edit" data-id="${p.id}">${ICONS.edit}编辑</button>
        ${p.status === '待确认' ? `<button class="btn-link success" data-act="confirm" data-id="${p.id}">${ICONS.check}确认</button>` : ''}
        ${p.status !== '已作废' && p.status !== '已退款' ? `<button class="btn-link danger" data-act="void" data-id="${p.id}">作废</button>` : ''}
        <button class="btn-link danger" data-act="del" data-id="${p.id}">${ICONS.trash}删除</button>` : ''}
      </td>
    </tr>`;
  }).join('') : emptyRow(9, '没有符合条件的缴费记录');
}

/* ---------- 行操作 ---------- */
function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const p = byId(DB.payments, id);
  if (!p) return;

  if (act === 'edit') {
    openEditor(p);
  } else if (act === 'confirm') {
    // 仅「待确认」可确认；状态流转规则由后端校验（409 提示）
    askConfirm('确认到账', `确认学员「${studentName(p.studentId)}」的 ${money(p.amount)} 缴费已到账吗？`, async () => {
      if (!await apiOk(() => api.paymentConfirm(id))) return;
      await hydrate(); await renderStats(); renderTable();
      showToast('已确认到账');
    });
  } else if (act === 'void') {
    askConfirm('作废记录', `确定将流水 ${p.id} 作废吗？作废后不计入收入统计。`, async () => {
      if (!await apiOk(() => api.paymentVoid(id))) return;
      await hydrate(); await renderStats(); renderTable();
      showToast('该缴费记录已作废');
    });
  } else if (act === 'del') {
    askConfirm('删除记录', `确定删除流水 ${p.id}（${studentName(p.studentId)} · ${money(p.amount)}）吗？删除后不可恢复。`, async () => {
      if (!await apiOk(() => api.remove('payments', id))) return;
      await hydrate(); await renderStats(); renderTable();
      showToast('缴费记录已删除');
    });
  }
}

/* ---------- 登记 / 编辑 ---------- */
function openEditor(p) {
  currentEditId = p ? p.id : null;
  $('#modal-title').textContent = p ? '编辑缴费' : '登记缴费';
  fillStudentSelect(p && p.studentId);
  fillClassSelect(p && p.classId);
  $('#f-amount').value = p ? p.amount : '';
  $('#f-method-edit').value = p ? p.method : '微信';
  $('#f-date').value = p ? p.date : todayStr();
  $('#f-status-edit').value = p ? p.status : '已支付';
  $('#f-note').value = p ? (p.note || '') : '';
  openModal('editor-modal');
}

async function submitForm() {
  const amount = $('#f-amount');
  const date = $('#f-date');
  const studentId = $('#f-student').value;
  const classId = $('#f-class').value;
  if (!studentId) { showToast('请先添加学员', 'error'); return; }
  if (!classId) { showToast('请选择缴费班级', 'error'); return; }
  if (!valid([[amount, '缴费金额'], [date, '缴费日期']])) return;
  if (Number(amount.value) <= 0) { showToast('缴费金额必须大于 0', 'error'); return; }

  const isEdit = !!currentEditId;
  const data = {
    studentId, classId,
    amount: Number(amount.value),
    method: $('#f-method-edit').value,
    date: date.value,
    status: $('#f-status-edit').value,
    note: $('#f-note').value.trim()
  };

  if (!await apiOk(() => isEdit ? api.update('payments', currentEditId, data) : api.create('payments', data))) return;
  await hydrate();
  closeModal('editor-modal');
  await renderStats(); renderTable();
  showToast(isEdit ? '缴费记录已更新' : `已为「${studentName(studentId)}」登记缴费 ${money(data.amount)}`);
}

