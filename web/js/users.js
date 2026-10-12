/* ============================================================
 * users.js —— 用户管理（仅超级管理员）
 * 账号增删改 / 角色分配 / 启用禁用 / 重置密码
 * 数据来源：/api/v1/users（仅管理员可拉取，普通角色被引导回工作台）
 * ============================================================ */

let currentEditKey = null;   // 当前编辑用户的登录账号（主键）

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('users');
  if (!user) return;

  // 权限守卫：非超级管理员禁止访问本页（后端接口同样返回 403）
  if (!isAdmin(user)) {
    showToast('您没有权限访问用户管理', 'error');
    setTimeout(() => location.href = 'dashboard.html', 1200);
    return;
  }

  $('#kw').addEventListener('input', renderTable);
  $('#f-role').addEventListener('change', renderTable);
  $('#f-status').addEventListener('change', renderTable);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#tbody').addEventListener('click', onTableClick);

  renderTable();
});

/* ---------- 角色徽章 ---------- */
const ROLE_BADGE = { '超级管理员': 'primary', '教务管理员': 'info', '财务专员': 'success', '前台接待': 'warning', '教师': 'gray' };
function roleBadge(role) { return `<span class="badge badge-${ROLE_BADGE[role] || 'gray'}">${esc(role)}</span>`; }

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  const role = $('#f-role').value;
  const st = $('#f-status').value;
  return DB.users.filter(u =>
    (!kw || u.name.toLowerCase().includes(kw) || u.username.toLowerCase().includes(kw) || (u.phone || '').includes(kw)) &&
    (!role || u.role === role) &&
    (!st || u.status === st)
  );
}

function renderTable() {
  const list = getFiltered();
  const me = getSessionUser();
  $('#count').textContent = list.length;
  $('#tbody').innerHTML = list.length ? list.map(u => `
    <tr>
      <td>
        <div class="cell-user">
          ${avatarHtml(u.name)}
          <div>
            <div class="cell-main">${esc(u.name)}${u.username === me.username ? ' <span class="badge badge-primary" style="margin-left:6px">当前账号</span>' : ''}</div>
            <div class="td-sub">${esc(u.username)}</div>
          </div>
        </div>
      </td>
      <td>${roleBadge(u.role)}</td>
      <td>${esc(u.phone || '—')}</td>
      <td class="td-sub">${esc(u.email || '—')}</td>
      <td class="td-sub">${esc(u.joinDate || '—')}</td>
      <td>${badge(u.status)}</td>
      <td class="td-actions">
        <button class="btn-link" data-act="edit" data-id="${esc(u.username)}">${ICONS.edit}编辑</button>
        <button class="btn-link" data-act="resetpwd" data-id="${esc(u.username)}">${ICONS.lock}重置密码</button>
        <button class="btn-link ${u.status === '启用' ? 'danger' : ''}" data-act="toggle" data-id="${esc(u.username)}">${u.status === '启用' ? ICONS.x + '禁用' : ICONS.check + '启用'}</button>
        <button class="btn-link danger" data-act="del" data-id="${esc(u.username)}">${ICONS.trash}删除</button>
      </td>
    </tr>`).join('') : emptyRow(7, '没有符合条件的用户');
}

/* ---------- 行操作 ---------- */
async function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const u = DB.users.find(x => x.username === id);
  if (!u) return;

  if (act === 'edit') {
    openEditor(u);
  } else if (act === 'resetpwd') {
    askConfirm('重置密码', `确定将「${u.name}（${u.username}）」的密码重置为初始密码 123456 吗？`, async () => {
      const rec = await apiOk(() => api.resetPassword(id));
      if (!rec) return;
      showToast(`密码已重置为 ${rec.initialPassword}`);
    });
  } else if (act === 'toggle') {
    // 不能禁用自己 / 至少保留一名启用管理员等规则由后端校验（409 提示）
    const next = u.status === '启用' ? '禁用' : '启用';
    if (!await apiOk(() => api.update('users', id, { status: next }))) return;
    await hydrate(); renderTable();
    showToast(next === '启用' ? `账号「${u.username}」已启用` : `账号「${u.username}」已禁用，该账号将无法登录`);
  } else if (act === 'del') {
    askConfirm('删除用户', `确定删除用户「${u.name}（${u.username}）」吗？删除后该账号将无法登录。`, async () => {
      if (!await apiOk(() => api.remove('users', id))) return;
      await hydrate(); renderTable();
      showToast('用户已删除');
    });
  }
}

/* ---------- 新增 / 编辑 ---------- */
function openEditor(u) {
  currentEditKey = u ? u.username : null;
  $('#modal-title').textContent = u ? '编辑用户' : '新增用户';
  $('#f-username').value = u ? u.username : '';
  $('#f-username').disabled = !!u;
  $('#f-name').value = u ? u.name : '';
  $('#f-pwd').value = '';
  $('#f-pwd').disabled = !!u;
  $('#f-pwd').placeholder = u ? '编辑不支持修改密码，请使用「重置密码」' : '初始密码，留空默认 123456（至少 6 位）';
  $('#f-role-edit').value = u ? u.role : '教务管理员';
  $('#f-phone').value = u ? (u.phone || '') : '';
  $('#f-email').value = u ? (u.email || '') : '';
  $('#f-joindate').value = u ? (u.joinDate || todayStr()) : todayStr();
  $('#f-status-edit').value = u ? u.status : '启用';
  openModal('editor-modal');
  if (!u) $('#f-username').focus(); else $('#f-name').focus();
}

async function submitForm() {
  const username = $('#f-username');
  const name = $('#f-name');
  const pwd = $('#f-pwd');
  const phone = $('#f-phone');
  const joinDate = $('#f-joindate');
  const isEdit = !!currentEditKey;

  if (!valid([[username, '登录账号'], [name, '姓名'], [phone, '手机号'], [joinDate, '加入日期']])) return;
  if (!isEdit && pwd.value && pwd.value.length < 6) { showToast('初始密码至少需要 6 位', 'error'); pwd.focus(); return; }
  if (!/^\d{11}$/.test(phone.value.trim())) { showToast('请输入 11 位手机号', 'error'); phone.focus(); return; }

  const data = {
    username: username.value.trim(),
    name: name.value.trim(),
    role: $('#f-role-edit').value,
    phone: phone.value.trim(),
    email: $('#f-email').value.trim(),
    joinDate: joinDate.value,
    status: $('#f-status-edit').value
  };
  if (!isEdit && pwd.value) data.password = pwd.value;   // 留空则由后端使用默认密码 123456

  // 账号重复 / 禁用自己 / 最后一名管理员等规则由后端校验（409 提示）
  if (!await apiOk(() => isEdit ? api.update('users', currentEditKey, data) : api.create('users', data))) return;
  await hydrate();
  closeModal('editor-modal');
  renderTable();
  showToast(isEdit ? '用户信息已更新'
    : `用户「${data.name}」创建成功，初始密码为 ${data.password || '123456'}`);
}

