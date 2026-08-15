-- ============================================================
-- EXPENSE TRACKING SERVICE — FULL DATABASE SCHEMA
-- PostgreSQL
-- DDD-aligned version
-- ============================================================


-- ============================================================
-- USERS
-- Aggregate root. user_id throughout the schema is a typed
-- domain identity referencing this table (enforced via FK).
-- ============================================================
CREATE TABLE users (
    id           SERIAL        PRIMARY KEY,
    email        VARCHAR(256)  NOT NULL UNIQUE,
    display_name VARCHAR(128)  NOT NULL,
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    version      INT           NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);


-- ============================================================
-- CURRENCIES
-- ============================================================
CREATE TABLE currencies (
    id          SERIAL       PRIMARY KEY,
    code        CHAR(3)      NOT NULL UNIQUE,   -- ISO 4217: USD, EUR, PLN
    name        VARCHAR(64)  NOT NULL,
    symbol      VARCHAR(8)   NOT NULL,
    decimals    SMALLINT     NOT NULL DEFAULT 2, -- JPY=0, USD/EUR=2, KWD=3
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- ============================================================
-- CATEGORIES
-- User-owned aggregate. Every category belongs to exactly one
-- user. Users create and manage all categories themselves —
-- there are no system-defined defaults.
-- ============================================================
CREATE TABLE categories (
    id          SERIAL       PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id),
    parent_id   INT          REFERENCES categories(id) ON DELETE SET NULL,
    code        CHAR(8)      NOT NULL,
    name        VARCHAR(64)  NOT NULL,
    icon        VARCHAR(32),
    type        VARCHAR(8)   NOT NULL CHECK (type IN ('expense', 'income', 'both')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    version     INT          NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, code)
);


-- ============================================================
-- ACCOUNTS
-- ============================================================
CREATE TABLE accounts (
    id          SERIAL       PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id),
    currency_id INT          NOT NULL REFERENCES currencies(id),
    code        CHAR(8)      NOT NULL,
    name        VARCHAR(64)  NOT NULL,
    type        VARCHAR(16)  NOT NULL CHECK (type IN ('cash', 'bank', 'credit', 'savings')),
    icon        VARCHAR(32),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    version     INT          NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, code)
);


-- ============================================================
-- TRANSACTIONS
-- amount is always positive; direction drives in/ex semantics.
-- balance is NOT stored here — derive it via SUM on read (DDD).
-- currency is NOT stored here — it is owned by the account
-- (accounts.currency_id). Derive Money(amount, account.currency)
-- in the domain layer. This assumes a transaction's currency
-- always matches its account's currency (no per-transaction FX).
-- comment is capped at 1000 chars; validation of content is the
-- application layer's responsibility.
-- ============================================================
CREATE TABLE transactions (
    id            SERIAL         PRIMARY KEY,
    user_id       INT            NOT NULL REFERENCES users(id),
    account_id    INT            NOT NULL REFERENCES accounts(id),
    category_id   INT            REFERENCES categories(id) ON DELETE SET NULL,
    amount        NUMERIC(18, 4) NOT NULL CHECK (amount > 0),
    direction     VARCHAR(6)     NOT NULL CHECK (direction IN ('debit', 'credit')),
    comment       VARCHAR(1000),
    is_active     BOOLEAN        NOT NULL DEFAULT TRUE,
    version       INT            NOT NULL DEFAULT 1,
    transacted_at TIMESTAMPTZ    NOT NULL,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ    NOT NULL DEFAULT now()
);


-- ============================================================
-- TRANSFERS
-- Immutable correlation record linking two transaction legs.
-- No updated_at (immutable by design — enforced via trigger below).
-- Soft-delete is handled via the transaction legs' is_active flag.
-- comment lives on transaction legs.
-- ============================================================
CREATE TABLE transfers (
    id          SERIAL      PRIMARY KEY,
    from_tx_id  INT         NOT NULL UNIQUE REFERENCES transactions(id),
    to_tx_id    INT         NOT NULL UNIQUE REFERENCES transactions(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- INDEXES
-- ============================================================

-- users
CREATE INDEX idx_users_email                 ON users(email);
CREATE INDEX idx_users_active                ON users(id) WHERE is_active = TRUE;

-- transactions
CREATE INDEX idx_transactions_account_date   ON transactions(account_id, transacted_at DESC);
CREATE INDEX idx_transactions_user_date      ON transactions(user_id, transacted_at DESC);
CREATE INDEX idx_transactions_category       ON transactions(category_id);
CREATE INDEX idx_transactions_active         ON transactions(user_id, transacted_at DESC) WHERE is_active = TRUE;

-- accounts
CREATE INDEX idx_accounts_user               ON accounts(user_id);
CREATE INDEX idx_accounts_user_active        ON accounts(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_accounts_currency           ON accounts(currency_id);

-- categories
CREATE INDEX idx_categories_user             ON categories(user_id);
CREATE INDEX idx_categories_user_active      ON categories(user_id, type) WHERE is_active = TRUE;
CREATE INDEX idx_categories_parent           ON categories(parent_id) WHERE parent_id IS NOT NULL;

-- transfers
CREATE INDEX idx_transfers_from_tx           ON transfers(from_tx_id);
CREATE INDEX idx_transfers_to_tx             ON transfers(to_tx_id);


-- ============================================================
-- TRIGGER: auto-update updated_at on row change.
-- Attached to all tables that have an updated_at column.
-- transfers is intentionally excluded (immutable by design).
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_currencies_updated_at
    BEFORE UPDATE ON currencies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- TRIGGER: increment version on row change (optimistic locking).
-- Include version in WHERE clause on UPDATE to detect conflicts:
--   UPDATE ... WHERE id = $1 AND version = $2
-- If 0 rows affected, a concurrent update occurred — retry or raise.
-- ============================================================
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_version
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER trg_accounts_version
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER trg_categories_version
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER trg_transactions_version
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION increment_version();


-- ============================================================
-- TRIGGER: block hard deletes — enforce soft-delete contract.
-- Use is_active = FALSE instead of DELETE on these tables.
-- ============================================================
CREATE OR REPLACE FUNCTION prevent_hard_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Hard delete is not allowed on %. Set is_active = FALSE instead.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_no_delete
    BEFORE DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();

CREATE TRIGGER trg_currencies_no_delete
    BEFORE DELETE ON currencies
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();

CREATE TRIGGER trg_categories_no_delete
    BEFORE DELETE ON categories
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();

CREATE TRIGGER trg_accounts_no_delete
    BEFORE DELETE ON accounts
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();

CREATE TRIGGER trg_transactions_no_delete
    BEFORE DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();


-- ============================================================
-- TRIGGER: enforce immutability of transfers.
-- transfers has no updated_at by design; any UPDATE is a bug.
-- ============================================================
CREATE OR REPLACE FUNCTION prevent_transfer_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'transfers is immutable. Soft-delete via the linked transaction legs instead.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transfers_no_update
    BEFORE UPDATE ON transfers
    FOR EACH ROW EXECUTE FUNCTION prevent_transfer_update();