/* ============================================================
 * profile.js —— 个人信息：资料维护 / 修改密码
 * 数据来源：/api/v1/auth/me（展示）、PUT /auth/profile、PUT /auth/password
 * ============================================================ */

let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
  currentUser = await boot('profile', false);
  if (!currentUser) return;

  // 以服务端资料为准（可能已被管理员更新过）
  const me = await apiOk(() => api.me(), '');
  if (me) currentUser = me;
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

/* ---------- 保存基本信息（PUT /auth/profile，写本地缓存的用户信息） ---------- */
async function saveProfile() {
  const name = $('#f-name');
  const phone = $('#f-phone');
  if (!valid([[name, '姓名'], [phone, '手机号码']])) return;
  if (!/^\d{11}$/.test(phone.value.trim())) { showToast('请输入 11 位手机号', 'error'); phone.focus(); return; }

  const rec = await apiOk(() => api.updateProfile({
    name: name.value.trim(),
    phone: phone.value.trim(),
    email: $('#f-email').value.trim()
  }), '');
  if (!rec) return;
  currentUser = rec;
  updateCachedUser(rec);

  // 同步刷新顶栏显示
  $('.topbar .user-name').textContent = currentUser.name;
  $('.topbar .avatar')?.remove();
  const userMeta = $('.topbar .user-meta');
  userMeta.insertAdjacentHTML('afterend', avatarHtml(currentUser.name));

  fillPage();
  showToast('个人信息已保存');
}

/* ---------- 修改密码（原密码正确性由后端校验） ---------- */
async function savePassword() {
  const oldpwd = $('#f-oldpwd');
  const newpwd = $('#f-newpwd');
  const newpwd2 = $('#f-newpwd2');
  if (!valid([[oldpwd, '原密码'], [newpwd, '新密码'], [newpwd2, '确认新密码']])) return;
  if (newpwd.value.length < 6) { showToast('新密码至少 6 位', 'error'); newpwd.focus(); return; }
  if (newpwd.value !== newpwd2.value) { showToast('两次输入的新密码不一致', 'error'); newpwd2.focus(); return; }

  const ok = await apiOk(() => api.changePassword(oldpwd.value, newpwd.value), '密码修改成功，下次登录请使用新密码');
  if (ok) oldpwd.value = newpwd.value = newpwd2.value = '';
}
