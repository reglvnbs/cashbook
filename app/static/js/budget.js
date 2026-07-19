import { api, categoryIcon, money } from './app.js';

const monthInput = document.querySelector('#budget-month');
const content = document.querySelector('#budget-content');
const errorNode = document.querySelector('#budget-error');
const monthTrigger = document.querySelector('#budget-month-trigger');
const monthLabel = document.querySelector('#budget-month-label');
const monthMenu = document.querySelector('#month-menu');
const pickerYear = document.querySelector('#picker-year');
let budgetData = null;
let editing = false;
let displayedYear = Number(monthInput.value.slice(0, 4));

function tone(percent) {
  if (percent > 100) return 'over';
  if (percent >= 80) return 'warning';
  return '';
}

function hasNoBudget(entry) {
  return entry.amount !== null && Number(entry.amount) === 0;
}

function progress(entry) {
  if (hasNoBudget(entry)) return '<div class="usage no-budget"><div class="progress-track"><span></span></div><small>100%</small></div>';
  if (entry.amount === null) return '<div class="usage unset"><div class="progress-track"><span></span></div><small>未设置</small></div>';
  return `<div class="usage ${tone(entry.usage_percent)}"><div class="progress-track"><span style="width:${Math.min(entry.usage_percent, 100)}%"></span></div><small>${entry.usage_percent.toFixed(2)}%</small></div>`;
}

function renderMonthPicker() {
  const [selectedYear, selectedMonth] = monthInput.value.split('-').map(Number);
  monthLabel.textContent = `${selectedYear}年${selectedMonth}月`;
  pickerYear.textContent = `${displayedYear}年`;
  monthMenu.querySelectorAll('[data-month]').forEach((button) => {
    const active = displayedYear === selectedYear && Number(button.dataset.month) === selectedMonth;
    button.classList.toggle('active', active);
    button.setAttribute('aria-current', active ? 'date' : 'false');
  });
}

function closeMonthMenu() {
  monthMenu.hidden = true;
  monthTrigger.setAttribute('aria-expanded', 'false');
}

function selectMonth(year, month) {
  monthInput.value = `${year}-${String(month).padStart(2, '0')}`;
  displayedYear = year;
  renderMonthPicker();
  closeMonthMenu();
  loadBudget();
}

function shiftMonth(offset) {
  const [year, month] = monthInput.value.split('-').map(Number);
  const target = new Date(year, month - 1 + offset, 1);
  selectMonth(target.getFullYear(), target.getMonth() + 1);
}

function render() {
  content.className = '';
  const total = budgetData.total_budget;
  const totalAmount = editing ? `<label class="budget-input"><span>¥</span><input data-total inputmode="decimal" value="${total.amount ?? ''}" placeholder="未设置"></label>` : `<strong>${total.amount === null ? '未设置' : hasNoBudget(total) ? '没有预算' : money(total.amount)}</strong>`;
  const totalTone = hasNoBudget(total) ? 'no-budget' : tone(total.usage_percent);
  content.innerHTML = `<article class="total-budget ${totalTone}"><div><p>总预算</p>${totalAmount}</div><div><p>已使用</p><strong>${money(total.used)}</strong></div><div><p>剩余</p><strong>${total.remaining !== null ? money(total.remaining) : '—'}</strong></div><div class="total-progress">${progress(total)}</div></article>
    <div class="category-budget-heading"><h3>分类预算</h3><span>本月支出与预算使用情况</span></div>
    <div class="category-budget-list">${budgetData.category_budgets.map((item) => {
      const itemTone = hasNoBudget(item) ? 'no-budget' : tone(item.usage_percent);
      const itemAmount = item.amount === null ? '未设置' : hasNoBudget(item) ? '没有预算' : money(item.amount);
      return `<article class="category-budget-row ${itemTone}" data-category-id="${item.category.id}">
        ${categoryIcon(item.category)}<div class="category-budget-name"><strong>${item.category.name}</strong><span>已用 ${money(item.used)}</span></div><div class="category-budget-progress">${progress(item)}</div><div class="category-budget-amount">${editing ? `<label class="budget-input small"><span>¥</span><input inputmode="decimal" value="${item.amount ?? ''}" placeholder="未设置"></label>` : `<strong>${itemAmount}</strong><span>${item.remaining !== null ? `剩余 ${money(item.remaining)}` : ''}</span>`}</div>
      </article>`;
    }).join('')}</div>`;
  document.querySelector('#budget-view-actions').hidden = editing;
  document.querySelector('#budget-edit-actions').hidden = !editing;
}

async function loadBudget() {
  editing = false; errorNode.textContent = ''; content.className = 'loading-block'; content.textContent = '正在读取…';
  try { budgetData = await api(`/api/budgets/${monthInput.value}`); render(); }
  catch (error) { content.className = 'error-state'; content.textContent = error.message; }
}

monthTrigger.addEventListener('click', () => {
  const opening = monthMenu.hidden;
  monthMenu.hidden = !opening;
  monthTrigger.setAttribute('aria-expanded', String(opening));
  if (opening) renderMonthPicker();
});
document.querySelector('#previous-month').addEventListener('click', () => shiftMonth(-1));
document.querySelector('#next-month').addEventListener('click', () => shiftMonth(1));
document.querySelector('#previous-year').addEventListener('click', () => { displayedYear -= 1; renderMonthPicker(); });
document.querySelector('#next-year').addEventListener('click', () => { displayedYear += 1; renderMonthPicker(); });
monthMenu.querySelectorAll('[data-month]').forEach((button) => button.addEventListener('click', () => selectMonth(displayedYear, Number(button.dataset.month))));
document.addEventListener('click', (event) => { if (!event.target.closest('.month-picker')) closeMonthMenu(); });
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMonthMenu(); });
document.querySelector('#edit-budget').addEventListener('click', () => { editing = true; render(); });
document.querySelector('#cancel-budget').addEventListener('click', () => { editing = false; errorNode.textContent = ''; render(); });
document.querySelector('#save-budget').addEventListener('click', async () => {
  errorNode.textContent = '';
  const categoryBudgets = [...content.querySelectorAll('[data-category-id]')].map((row) => ({ category_id: Number(row.dataset.categoryId), amount: row.querySelector('input').value || null }));
  const payload = { total_budget: content.querySelector('[data-total]').value || null, category_budgets: categoryBudgets };
  try { budgetData = await api(`/api/budgets/${monthInput.value}`, { method: 'PUT', body: JSON.stringify(payload) }); editing = false; render(); }
  catch (error) { errorNode.textContent = error.message; }
});
renderMonthPicker();
await loadBudget();
