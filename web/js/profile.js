/* ============================================================
 * profile.js —— 个人信息：资料维护 / 修改密码
 * ============================================================ */

let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
  currentUser = renderLayout('profile');
  if (!currentUser) return;
  fillPage();

  $('#btn-save-profile').addEventListener('click', saveProfile);
  $('#btn-save-pwd').addEventListener('click', savePassword);
});

function fillPage() {
  const u = currentUser;
  // 左侧卡片
  const avatar = $('#p-avatar');
  avatar.textContent = u.name.length > 2 ? u.name.slice(-2) : u.name;
  avatar.style.background = avatarColor(u.name);
  $('#p-name').textContent = u.name;
  $('#p-role').innerHTML = `<span class="badge badge-primary">${esc(u.role)}</span>`;
  $('#p-username').textContent = u.username;
  $('#p-phone').textContent = u.phone || '—';
  $('#p-email').textContent = u.email || '—';
  $('#p-join').textContent = u.joinDate || '—';
  // 右侧表单
  $('#f-name').value = u.name;
  $('#f-phone').value = u.phone || '';
  $('#f-email').value = u.email || '';
}

/* ---------- 保存基本信息 ---------- */
function saveProfile() {
  const name = $('#f-name');
  const phone = $('#f-phone');
  if (!valid([[name, '姓名'], [phone, '手机号码']])) return;
  if (!/^\d{11}$/.test(phone.value.trim())) { showToast('请输入 11 位手机号', 'error'); phone.focus(); return; }

  currentUser.name = name.value.trim();
  currentUser.phone = phone.value.trim();
  currentUser.email = $('#f-email').value.trim();
  saveDB();

  // 同步刷新顶栏显示
  $('.topbar .user-name').textContent = currentUser.name;
  $('.topbar .avatar')?.remove();
  const userMeta = $('.topbar .user-meta');
  userMeta.insertAdjacentHTML('afterend', avatarHtml(currentUser.name));

  fillPage();
  showToast('个人信息已保存');
}

/* ---------- 修改密码 ---------- */
function savePassword() {
  const oldpwd = $('#f-oldpwd');
  const newpwd = $('#f-newpwd');
  const newpwd2 = $('#f-newpwd2');
  if (!valid([[oldpwd, '原密码'], [newpwd, '新密码'], [newpwd2, '确认新密码']])) return;
  if (oldpwd.value !== currentUser.password) { showToast('原密码不正确', 'error'); oldpwd.focus(); return; }
  if (newpwd.value.length < 6) { showToast('新密码至少 6 位', 'error'); newpwd.focus(); return; }
  if (newpwd.value !== newpwd2.value) { showToast('两次输入的新密码不一致', 'error'); newpwd2.focus(); return; }

  currentUser.password = newpwd.value;
  saveDB();
  oldpwd.value = newpwd.value = newpwd2.value = '';
  showToast('密码修改成功，下次登录请使用新密码');
}
