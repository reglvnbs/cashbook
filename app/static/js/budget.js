import { api, categoryIcon, money } from './app.js';

const monthInput = document.querySelector('#budget-month');
const content = document.querySelector('#budget-content');
const errorNode = document.querySelector('#budget-error');
let budgetData = null;
let editing = false;

function tone(percent) {
  if (percent > 100) return 'over';
  if (percent >= 80) return 'warning';
  return '';
}

function progress(entry) {
  if (entry.amount === null) return '<span class="muted">未设置</span>';
  return `<div class="usage ${tone(entry.usage_percent)}"><div class="progress-track"><span style="width:${Math.min(entry.usage_percent, 100)}%"></span></div><small>${entry.usage_percent.toFixed(2)}%</small></div>`;
}

function render() {
  content.className = '';
  const total = budgetData.total_budget;
  const totalAmount = editing ? `<label class="budget-input"><span>¥</span><input data-total inputmode="decimal" value="${total.amount || ''}" placeholder="未设置"></label>` : `<strong>${total.amount ? money(total.amount) : '未设置'}</strong>`;
  content.innerHTML = `<article class="total-budget ${tone(total.usage_percent)}"><div><p>总预算</p>${totalAmount}</div><div><p>已使用</p><strong>${money(total.used)}</strong></div><div><p>剩余</p><strong>${total.remaining !== null ? money(total.remaining) : '—'}</strong></div><div class="total-progress">${progress(total)}</div></article>
    <div class="category-budget-heading"><h3>分类预算</h3><span>本月支出与预算使用情况</span></div>
    <div class="category-budget-list">${budgetData.category_budgets.map((item) => `<article class="category-budget-row ${tone(item.usage_percent)}" data-category-id="${item.category.id}">
      ${categoryIcon(item.category)}<div class="category-budget-name"><strong>${item.category.name}</strong><span>已用 ${money(item.used)}</span></div><div class="category-budget-progress">${progress(item)}</div><div class="category-budget-amount">${editing ? `<label class="budget-input small"><span>¥</span><input inputmode="decimal" value="${item.amount || ''}" placeholder="未设置"></label>` : `<strong>${item.amount ? money(item.amount) : '未设置'}</strong><span>${item.remaining !== null ? `剩余 ${money(item.remaining)}` : ''}</span>`}</div>
    </article>`).join('')}</div>`;
  document.querySelector('#budget-view-actions').hidden = editing;
  document.querySelector('#budget-edit-actions').hidden = !editing;
}

async function loadBudget() {
  editing = false; errorNode.textContent = ''; content.className = 'loading-block'; content.textContent = '正在读取…';
  try { budgetData = await api(`/api/budgets/${monthInput.value}`); render(); }
  catch (error) { content.className = 'error-state'; content.textContent = error.message; }
}

monthInput.addEventListener('change', loadBudget);
document.querySelector('#edit-budget').addEventListener('click', () => { editing = true; render(); });
document.querySelector('#cancel-budget').addEventListener('click', () => { editing = false; errorNode.textContent = ''; render(); });
document.querySelector('#save-budget').addEventListener('click', async () => {
  errorNode.textContent = '';
  const categoryBudgets = [...content.querySelectorAll('[data-category-id]')].map((row) => ({ category_id: Number(row.dataset.categoryId), amount: row.querySelector('input').value || null }));
  const payload = { total_budget: content.querySelector('[data-total]').value || null, category_budgets: categoryBudgets };
  try { budgetData = await api(`/api/budgets/${monthInput.value}`, { method: 'PUT', body: JSON.stringify(payload) }); editing = false; render(); }
  catch (error) { errorNode.textContent = error.message; }
});
await loadBudget();

