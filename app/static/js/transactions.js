import { api, categoryIcon, escapeHtml, getCategories, initTransactionActions, money } from './app.js';

const filterForm = document.querySelector('#transaction-filters');
const list = document.querySelector('#transaction-list');
let page = 1;
let openTransaction;

function selectedValues(name) {
  return [...filterForm.querySelectorAll(`[name="${name}"]:checked`)].map((input) => input.value);
}

async function loadTransactions() {
  list.className = 'loading-block'; list.textContent = '正在读取…';
  const params = new URLSearchParams({ page: String(page) });
  for (const name of ['keyword', 'start_date', 'end_date']) {
    if (filterForm.elements[name].value) params.set(name, filterForm.elements[name].value);
  }
  const types = selectedValues('types'); if (types.length) params.set('types', types.join(','));
  const categories = selectedValues('category_ids'); if (categories.length) params.set('category_ids', categories.join(','));
  try {
    const data = await api(`/api/transactions?${params}`);
    document.querySelector('#transaction-total').textContent = `共 ${data.pagination.total_items} 笔`;
    list.className = '';
    if (!data.items.length) list.innerHTML = '<div class="empty-state">没有符合条件的流水</div>';
    else list.innerHTML = `<div class="desktop-table"><table><thead><tr><th>日期</th><th>分类</th><th>备注</th><th class="align-right">金额</th><th></th></tr></thead><tbody>${data.items.map(rowMarkup).join('')}</tbody></table></div><div class="mobile-cards">${data.items.map(cardMarkup).join('')}</div>`;
    list.querySelectorAll('[data-id]').forEach((node) => node.addEventListener('click', async (event) => {
      if (event.target.closest('button') || node.classList.contains('transaction-card')) {
        const item = await api(`/api/transactions/${node.dataset.id}`); openTransaction(item);
      }
    }));
    list.querySelectorAll('.transaction-card').forEach((node) => node.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); node.click(); }
    }));
    renderPagination(data.pagination);
  } catch (error) { list.className = 'error-state'; list.textContent = error.message; }
}

function rowMarkup(item) {
  const sign = item.transaction_type === 'income' ? '+' : '−';
  return `<tr data-id="${item.id}"><td>${item.occurred_on}</td><td><span class="category-cell">${categoryIcon(item.category, 'small')}<strong>${item.category.name}</strong></span></td><td class="note-cell">${item.note ? escapeHtml(item.note) : '<span class="muted">无备注</span>'}</td><td class="align-right amount ${item.transaction_type}">${sign}${money(item.amount)}</td><td class="align-right"><button class="icon-button edit-button" aria-label="编辑流水">›</button></td></tr>`;
}

function cardMarkup(item) {
  const sign = item.transaction_type === 'income' ? '+' : '−';
  return `<article class="transaction-card" data-id="${item.id}" tabindex="0">${categoryIcon(item.category)}<div class="transaction-card-main"><strong>${item.category.name}</strong><span>${item.occurred_on}${item.note ? ` · ${escapeHtml(item.note)}` : ''}</span></div><strong class="amount ${item.transaction_type}">${sign}${money(item.amount)}</strong></article>`;
}

function renderPagination(pagination) {
  const nav = document.querySelector('#pagination');
  if (pagination.total_pages <= 1) { nav.innerHTML = ''; return; }
  nav.innerHTML = `<button class="button secondary" ${pagination.page <= 1 ? 'disabled' : ''} data-page="${pagination.page - 1}">上一页</button><span>第 ${pagination.page} / ${pagination.total_pages} 页</span><button class="button secondary" ${pagination.page >= pagination.total_pages ? 'disabled' : ''} data-page="${pagination.page + 1}">下一页</button>`;
  nav.querySelectorAll('[data-page]').forEach((button) => button.addEventListener('click', () => { page = Number(button.dataset.page); loadTransactions(); }));
}

const categories = await getCategories();
document.querySelector('#category-filter').innerHTML = categories.map((item) => `<label class="check-chip"><input type="checkbox" name="category_ids" value="${item.id}"><span>${item.name}</span></label>`).join('');
filterForm.addEventListener('submit', (event) => { event.preventDefault(); page = 1; loadTransactions(); });
filterForm.querySelectorAll('input[type="checkbox"], input[type="date"]').forEach((input) => input.addEventListener('change', () => { page = 1; loadTransactions(); }));
document.querySelector('#reset-filters').addEventListener('click', () => { filterForm.reset(); page = 1; loadTransactions(); });
({ openTransaction } = await initTransactionActions(loadTransactions));
await loadTransactions();
