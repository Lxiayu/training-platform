/* ============================================================
 * users.js —— 用户管理（仅超级管理员）
 * 账号增删改 / 角色分配 / 启用禁用 / 重置密码
 * ============================================================ */

let currentEditKey = null;   // 当前编辑用户的登录账号（主键）

document.addEventListener('DOMContentLoaded', () => {
  const user = renderLayout('users');
  if (!user) return;

  // 权限守卫：非超级管理员禁止访问本页
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
function onTableClick(e) {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const { act, id } = btn.dataset;
  const u = DB.users.find(x => x.username === id);
  if (!u) return;
  const me = getSessionUser();

  if (act === 'edit') {
    openEditor(u);
  } else if (act === 'resetpwd') {
    askConfirm('重置密码', `确定将「${u.name}（${u.username}）」的密码重置为初始密码 123456 吗？`, () => {
      u.password = '123456';
      saveDB();
      showToast('密码已重置为 123456');
    });
  } else if (act === 'toggle') {
    if (u.username === me.username) { showToast('不能禁用当前登录账号', 'error'); return; }
    if (u.status === '启用' && lastActiveAdmin(u)) { showToast('系统至少需保留一个启用的超级管理员', 'error'); return; }
    u.status = u.status === '启用' ? '禁用' : '启用';
    saveDB(); renderTable();
    showToast(u.status === '启用' ? `账号「${u.username}」已启用` : `账号「${u.username}」已禁用，该账号将无法登录`);
  } else if (act === 'del') {
    if (u.username === me.username) { showToast('不能删除当前登录账号', 'error'); return; }
    if (lastActiveAdmin(u)) { showToast('系统至少需保留一个启用的超级管理员', 'error'); return; }
    askConfirm('删除用户', `确定删除用户「${u.name}（${u.username}）」吗？删除后该账号将无法登录。`, () => {
      DB.users = DB.users.filter(x => x.username !== u.username);
      saveDB(); renderTable();
      showToast('用户已删除');
    });
  }
}

// 判断：u 是否为系统最后一个「启用的超级管理员」
function lastActiveAdmin(u) {
  return u.role === '超级管理员' && u.status === '启用' &&
    DB.users.filter(x => x.role === '超级管理员' && x.status === '启用').length === 1;
}

/* ---------- 新增 / 编辑 ---------- */
function openEditor(u) {
  currentEditKey = u ? u.username : null;
  $('#modal-title').textContent = u ? '编辑用户' : '新增用户';
  $('#f-username').value = u ? u.username : '';
  $('#f-username').disabled = !!u;
  $('#f-name').value = u ? u.name : '';
  $('#f-pwd').value = '';
  $('#f-pwd').placeholder = u ? '留空表示不修改密码' : '请输入初始密码（至少 6 位）';
  $('#f-role-edit').value = u ? u.role : '教务管理员';
  $('#f-phone').value = u ? (u.phone || '') : '';
  $('#f-email').value = u ? (u.email || '') : '';
  $('#f-joindate').value = u ? (u.joinDate || todayStr()) : todayStr();
  $('#f-status-edit').value = u ? u.status : '启用';
  openModal('editor-modal');
  if (!u) $('#f-username').focus(); else $('#f-name').focus();
}

function submitForm() {
  const username = $('#f-username');
  const name = $('#f-name');
  const pwd = $('#f-pwd');
  const phone = $('#f-phone');
  const joinDate = $('#f-joindate');
  const isEdit = !!currentEditKey;

  if (!valid([[username, '登录账号'], [name, '姓名'], [phone, '手机号'], [joinDate, '加入日期']])) return;
  if (!isEdit && pwd.value.length < 6) { showToast('初始密码至少需要 6 位', 'error'); pwd.focus(); return; }
  if (!/^\d{11}$/.test(phone.value.trim())) { showToast('请输入 11 位手机号', 'error'); phone.focus(); return; }

  const role = $('#f-role-edit').value;
  const status = $('#f-status-edit').value;

  if (!isEdit && DB.users.some(x => x.username === username.value.trim())) {
    showToast('该登录账号已存在，请更换', 'error'); username.focus(); return;
  }
  if (isEdit) {
    const target = DB.users.find(x => x.username === currentEditKey);
    const me = getSessionUser();
    if (target && target.username === me.username && status === '禁用') {
      showToast('不能禁用当前登录账号', 'error'); return;
    }
    if (target && lastActiveAdmin(target) && (role !== '超级管理员' || status === '禁用')) {
      showToast('系统至少需保留一个启用的超级管理员', 'error'); return;
    }
  }

  const data = {
    name: name.value.trim(),
    role,
    phone: phone.value.trim(),
    email: $('#f-email').value.trim(),
    joinDate: joinDate.value,
    status
  };

  if (isEdit) {
    const idx = DB.users.findIndex(x => x.username === currentEditKey);
    if (idx > -1) {
      DB.users[idx] = { ...DB.users[idx], ...data };
      if (pwd.value) DB.users[idx].password = pwd.value;
    }
  } else {
    DB.users.push({ username: username.value.trim(), password: pwd.value, ...data });
  }
  saveDB();
  closeModal('editor-modal');
  renderTable();
  showToast(isEdit ? '用户信息已更新' : `用户「${data.name}」创建成功，初始密码已生效`);
}

