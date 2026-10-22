/* ============================================================
 * news.js —— 新闻中心：分类筛选 / 置顶头条 / 详情 / 发布编辑删除
 * 数据来源：/api/v1/news（阅读量走 /news/{id}/view 专用端点）
 * ============================================================ */

let currentEditId = null;
let filterCat = '';
let canWrite = false;   // 发布 / 编辑 / 删除仅超管 / 教务（与后端 require_roles 一致）

const NEWS_CATS = ['机构动态', '活动通知', '比赛获奖', '开班信息'];
const CAT_META = {
  '机构动态': { icon: 'building', color: '#4f46e5' },
  '活动通知': { icon: 'calendar', color: '#0ea5e9' },
  '比赛获奖': { icon: 'trophy',   color: '#f59e0b' },
  '开班信息': { icon: 'users',    color: '#10b981' }
};

document.addEventListener('DOMContentLoaded', async () => {
  const user = await boot('news');
  if (!user) return;

  // 读接口全员可见，写操作仅超管 / 教务：无权限者隐藏发布入口
  canWrite = canPublishNews(user);
  if (!canWrite) $('#btn-add').style.display = 'none';

  $('#kw').addEventListener('input', renderList);
  $('#btn-add').addEventListener('click', () => openEditor(null));
  $('#btn-submit').addEventListener('click', submitForm);
  $('#chips').addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    filterCat = chip.dataset.cat || '';
    renderChips(); renderList();
  });
  // 头条 / 列表项点击：按钮优先，其余区域打开详情
  $('#news-hero').addEventListener('click', e => {
    const btn = e.target.closest('button[data-act]');
    if (btn) { handleAct(btn); return; }
    const hero = e.target.closest('.news-hero');
    if (hero) openDetail(hero.dataset.id);
  });
  $('#news-list').addEventListener('click', e => {
    const btn = e.target.closest('button[data-act]');
    if (btn) { handleAct(btn); return; }
    const item = e.target.closest('.news-item');
    if (item) openDetail(item.dataset.id);
  });

  renderChips();
  renderList();
});

/* ---------- 分类筛选标签 ---------- */
function renderChips() {
  $('#chips').innerHTML = ['全部', ...NEWS_CATS].map(c =>
    `<button class="chip ${(!filterCat && c === '全部') || filterCat === c ? 'active' : ''}" data-cat="${c === '全部' ? '' : c}">${c}</button>`
  ).join('');
}

/* ---------- 列表 ---------- */
function getFiltered() {
  const kw = $('#kw').value.trim().toLowerCase();
  return DB.news.filter(n =>
    (!filterCat || n.category === filterCat) &&
    (!kw || n.title.toLowerCase().includes(kw) || (n.summary || '').toLowerCase().includes(kw))
  );
}

function renderList() {
  const list = getFiltered().slice().sort((a, b) => (b.top - a.top) || b.date.localeCompare(a.date));
  const hero = list.find(n => n.top) || null;
  const rest = hero ? list.filter(n => n !== hero) : list;

  // 置顶头条
  $('#news-hero').innerHTML = hero ? `
    <div class="news-hero" data-id="${hero.id}">
      <span class="hero-cat">${esc(hero.category)}</span>
      <div class="news-hero-title">${esc(hero.title)}</div>
      <div class="news-hero-summary">${esc(hero.summary)}</div>
      <div class="news-hero-meta">
        <span>${esc(hero.date)}</span>
        <span>${esc(hero.author)} 发布</span>
        <span>${hero.views || 0} 次阅读</span>
        <span class="hero-more">阅读全文 ${ICONS.arrow}</span>
      </div>
    </div>` : '';

  // 其余新闻
  $('#news-list').innerHTML = rest.length ? rest.map(n => {
    const meta = CAT_META[n.category] || CAT_META['机构动态'];
    return `
    <div class="news-item" data-id="${n.id}">
      <div class="news-cat-block" style="background:${meta.color}">${ICONS[meta.icon]}</div>
      <div class="news-main">
        <div class="news-title">${esc(n.title)}${n.top ? '<span class="top-flag">置顶</span>' : ''}${n.status === '草稿' ? '<span class="top-flag draft">草稿</span>' : ''}</div>
        <div class="news-summary clamp-2">${esc(n.summary)}</div>
        <div class="news-meta">
          <span>${esc(n.category)}</span><span>${esc(n.date)}</span><span>${esc(n.author)}</span><span>${n.views || 0} 次阅读</span>
        </div>
      </div>
      <div class="news-side">
        <div class="news-date">${esc((n.date || '').slice(5))}</div>
        ${canWrite ? `<div class="news-item-actions">
          <button class="btn-link" data-act="edit" data-id="${n.id}">${ICONS.edit}编辑</button>
          <button class="btn-link danger" data-act="del" data-id="${n.id}">${ICONS.trash}删除</button>
        </div>` : ''}
      </div>
    </div>`;
  }).join('') : `
    <div class="card" style="padding:44px;text-align:center;color:var(--muted)">
      ${ICONS.empty}<div style="margin-top:8px">暂无新闻，点击右上角「发布资讯」创建第一条吧</div>
    </div>`;
}

/* ---------- 详情（阅读量由后端 /news/{id}/view 累加并返回） ---------- */
async function openDetail(id) {
  if (!byId(DB.news, id)) return;
  const n = await apiOk(() => api.newsView(id), '');
  if (!n) return;
  const idx = DB.news.findIndex(x => x.id === id);
  if (idx > -1) DB.news[idx] = n;
  renderList();
  $('#detail-body').innerHTML = `
    <div class="news-detail-title">${esc(n.title)}</div>
    <div class="news-detail-meta">
      ${badge(n.category)}<span>${esc(n.date)}</span><span>作者：${esc(n.author)}</span><span>${n.views} 次阅读</span>
    </div>
    <div class="news-detail-body">
      ${(n.content && n.content.length ? n.content : ['（暂无正文）']).map(p => `<p>${esc(p)}</p>`).join('')}
    </div>`;
  openModal('detail-modal');
}

/* ---------- 编辑 / 删除 ---------- */
function handleAct(btn) {
  const { act, id } = btn.dataset;
  if (!canWrite) { showToast('您没有权限发布或维护资讯', 'error'); return; }
  const n = byId(DB.news, id);
  if (!n) return;
  if (act === 'edit') {
    openEditor(n);
  } else if (act === 'del') {
    askConfirm('删除新闻', `确定删除「${n.title}」吗？删除后不可恢复。`, async () => {
      if (!await apiOk(() => api.remove('news', id))) return;
      await hydrate(); renderList();
      showToast('新闻已删除');
    });
  }
}

function openEditor(n) {
  currentEditId = n ? n.id : null;
  $('#modal-title').textContent = n ? '编辑新闻' : '发布新闻';
  $('#f-title').value = n ? n.title : '';
  $('#f-cat').value = n ? n.category : '机构动态';
  $('#f-top').value = n && n.top ? '是' : '否';
  $('#f-date').value = n ? n.date : todayStr();
  $('#f-author').value = n ? n.author : ((getSessionUser() || {}).name || '');
  $('#f-summary').value = n ? (n.summary || '') : '';
  $('#f-content').value = n ? (n.content || []).join('\n') : '';
  $('#f-status-edit').value = n ? n.status : '已发布';
  openModal('editor-modal');
  $('#f-title').focus();
}

async function submitForm() {
  const title = $('#f-title');
  const date = $('#f-date');
  const author = $('#f-author');
  const summary = $('#f-summary');
  const content = $('#f-content');
  if (!valid([[title, '新闻标题'], [date, '发布日期'], [author, '作者'], [summary, '摘要'], [content, '正文内容']])) return;

  const isEdit = !!currentEditId;
  const data = {
    title: title.value.trim(),
    category: $('#f-cat').value,
    top: $('#f-top').value === '是',
    date: date.value,
    author: author.value.trim(),
    status: $('#f-status-edit').value,
    summary: summary.value.trim(),
    content: content.value.split(/\n+/).map(s => s.trim()).filter(Boolean)
  };

  if (!await apiOk(() => isEdit ? api.update('news', currentEditId, data) : api.create('news', data))) return;
  await hydrate();
  closeModal('editor-modal');
  renderList();
  showToast(isEdit ? '新闻已更新' : '新闻发布成功');
}

