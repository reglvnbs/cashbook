import { api, categoryIcon, initTransactionActions, money } from './app.js';

const dateForm = document.querySelector('#overview-date-form');
const categoryList = document.querySelector('#expense-categories');

function budgetClass(percent) {
  if (percent > 100) return 'over';
  if (percent >= 80) return 'warning';
  return '';
}

async function loadOverview() {
  categoryList.className = 'category-breakdown loading-block';
  categoryList.textContent = '正在读取…';
  const params = new URLSearchParams();
  if (dateForm.elements.start_date.value && dateForm.elements.end_date.value) {
    params.set('start_date', dateForm.elements.start_date.value);
    params.set('end_date', dateForm.elements.end_date.value);
  }
  try {
    const data = await api(`/api/overview?${params}`);
    dateForm.elements.start_date.value = data.date_range.start_date;
    dateForm.elements.end_date.value = data.date_range.end_date;
    const cards = document.querySelectorAll('.summary-card strong');
    cards[0].textContent = money(data.summary.balance);
    cards[1].textContent = `+${money(data.summary.income)}`;
    cards[2].textContent = `−${money(data.summary.expense)}`;
    document.querySelector('#expense-total').textContent = `合计 ${money(data.summary.expense)}`;
    categoryList.className = 'category-breakdown';
    categoryList.innerHTML = data.expense_categories.length ? data.expense_categories.map((item) => `<article class="breakdown-row">
      ${categoryIcon(item.category)}<div class="breakdown-main"><div class="breakdown-label"><strong>${item.category.name}</strong><span>${item.percentage.toFixed(2)}%</span></div><div class="progress-track"><span style="width:${Math.min(item.percentage, 100)}%;--category:${item.category.color}"></span></div></div><strong class="breakdown-amount">${money(item.amount)}</strong>
    </article>`).join('') : '<div class="empty-state">所选日期内暂无支出</div>';
    const panel = document.querySelector('#budget-summary-panel');
    if (!data.budget_summary) { panel.hidden = true; }
    else {
      panel.hidden = false;
      const total = data.budget_summary.total_budget;
      const noBudget = total.amount !== null && Number(total.amount) === 0;
      document.querySelector('#budget-summary').innerHTML = noBudget ? `<div class="budget-summary-card no-budget">
        <div><span>已使用</span><strong>${money(total.used)}</strong></div><div><span>总预算</span><strong>没有预算</strong></div><div><span>剩余</span><strong>${money(total.remaining)}</strong></div>
        <div class="progress-track budget-progress"><span></span></div><p>100%</p>
      </div>` : total.amount ? `<div class="budget-summary-card ${budgetClass(total.usage_percent)}">
        <div><span>已使用</span><strong>${money(total.used)}</strong></div><div><span>总预算</span><strong>${money(total.amount)}</strong></div><div><span>剩余</span><strong>${money(total.remaining)}</strong></div>
        <div class="progress-track budget-progress"><span style="width:${Math.min(total.usage_percent, 100)}%"></span></div><p>已使用 ${total.usage_percent.toFixed(2)}%</p>
      </div>` : `<div class="budget-summary-card unset">
        <div><span>已使用</span><strong>${money(total.used)}</strong></div><div><span>总预算</span><strong>未设置</strong></div><div><span>剩余</span><strong>—</strong></div>
        <div class="progress-track budget-progress"><span></span></div><p>未设置预算</p>
      </div>`;
    }
  } catch (error) {
    categoryList.className = 'error-state'; categoryList.textContent = error.message;
  }
}

dateForm.addEventListener('submit', (event) => { event.preventDefault(); loadOverview(); });
await initTransactionActions(loadOverview);
await loadOverview();
