-- 固定分类：编号是前后端共同使用的稳定标识，不可复用。
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    color TEXT NOT NULL CHECK (color GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'),
    UNIQUE (transaction_type, name)
);

-- 金额统一保存为整数分；应用层负责日期和备注长度的完整校验。
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    occurred_on TEXT NOT NULL CHECK (occurred_on GLOB '????-??-??'),
    note TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 200),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- category_id 为空表示该月总预算，否则表示支出分类预算。
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL CHECK (month GLOB '????-??'),
    category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    updated_at TEXT NOT NULL,
    UNIQUE (month, category_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_budgets_total_month
    ON budgets(month) WHERE category_id IS NULL;
CREATE INDEX IF NOT EXISTS ix_transactions_date
    ON transactions(occurred_on DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_type_date
    ON transactions(transaction_type, occurred_on DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_category_date
    ON transactions(category_id, occurred_on DESC);

-- SQLite 无法用普通 CHECK 跨表校验，触发器保证流水与分类类型一致。
CREATE TRIGGER IF NOT EXISTS trg_transactions_category_type_insert
BEFORE INSERT ON transactions
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM categories
    WHERE id = NEW.category_id AND transaction_type = NEW.transaction_type
)
BEGIN
    SELECT RAISE(ABORT, 'transaction category type mismatch');
END;

CREATE TRIGGER IF NOT EXISTS trg_transactions_category_type_update
BEFORE UPDATE OF transaction_type, category_id ON transactions
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM categories
    WHERE id = NEW.category_id AND transaction_type = NEW.transaction_type
)
BEGIN
    SELECT RAISE(ABORT, 'transaction category type mismatch');
END;

CREATE TRIGGER IF NOT EXISTS trg_budgets_expense_category_insert
BEFORE INSERT ON budgets
FOR EACH ROW
WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM categories WHERE id = NEW.category_id AND transaction_type = 'expense'
)
BEGIN
    SELECT RAISE(ABORT, 'budget category must be expense');
END;

CREATE TRIGGER IF NOT EXISTS trg_budgets_expense_category_update
BEFORE UPDATE OF category_id ON budgets
FOR EACH ROW
WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM categories WHERE id = NEW.category_id AND transaction_type = 'expense'
)
BEGIN
    SELECT RAISE(ABORT, 'budget category must be expense');
END;

INSERT OR IGNORE INTO categories (id, name, transaction_type, color) VALUES
    (1, '餐饮', 'expense', '#C77956'),
    (2, '交通', 'expense', '#5F86A6'),
    (3, '购物', 'expense', '#B96F87'),
    (4, '居住', 'expense', '#8173A2'),
    (5, '娱乐', 'expense', '#B58A45'),
    (6, '医疗', 'expense', '#5D948D'),
    (7, '学习', 'expense', '#6778A8'),
    (8, '人情', 'expense', '#B26767'),
    (9, '理财亏损', 'expense', '#9C6B6B'),
    (10, '其他支出', 'expense', '#7B818B'),
    (11, '工资', 'income', '#4F9278'),
    (12, '奖金', 'income', '#6D9A62'),
    (13, '理财收益', 'income', '#4F8F8A'),
    (14, '兼职', 'income', '#789151'),
    (15, '红包', 'income', '#A96370'),
    (16, '退款', 'income', '#588BA5'),
    (17, '其他收入', 'income', '#6F7B83');

