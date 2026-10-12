/* ============================================================
 * settings.js —— 系统设置：机构信息 / 业务开关 / 演示数据重置
 * 数据来源：GET /settings（全员可读）；PUT、POST /reset 仅管理员
 * ============================================================ */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('settings');
  if (!user) return;

  fillOrgForm();
  fillSettings();

  // 非管理员只读：写入接口均 require_admin，前端同步禁用
  if (!isAdmin(user)) {
    $$('#settings-page input, #settings-page select, #settings-page textarea, #settings-page button').forEach(el => el.disabled = true);
    showToast('系统设置仅超级管理员可修改，您当前为只读模式', 'info');
    return;
  }

  $('#btn-save-org').addEventListener('click', saveOrg);
  ['sw-leave', 'sw-remind', 'sw-receipt'].forEach(id => $('#' + id).addEventListener('change', onSwitchChange));
  $('#s-newstatus').addEventListener('change', async () => {
    const val = $('#s-newstatus').value;
    if (!await apiOk(() => api.settingsUpdate({ newStudentStatus: val }))) return;
    await hydrate();
    showToast(`新学员默认状态已设为「${val}」`);
  });
  $('#btn-reset').addEventListener('click', () => {
    askConfirm('重置演示数据', '将清空服务器上所有业务修改，恢复到初始演示数据（含账号密码），确定继续吗？', async () => {
      if (!await apiOk(() => api.settingsReset(), '')) return;
      await hydrate();
      fillOrgForm();
      fillSettings();
      showToast('演示数据已重置');
    });
  });
});

/* ---------- 机构信息 ---------- */
function fillOrgForm() {
  $('#s-name').value = DB.org.name || '';
  $('#s-phone').value = DB.org.phone || '';
  $('#s-address').value = DB.org.address || '';
  $('#s-intro').value = DB.org.intro || '';
}

async function saveOrg() {
  const name = $('#s-name');
  const phone = $('#s-phone');
  if (!valid([[name, '机构名称'], [phone, '联系电话']])) return;
  if (!await apiOk(() => api.settingsUpdate({
    name: name.value.trim(),
    phone: phone.value.trim(),
    address: $('#s-address').value.trim(),
    intro: $('#s-intro').value.trim()
  }))) return;
  await hydrate();
  showToast('机构信息已保存');
}

/* ---------- 业务开关 ---------- */
function fillSettings() {
  $('#sw-leave').checked = !!DB.settings.allowLeave;
  $('#sw-remind').checked = !!DB.settings.scheduleRemind;
  $('#sw-receipt').checked = !!DB.settings.receiptPrint;
  $('#s-newstatus').value = DB.settings.newStudentStatus || '在读';
}

const SWITCH_NAMES = {
  'sw-leave': ['允许学员自助请假', 'allowLeave'],
  'sw-remind': ['上课自动提醒', 'scheduleRemind'],
  'sw-receipt': ['缴费收据自动打印', 'receiptPrint']
};

async function onSwitchChange(e) {
  const [label, key] = SWITCH_NAMES[e.target.id];
  const ok = await apiOk(() => api.settingsUpdate({ [key]: e.target.checked }));
  if (!ok) { e.target.checked = !e.target.checked; return; }   // 保存失败回滚开关状态
  await hydrate();
  showToast(`${label}已${e.target.checked ? '开启' : '关闭'}`);
}
