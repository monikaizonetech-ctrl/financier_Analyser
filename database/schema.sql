-- ProAnalyser PostgreSQL schema
-- NOTE: the backend also auto-creates these tables via SQLAlchemy (Base.metadata.create_all)
-- the first time it starts. This file is provided as a reference / for manual setup.

CREATE TYPE user_role AS ENUM ('Admin', 'Manager', 'Member');
CREATE TYPE user_status AS ENUM ('Active', 'Inactive', 'Pending');

CREATE TABLE users (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20),
    hashed_password VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'Member',
    status          user_status NOT NULL DEFAULT 'Active',
    added_by_id     VARCHAR(36) REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TYPE report_type AS ENUM ('BSA', 'GST', 'ITR');
CREATE TYPE report_status AS ENUM ('Need to analyse', 'Processing', 'Ready to use', 'Failed');

CREATE TABLE reports (
    id              VARCHAR(36) PRIMARY KEY,
    reference_id    VARCHAR(64) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    report_type     report_type NOT NULL,
    status          report_status NOT NULL DEFAULT 'Need to analyse',
    owner_id        VARCHAR(36) NOT NULL REFERENCES users(id),
    result_summary  JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    analysed_at     TIMESTAMP
);

CREATE TYPE file_status AS ENUM ('Uploaded', 'Processing', 'Processed', 'Error');
CREATE TYPE file_authenticity AS ENUM ('Pending', 'Verified', 'Suspicious');

CREATE TABLE report_files (
    id                  VARCHAR(36) PRIMARY KEY,
    report_id           VARCHAR(36) NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    s_no                INTEGER NOT NULL,
    file_name           VARCHAR(255) NOT NULL,
    stored_path         VARCHAR(500) NOT NULL,
    sub_type            VARCHAR(50),
    year                VARCHAR(20),
    password_protected  BOOLEAN NOT NULL DEFAULT FALSE,
    file_status         file_status NOT NULL DEFAULT 'Uploaded',
    authenticity        file_authenticity NOT NULL DEFAULT 'Pending',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TYPE plan_type AS ENUM ('Free Trial', 'Paid Trial', 'Standard', 'Pro', 'Enterprise');
CREATE TYPE subscription_status AS ENUM ('Active', 'Expired', 'Cancelled');

CREATE TABLE subscriptions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) UNIQUE NOT NULL REFERENCES users(id),
    plan            plan_type NOT NULL DEFAULT 'Free Trial',
    status          subscription_status NOT NULL DEFAULT 'Active',
    credits_total   FLOAT NOT NULL DEFAULT 2.5,
    credits_used    FLOAT NOT NULL DEFAULT 0,
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMP NOT NULL
);

CREATE TYPE transaction_type AS ENUM ('Credit Purchase', 'Plan Upgrade', 'Refund');

CREATE TABLE transactions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id),
    type            transaction_type NOT NULL,
    amount          NUMERIC(10, 2) NOT NULL,
    description     VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_owner ON reports(owner_id);
CREATE INDEX idx_report_files_report ON report_files(report_id);
CREATE INDEX idx_users_added_by ON users(added_by_id);
CREATE INDEX idx_transactions_user ON transactions(user_id);
