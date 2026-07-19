const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
let categoryCache = null;

export async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrfToken);
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error?.message || '请求失败，请稍后重试');
    error.fields = payload.error?.fields || {};
    error.code = payload.error?.code;
    throw error;
  }
  return payload.data;
}

export async function getCategories() {
  if (!categoryCache) categoryCache = await api('/api/categories');
  return categoryCache;
}

export function money(value) {
  const number = Number(value || 0);
  return `¥${number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

const iconPaths = {
  1: '<path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M17 3v18M14 3c0 5 1 7 3 7"/>',
  2: '<path d="M3 11l18-7-7 18-3-8-8-3Z"/><path d="m11 14 4-4"/>',
  3: '<path d="M5 8h14l-1 13H6L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/>',
  4: '<path d="m3 11 9-8 9 8"/><path d="M5 10v11h14V10M9 21v-7h6v7"/>',
  5: '<path d="M8 8h8a5 5 0 0 1 5 5v3a3 3 0 0 1-5 2l-2-2h-4l-2 2a3 3 0 0 1-5-2v-3a5 5 0 0 1 5-5Z"/><path d="M7 12v4M5 14h4M16 13h.01M18 15h.01"/>',
  6: '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3Z"/>',
  7: '<path d="M4 5a7 7 0 0 1 8 2v14a7 7 0 0 0-8-2V5ZM20 5a7 7 0 0 0-8 2v14a7 7 0 0 1 8-2V5Z"/>',
  8: '<path d="m8 12 3 3a2 2 0 0 0 3 0l4-4"/><path d="m2 9 4-4 5 2 2-1 5 2 4 4-6 6a3 3 0 0 1-4 0L2 9Z"/>',
  9: '<path d="m3 6 7 7 4-4 7 7"/><path d="M21 11v5h-5"/>',
  10: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
  11: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/>',
  12: '<circle cx="12" cy="8" r="5"/><path d="m8 12-2 9 6-3 6 3-2-9"/>',
  13: '<path d="m3 18 7-7 4 4 7-9"/><path d="M16 6h5v5"/>',
  14: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M2 21h20M9 21v-4h6v4"/>',
  15: '<rect x="3" y="8" width="18" height="13" rx="2"/><path d="M12 8v13M3 12h18M7 8c-3 0-3-4-1-5 3-1 6 5 6 5M17 8c3 0 3-4 1-5-3-1-6 5-6 5"/>',
  16: '<path d="m9 14-4-4 4-4"/><path d="M5 10h9a5 5 0 0 1 5 5v3"/>',
  17: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
};

export function categoryIcon(category, size = 'normal') {
  const path = iconPaths[category.id] || '<circle cx="12" cy="12" r="8"/><path d="M8 12h8"/>';
  return `<span class="category-icon ${size}" style="--category:${category.color}"><svg viewBox="0 0 24 24" aria-hidden="true">${path}</svg></span>`;
}

function setError(container, error) {
  container.textContent = error?.message || '';
}

function fillCategorySelect(select, categories, type, selected) {
  select.innerHTML = categories.filter((item) => item.transaction_type === type)
    .map((item) => `<option value="${item.id}" ${Number(selected) === item.id ? 'selected' : ''}>${item.name}</option>`).join('');
}

export async function initTransactionActions(onSaved = () => location.reload()) {
  const formDialog = document.querySelector('#transaction-dialog');
  if (!formDialog) return { openTransaction: () => {} };
  const form = document.querySelector('#transaction-form');
  const formError = form.querySelector('.form-error');
  const deleteButton = document.querySelector('#delete-transaction');
  const aiDialog = document.querySelector('#ai-dialog');
  const categories = await getCategories();
  const today = document.body.dataset.today;
  form.elements.occurred_on.max = today;

  function openTransaction(transaction = null) {
    form.reset();
    formError.textContent = '';
    form.elements.id.value = transaction?.id || '';
    const type = transaction?.transaction_type || 'expense';
    form.querySelector(`[name="transaction_type"][value="${type}"]`).checked = true;
    form.elements.amount.value = transaction?.amount || '';
    form.elements.occurred_on.value = transaction?.occurred_on || today;
    form.elements.note.value = transaction?.note || '';
    fillCategorySelect(form.elements.category_id, categories, type, transaction?.category?.id);
    deleteButton.hidden = !transaction;
    document.querySelector('#transaction-dialog-title').textContent = transaction ? '编辑流水' : '记一笔';
    formDialog.showModal();
  }

  document.querySelectorAll('.js-manual-transaction').forEach((button) => button.addEventListener('click', () => openTransaction()));
  document.querySelectorAll('.js-ai-transaction').forEach((button) => button.addEventListener('click', () => {
    document.querySelector('#ai-input-stage').hidden = false;
    document.querySelector('#ai-draft-stage').hidden = true;
    aiDialog.querySelectorAll('.form-error').forEach((node) => { node.textContent = ''; });
    aiDialog.showModal();
  }));
  document.querySelectorAll('.sheet-dialog .js-close').forEach((button) => button.addEventListener('click', () => button.closest('dialog').close()));
  form.querySelectorAll('[name="transaction_type"]').forEach((radio) => radio.addEventListener('change', () => fillCategorySelect(form.elements.category_id, categories, radio.value)));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setError(formError);
    const id = form.elements.id.value;
    const data = {
      transaction_type: new FormData(form).get('transaction_type'),
      amount: form.elements.amount.value,
      category_id: Number(form.elements.category_id.value),
      occurred_on: form.elements.occurred_on.value,
      note: form.elements.note.value,
    };
    try {
      await api(id ? `/api/transactions/${id}` : '/api/transactions', { method: id ? 'PUT' : 'POST', body: JSON.stringify(data) });
      formDialog.close();
      onSaved();
    } catch (error) { setError(formError, error); }
  });

  deleteButton.addEventListener('click', async () => {
    const id = form.elements.id.value;
    if (!id || !confirm('确定删除这笔流水吗？删除后无法恢复。')) return;
    try {
      await api(`/api/transactions/${id}`, { method: 'DELETE' });
      formDialog.close();
      onSaved();
    } catch (error) { setError(formError, error); }
  });

  const inputStage = document.querySelector('#ai-input-stage');
  const draftStage = document.querySelector('#ai-draft-stage');
  const draftList = document.querySelector('#draft-list');
  function renderDrafts(drafts) {
    draftList.innerHTML = drafts.map((draft, index) => `<article class="draft-card" data-index="${index}">
      <div class="draft-card-head"><strong>流水 ${index + 1}</strong><button type="button" class="text-button danger remove-draft">移除</button></div>
      <div class="draft-fields">
        <label class="field"><span>收支</span><select name="transaction_type"><option value="expense" ${draft.transaction_type === 'expense' ? 'selected' : ''}>支出</option><option value="income" ${draft.transaction_type === 'income' ? 'selected' : ''}>收入</option></select></label>
        <label class="field"><span>金额</span><input name="amount" inputmode="decimal" value="${draft.amount}" required></label>
        <label class="field"><span>分类</span><select name="category_id"></select></label>
        <label class="field"><span>日期</span><input name="occurred_on" type="date" max="${today}" value="${draft.occurred_on}" required></label>
        <label class="field draft-note"><span>备注</span><input name="note" maxlength="200" value="${escapeHtml(draft.note)}"></label>
      </div>
    </article>`).join('');
    draftList.querySelectorAll('.draft-card').forEach((card, index) => {
      const type = card.querySelector('[name="transaction_type"]');
      const category = card.querySelector('[name="category_id"]');
      fillCategorySelect(category, categories, type.value, drafts[index].category_id);
      type.addEventListener('change', () => fillCategorySelect(category, categories, type.value));
      card.querySelector('.remove-draft').addEventListener('click', () => { card.remove(); updateDraftCount(); });
    });
    updateDraftCount();
  }
  function updateDraftCount() { document.querySelector('#draft-count').textContent = `${draftList.children.length} 笔`; }

  document.querySelector('#parse-ai').addEventListener('click', async () => {
    const errorNode = inputStage.querySelector('.form-error');
    setError(errorNode);
    const button = document.querySelector('#parse-ai');
    button.disabled = true; button.textContent = '识别中…';
    try {
      const data = await api('/api/ai/parse', { method: 'POST', body: JSON.stringify({ text: document.querySelector('#ai-text').value }) });
      renderDrafts(data.drafts); inputStage.hidden = true; draftStage.hidden = false;
    } catch (error) { setError(errorNode, error); }
    finally { button.disabled = false; button.textContent = '识别流水'; }
  });
  document.querySelector('#back-to-ai-input').addEventListener('click', () => { draftStage.hidden = true; inputStage.hidden = false; });
  document.querySelector('#save-ai-drafts').addEventListener('click', async () => {
    const errorNode = draftStage.querySelector('.form-error');
    setError(errorNode);
    const cards = [...draftList.querySelectorAll('.draft-card')];
    if (!cards.length) { errorNode.textContent = '请至少保留一笔流水'; return; }
    const transactions = cards.map((card) => ({
      transaction_type: card.querySelector('[name="transaction_type"]').value,
      amount: card.querySelector('[name="amount"]').value,
      category_id: Number(card.querySelector('[name="category_id"]').value),
      occurred_on: card.querySelector('[name="occurred_on"]').value,
      note: card.querySelector('[name="note"]').value,
    }));
    try {
      await api('/api/transactions/batch', { method: 'POST', body: JSON.stringify({ transactions }) });
      aiDialog.close(); onSaved();
    } catch (error) { setError(errorNode, error); }
  });
  return { openTransaction };
}

window.Cashbook = { api, getCategories, money, escapeHtml, categoryIcon, initTransactionActions };
