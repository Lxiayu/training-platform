/* ============================================================
 * settings.js —— 系统设置：机构信息 / 业务开关 / 演示数据重置
 * ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  if (!renderLayout('settings')) return;

  fillOrgForm();
  fillSettings();

  $('#btn-save-org').addEventListener('click', saveOrg);
  ['sw-leave', 'sw-remind', 'sw-receipt'].forEach(id => $('#' + id).addEventListener('change', onSwitchChange));
  $('#s-newstatus').addEventListener('change', () => {
    DB.settings.newStudentStatus = $('#s-newstatus').value;
    saveDB();
    showToast(`新学员默认状态已设为「${$('#s-newstatus').value}」`);
  });
  $('#btn-reset').addEventListener('click', () => {
    askConfirm('重置演示数据', '将清空本地所有修改，恢复到初始演示数据（含账号密码），确定继续吗？', () => {
      resetDB();
      loadDB();
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

function saveOrg() {
  const name = $('#s-name');
  const phone = $('#s-phone');
  if (!valid([[name, '机构名称'], [phone, '联系电话']])) return;
  DB.org = {
    name: name.value.trim(),
    phone: phone.value.trim(),
    address: $('#s-address').value.trim(),
    intro: $('#s-intro').value.trim()
  };
  saveDB();
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

function onSwitchChange(e) {
  const [label, key] = SWITCH_NAMES[e.target.id];
  DB.settings[key] = e.target.checked;
  saveDB();
  showToast(`${label}已${e.target.checked ? '开启' : '关闭'}`);
}
