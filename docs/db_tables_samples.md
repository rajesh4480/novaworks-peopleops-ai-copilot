# SQLite DB Snapshot

- Database file: `backend/storage/hrms.db`
- Tables found: **22**
- Sample rows per table: **3**
- Source: uploaded `hrms.db` snapshot; schema and row counts below were read directly from this database.
- Sensitive sample values (password hashes, bank/tax identifiers, contact details, and personal dates/addresses) are redacted.

## Tables

- `ai_audit_logs`
- `alembic_version`
- `announcements`
- `attendance_logs`
- `departments`
- `employee_documents`
- `employee_projects`
- `employee_skills`
- `employees`
- `holidays`
- `hr_policies`
- `job_history`
- `leave_balances`
- `leave_requests`
- `onboarding_tasks`
- `payroll_records`
- `pending_action_confirmations`
- `poll_responses`
- `polls`
- `projects`
- `skills`
- `tickets`

## `ai_audit_logs`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `user_id` | `INTEGER` | 1 | 0 | `` |
| `role` | `VARCHAR(30)` | 1 | 0 | `` |
| `message` | `TEXT` | 1 | 0 | `` |
| `intent` | `VARCHAR(50)` | 1 | 0 | `` |
| `tool_name` | `VARCHAR(100)` | 1 | 0 | `` |
| `action_status` | `VARCHAR(30)` | 1 | 0 | `` |
| `records_accessed` | `INTEGER` | 1 | 0 | `'0'` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |
| `latency_ms` | `FLOAT` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 933)

| id | user_id | role | message | intent | tool_name | action_status | records_accessed | created_at | latency_ms |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | EMPLOYEE | AUDIT LOGGER TEST | test | audit_test | success | 1 | 2026-10-07 20:26:41 |  |
| 2 | 1 | ADMIN | How many casual leave days do I get? | policy_question | policy_rag | success | 1 | 2026-10-08 12:27:48 |  |
| 3 | 1 | ADMIN | How many employees are there? | sql_question | sql_agent | success | 1 | 2026-10-08 12:28:44 |  |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `user_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_ai_audit_logs_created_at` | 0 | c |
| `ix_ai_audit_logs_action_status` | 0 | c |
| `ix_ai_audit_logs_tool_name` | 0 | c |
| `ix_ai_audit_logs_intent` | 0 | c |
| `ix_ai_audit_logs_role` | 0 | c |
| `ix_ai_audit_logs_user_id` | 0 | c |
| `ix_ai_audit_logs_id` | 0 | c |

## `alembic_version`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `version_num` | `VARCHAR(32)` | 1 | 1 | `` |

### Sample Records (showing up to 3 of 1)

| version_num |
|---|
| bdfc4f3d0ad9 |

### Indexes

| name | unique | origin |
|---|---:|---|
| `sqlite_autoindex_alembic_version_1` | 1 | pk |

## `announcements`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `title` | `VARCHAR(180)` | 1 | 0 | `` |
| `body` | `TEXT` | 1 | 0 | `` |
| `author_id` | `INTEGER` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 11)

| id | title | body | author_id | created_at |
|---|---|---|---|---|
| 1 | Quarterly Townhall - Friday 4 PM | Join the all-hands townhall this Friday at 4 PM in the main hall and via livestream. | 1 | 2026-10-01 14:46:45 |
| 2 | Platform Sprint Planning | Sprint planning starts Monday 10 AM. Please update your task estimates before EOD Friday. | 2 | 2026-10-01 14:46:45 |
| 3 | Test Notice | This is a test announcement | 2 | 2026-10-13 14:56:03 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `author_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_announcements_created_at` | 0 | c |
| `ix_announcements_author_id` | 0 | c |
| `ix_announcements_title` | 0 | c |
| `ix_announcements_id` | 0 | c |

## `attendance_logs`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `date` | `DATE` | 1 | 0 | `` |
| `clock_in` | `TIME` | 0 | 0 | `` |
| `clock_out` | `TIME` | 0 | 0 | `` |
| `status` | `VARCHAR(7)` | 1 | 0 | `` |
| `work_mode` | `VARCHAR(20)` | 0 | 0 | `` |
| `punctuality` | `VARCHAR(20)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 22)

| id | employee_id | date | clock_in | clock_out | status | work_mode | punctuality |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 2026-09-30 | 09:00:00.000000 | 18:00:00.000000 | ON_TIME | PRESENT | ON_TIME |
| 2 | 1 | 2026-09-29 | 09:00:00.000000 | 18:00:00.000000 | ON_TIME | PRESENT | ON_TIME |
| 3 | 1 | 2026-09-28 | 09:10:00.000000 | 18:00:00.000000 | LATE | PRESENT | LATE |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_attendance_logs_punctuality` | 0 | c |
| `ix_attendance_logs_work_mode` | 0 | c |
| `ix_attendance_logs_status` | 0 | c |
| `ix_attendance_logs_id` | 0 | c |
| `ix_attendance_logs_employee_id` | 0 | c |
| `ix_attendance_logs_date` | 0 | c |

## `departments`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `location` | `VARCHAR(120)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 6)

| id | name | location |
|---|---|---|
| 1 | CEO | New York |
| 2 | Engineering | Bengaluru |
| 3 | Finance | London |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_departments_location` | 0 | c |
| `ix_departments_name` | 0 | c |
| `ix_departments_id` | 0 | c |

## `employee_documents`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `title` | `VARCHAR(220)` | 1 | 0 | `` |
| `document_type` | `VARCHAR(40)` | 1 | 0 | `` |
| `original_filename` | `VARCHAR(255)` | 1 | 0 | `` |
| `file_path` | `TEXT` | 1 | 0 | `` |
| `mime_type` | `VARCHAR(120)` | 1 | 0 | `` |
| `size_bytes` | `INTEGER` | 1 | 0 | `` |
| `checksum` | `VARCHAR(64)` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |
| `uploaded_by` | `INTEGER` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 0)

_No rows_

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |
| `uploaded_by` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_employee_documents_uploaded_by` | 0 | c |
| `ix_employee_documents_checksum` | 0 | c |
| `ix_employee_documents_id` | 0 | c |
| `ix_employee_documents_created_at` | 0 | c |
| `ix_employee_documents_document_type` | 0 | c |
| `ix_employee_documents_employee_id` | 0 | c |

## `employee_projects`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `project_id` | `INTEGER` | 1 | 0 | `` |
| `role_on_project` | `VARCHAR(120)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 2211)

| id | employee_id | project_id | role_on_project |
|---|---|---|---|
| 1 | 1 | 6 | HR Operations |
| 2 | 1 | 7 | Talent Specialist |
| 3 | 2 | 11 | Revenue Controller |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `project_id` | `projects` | `id` | `NO ACTION` | `NO ACTION` |
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_employee_projects_project_id` | 0 | c |
| `ix_employee_projects_employee_id` | 0 | c |
| `ix_employee_projects_id` | 0 | c |
| `sqlite_autoindex_employee_projects_1` | 1 | u |

## `employee_skills`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `skill_id` | `INTEGER` | 1 | 0 | `` |
| `level` | `VARCHAR(12)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 2006)

| id | employee_id | skill_id | level |
|---|---|---|---|
| 1 | 1 | 1 | BEGINNER |
| 2 | 1 | 4 | INTERMEDIATE |
| 3 | 2 | 2 | INTERMEDIATE |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `skill_id` | `skills` | `id` | `NO ACTION` | `NO ACTION` |
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_employee_skills_skill_id` | 0 | c |
| `ix_employee_skills_employee_id` | 0 | c |
| `ix_employee_skills_id` | 0 | c |
| `sqlite_autoindex_employee_skills_1` | 1 | u |

## `employees`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `email` | `VARCHAR(255)` | 1 | 0 | `` |
| `hashed_password` | `VARCHAR(255)` | 1 | 0 | `` |
| `department_id` | `INTEGER` | 0 | 0 | `` |
| `manager_id` | `INTEGER` | 0 | 0 | `` |
| `role` | `VARCHAR(8)` | 1 | 0 | `` |
| `status` | `VARCHAR(8)` | 1 | 0 | `` |
| `joining_date` | `DATE` | 1 | 0 | `` |
| `phone` | `VARCHAR(20)` | 0 | 0 | `` |
| `address` | `VARCHAR(255)` | 0 | 0 | `` |
| `blood_type` | `VARCHAR(8)` | 0 | 0 | `` |
| `occupancy` | `VARCHAR(60)` | 0 | 0 | `` |
| `date_of_birth` | `DATE` | 0 | 0 | `` |
| `profile_photo_path` | `VARCHAR(255)` | 0 | 0 | `` |
| `profile_photo_mime` | `VARCHAR(64)` | 0 | 0 | `` |
| `current_salary_usd` | `NUMERIC(12, 2)` | 0 | 0 | `` |
| `bank_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_account_number` | `VARCHAR(34)` | 0 | 0 | `` |
| `bank_account_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_branch` | `VARCHAR(120)` | 0 | 0 | `` |
| `bank_ifsc` | `VARCHAR(20)` | 0 | 0 | `` |
| `pan_number` | `VARCHAR(20)` | 0 | 0 | `` |
| `pan_name` | `VARCHAR(120)` | 0 | 0 | `` |
| `pan_dob` | `DATE` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 1003)

| id | name | email | hashed_password | department_id | manager_id | role | status | joining_date | phone | address | blood_type | occupancy | date_of_birth | profile_photo_path | profile_photo_mime | current_salary_usd | bank_name | bank_account_number | bank_account_name | bank_branch | bank_ifsc | pan_number | pan_name | pan_dob |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Admin User | admin@mock-hrms.dev | [REDACTED] | 6 |  | ADMIN | ACTIVE | 2022-01-01 | [REDACTED] | [REDACTED] | O+ | Full-Time | [REDACTED] |  |  | 60000 | JPMorgan Chase | [REDACTED] | [REDACTED] | Midtown | [REDACTED] | [REDACTED] | [REDACTED] | [REDACTED] |
| 2 | Manager User | manager@mock-hrms.dev | [REDACTED] | 3 |  | MANAGER | ACTIVE | 2022-01-01 | [REDACTED] | [REDACTED] | O+ | Full-Time | [REDACTED] |  |  | 64500 | Citibank | [REDACTED] | [REDACTED] | Main Branch | [REDACTED] | [REDACTED] | [REDACTED] | [REDACTED] |
| 3 | Employee User | employee@mock-hrms.dev | [REDACTED] | 2 | 2 | EMPLOYEE | ACTIVE | 2022-01-01 | [REDACTED] | [REDACTED] | O+ | Full-Time | [REDACTED] |  |  | 69000 | DBS Bank | [REDACTED] | [REDACTED] | Downtown | [REDACTED] | [REDACTED] | [REDACTED] | [REDACTED] |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `manager_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |
| `department_id` | `departments` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_employees_date_of_birth` | 0 | c |
| `ix_employees_occupancy` | 0 | c |
| `ix_employees_blood_type` | 0 | c |
| `ix_employees_status` | 0 | c |
| `ix_employees_name` | 0 | c |
| `ix_employees_id` | 0 | c |
| `ix_employees_email` | 1 | c |
| `ix_employees_department_id` | 0 | c |

## `holidays`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `date` | `DATE` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 8)

| id | name | date |
|---|---|---|
| 1 | International Women's Day | 2027-03-08 |
| 2 | International Workers' Day | 2027-05-01 |
| 3 | United Nations Day | 2026-10-24 |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_holidays_date` | 0 | c |
| `ix_holidays_name` | 0 | c |
| `ix_holidays_id` | 0 | c |

## `hr_policies`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `title` | `VARCHAR(220)` | 1 | 0 | `` |
| `content` | `TEXT` | 0 | 0 | `` |
| `category` | `VARCHAR(60)` | 1 | 0 | `` |
| `embedding` | `JSON` | 0 | 0 | `` |
| `original_filename` | `VARCHAR(255)` | 0 | 0 | `` |
| `file_path` | `TEXT` | 0 | 0 | `` |
| `mime_type` | `VARCHAR(100)` | 0 | 0 | `` |
| `size_bytes` | `INTEGER` | 0 | 0 | `` |
| `uploaded_by` | `INTEGER` | 0 | 0 | `` |
| `checksum` | `VARCHAR(64)` | 0 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 27)

| id | title | content | category | embedding | original_filename | file_path | mime_type | size_bytes | uploaded_by | checksum | created_at |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Leave Policy |  | LEAVE | null | seed_policy_01.md | \app\storage\hr-policies\seed_policy_01.md | text/markdown | 94 | 1 | 94e7da2e5205a2ea272353937058c79222886b781ef6c9d7f81632b4d9a7a236 | 2026-10-01 14:46:54 |
| 2 | Attendance Policy |  | ATTENDANCE | null | seed_policy_02.md | \app\storage\hr-policies\seed_policy_02.md | text/markdown | 82 | 1 | 1847a5ab310e2f0a2c302e923ac134e8bf3538feb109f7182a56ac78f766d13b | 2026-10-01 14:46:54 |
| 3 | WFH Policy |  | WFH | null | seed_policy_03.md | \app\storage\hr-policies\seed_policy_03.md | text/markdown | 83 | 1 | a4085f25dc54a1247cab74ab204bb496114ba81641ce4a36bcf312cd9af13354 | 2026-10-01 14:46:54 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `uploaded_by` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_hr_policies_checksum` | 0 | c |
| `ix_hr_policies_uploaded_by` | 0 | c |
| `ix_hr_policies_id` | 0 | c |
| `ix_hr_policies_title` | 0 | c |
| `ix_hr_policies_category` | 0 | c |

## `job_history`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `designation` | `VARCHAR(120)` | 1 | 0 | `` |
| `business_unit` | `VARCHAR(120)` | 1 | 0 | `` |
| `department` | `VARCHAR(120)` | 1 | 0 | `` |
| `start_date` | `DATE` | 1 | 0 | `` |
| `end_date` | `DATE` | 0 | 0 | `` |
| `is_current` | `BOOLEAN` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 1005)

| id | employee_id | designation | business_unit | department | start_date | end_date | is_current |
|---|---|---|---|---|---|---|---|
| 1 | 1 | HR Director | Corporate | HR | 2022-01-01 |  | 1 |
| 2 | 2 | Finance Manager | Corporate | Finance | 2022-01-01 |  | 1 |
| 3 | 3 | Software Engineer II | Corporate | Engineering | 2022-01-01 |  | 1 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_job_history_is_current` | 0 | c |
| `ix_job_history_end_date` | 0 | c |
| `ix_job_history_start_date` | 0 | c |
| `ix_job_history_employee_id` | 0 | c |
| `ix_job_history_id` | 0 | c |

## `leave_balances`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `leave_type` | `VARCHAR(6)` | 1 | 0 | `` |
| `total` | `FLOAT` | 1 | 0 | `` |
| `used` | `FLOAT` | 1 | 0 | `` |
| `remaining` | `FLOAT` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 3009)

| id | employee_id | leave_type | total | used | remaining |
|---|---|---|---|---|---|
| 1 | 1 | CASUAL | 12.0 | 5.0 | 7.0 |
| 2 | 1 | SICK | 10.0 | 1.0 | 9.0 |
| 3 | 1 | EARNED | 15.0 | 4.0 | 11.0 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_leave_balances_employee_id` | 0 | c |
| `ix_leave_balances_leave_type` | 0 | c |
| `ix_leave_balances_id` | 0 | c |

## `leave_requests`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `leave_type` | `VARCHAR(6)` | 1 | 0 | `` |
| `start_date` | `DATE` | 1 | 0 | `` |
| `end_date` | `DATE` | 1 | 0 | `` |
| `reason` | `VARCHAR(500)` | 1 | 0 | `` |
| `status` | `VARCHAR(8)` | 1 | 0 | `` |
| `approver_id` | `INTEGER` | 0 | 0 | `` |
| `is_half_day` | `BOOLEAN` | 1 | 0 | `0` |
| `half_day_period` | `VARCHAR(11)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 20)

| id | employee_id | leave_type | start_date | end_date | reason | status | approver_id | is_half_day | half_day_period |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | CASUAL | 2026-10-03 | 2026-10-04 | Family function | REJECTED | 1 | 0 |  |
| 2 | 3 | SICK | 2026-09-21 | 2026-09-22 | Recovery leave | APPROVED | 2 | 0 |  |
| 3 | 3 | CASUAL | 2026-10-12 | 2026-10-12 | Casual leave requested through HR Copilot. | PENDING |  | 0 |  |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `approver_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_leave_requests_status` | 0 | c |
| `ix_leave_requests_start_date` | 0 | c |
| `ix_leave_requests_approver_id` | 0 | c |
| `ix_leave_requests_leave_type` | 0 | c |
| `ix_leave_requests_id` | 0 | c |
| `ix_leave_requests_employee_id` | 0 | c |
| `ix_leave_requests_end_date` | 0 | c |

## `onboarding_tasks`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `ticket_id` | `INTEGER` | 1 | 0 | `` |
| `task_name` | `VARCHAR(200)` | 1 | 0 | `` |
| `is_completed` | `BOOLEAN` | 1 | 0 | `` |
| `due_date` | `DATE` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 2)

| id | ticket_id | task_name | is_completed | due_date |
|---|---|---|---|---|
| 1 | 2 | Issue laptop | 0 |  |
| 2 | 2 | Generate ID card | 0 | 2026-10-03 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `ticket_id` | `tickets` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_onboarding_tasks_due_date` | 0 | c |
| `ix_onboarding_tasks_is_completed` | 0 | c |
| `ix_onboarding_tasks_ticket_id` | 0 | c |
| `ix_onboarding_tasks_id` | 0 | c |

## `payroll_records`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `month` | `DATE` | 1 | 0 | `` |
| `gross` | `FLOAT` | 1 | 0 | `` |
| `deductions` | `JSON` | 1 | 0 | `` |
| `net` | `FLOAT` | 1 | 0 | `` |
| `pan` | `VARCHAR(20)` | 1 | 0 | `` |
| `pf_uan` | `VARCHAR(30)` | 0 | 0 | `` |
| `esi_no` | `VARCHAR(30)` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 5842)

| id | employee_id | month | gross | deductions | net | pan | pf_uan | esi_no |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 2026-10-01 | 60300.0 | {"pf": 2713.5, "esi": 482.4, "tax": 6030.0} | 51074.1 | ADHLP1000T | [REDACTED] | [REDACTED] |
| 2 | 1 | 2026-09-01 | 60600.0 | {"pf": 2727.0, "esi": 484.8, "tax": 6060.0} | 51328.2 | ADHLP1000T | [REDACTED] | [REDACTED] |
| 3 | 1 | 2026-08-01 | 60000.0 | {"pf": 2700.0, "esi": 480.0, "tax": 6000.0} | 50820.0 | ADHLP1000T | [REDACTED] | [REDACTED] |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_payroll_records_pan` | 0 | c |
| `ix_payroll_records_month` | 0 | c |
| `ix_payroll_records_employee_id` | 0 | c |
| `ix_payroll_records_id` | 0 | c |

## `pending_action_confirmations`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `token` | `VARCHAR(36)` | 1 | 0 | `` |
| `user_id` | `INTEGER` | 1 | 0 | `` |
| `action_type` | `VARCHAR(50)` | 1 | 0 | `` |
| `question` | `TEXT` | 1 | 0 | `` |
| `status` | `VARCHAR(20)` | 1 | 0 | `'pending'` |
| `created_at` | `DATETIME` | 1 | 0 | `` |
| `expires_at` | `DATETIME` | 1 | 0 | `` |
| `confirmed_at` | `DATETIME` | 0 | 0 | `` |
| `completed_at` | `DATETIME` | 0 | 0 | `` |
| `error_message` | `TEXT` | 0 | 0 | `` |

### Sample Records (showing up to 3 of 31)

| id | token | user_id | action_type | question | status | created_at | expires_at | confirmed_at | completed_at | error_message |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 737d40e5-7d40-40d7-a1c9-7c4dcb31e710 | 1 | announcement_creation | Create an announcement titled "HITL Test Announcement" with the message "Testing human-in-the-loop confirma... | pending | 2026-10-28 09:42:17.031109 | 2026-10-28 09:52:17.031109 |  |  |  |
| 2 | ec5db60c-d640-49e5-b6f8-6d670b69932e | 1 | announcement_creation | Create an announcement titled "HITL Test Announcement" with the message "Testing human-in-the-loop confirma... | completed | 2026-10-28 09:43:26.529880 | 2026-10-28 09:53:26.529880 | 2026-10-28 09:46:59.636287 | 2026-10-28 09:46:59.686721 |  |
| 3 | 2873e4e9-d513-461b-8942-62bcd4d14350 | 1 | announcement_creation | Create an announcement titled "HITL Frontend Test" with the message "Testing confirmation through the UI." | completed | 2026-10-28 10:02:35.502554 | 2026-10-28 10:12:35.502554 | 2026-10-28 10:02:42.831676 | 2026-10-28 10:02:42.896014 |  |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `user_id` | `employees` | `id` | `NO ACTION` | `CASCADE` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_pending_action_confirmations_expires_at` | 0 | c |
| `ix_pending_action_confirmations_user_status` | 0 | c |
| `ix_pending_action_confirmations_status` | 0 | c |
| `ix_pending_action_confirmations_user_id` | 0 | c |
| `ix_pending_action_confirmations_token` | 1 | c |
| `ix_pending_action_confirmations_id` | 0 | c |

## `poll_responses`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `poll_id` | `INTEGER` | 1 | 0 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `option_index` | `INTEGER` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 2)

| id | poll_id | employee_id | option_index |
|---|---|---|---|
| 1 | 1 | 3 | 0 |
| 2 | 1 | 1 | 1 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `poll_id` | `polls` | `id` | `NO ACTION` | `NO ACTION` |
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_poll_responses_option_index` | 0 | c |
| `ix_poll_responses_employee_id` | 0 | c |
| `ix_poll_responses_poll_id` | 0 | c |
| `ix_poll_responses_id` | 0 | c |
| `sqlite_autoindex_poll_responses_1` | 1 | u |

## `polls`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `question` | `VARCHAR(300)` | 1 | 0 | `` |
| `options` | `JSON` | 1 | 0 | `` |
| `created_by` | `INTEGER` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 1)

| id | question | options | created_by | created_at |
|---|---|---|---|---|
| 1 | Which initiative should be prioritized next quarter? | ["Improve leave workflow", "Automate payroll FAQ", "Manager dashboard revamp"] | 2 | 2026-10-01 14:46:54 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `created_by` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_polls_created_at` | 0 | c |
| `ix_polls_created_by` | 0 | c |
| `ix_polls_id` | 0 | c |

## `projects`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(180)` | 1 | 0 | `` |
| `description` | `TEXT` | 0 | 0 | `` |
| `status` | `VARCHAR(20)` | 1 | 0 | `'ONGOING'` |

### Sample Records (showing up to 3 of 25)

| id | name | description | status |
|---|---|---|---|
| 1 | Talent Intelligence Platform | Internal skills intelligence and capability planning platform. | ONGOING |
| 2 | Engineering Reliability Hub | Service quality, SLO tracking, and incident intelligence workflows. | ONGOING |
| 3 | Data Platform Modernization | Warehouse optimization, ETL reliability, and data contract governance. | ONGOING |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_projects_status` | 0 | c |
| `ix_projects_name` | 0 | c |
| `ix_projects_id` | 0 | c |

## `skills`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `name` | `VARCHAR(120)` | 1 | 0 | `` |
| `normalized_name` | `VARCHAR(120)` | 1 | 0 | `` |

### Sample Records (showing up to 3 of 8)

| id | name | normalized_name |
|---|---|---|
| 1 | Python | python |
| 2 | AI Engineer | ai engineer |
| 3 | FastAPI | fastapi |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_skills_normalized_name` | 0 | c |
| `ix_skills_id` | 0 | c |
| `sqlite_autoindex_skills_2` | 1 | u |
| `sqlite_autoindex_skills_1` | 1 | u |

## `tickets`

### Columns

| name | type | notnull | pk | default |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 1 | 1 | `` |
| `employee_id` | `INTEGER` | 1 | 0 | `` |
| `assignee_id` | `INTEGER` | 0 | 0 | `` |
| `title` | `VARCHAR(180)` | 1 | 0 | `` |
| `description` | `TEXT` | 1 | 0 | `` |
| `category` | `VARCHAR(10)` | 1 | 0 | `` |
| `priority` | `VARCHAR(6)` | 1 | 0 | `` |
| `status` | `VARCHAR(11)` | 1 | 0 | `` |
| `created_at` | `DATETIME` | 1 | 0 | `CURRENT_TIMESTAMP` |

### Sample Records (showing up to 3 of 27)

| id | employee_id | assignee_id | title | description | category | priority | status | created_at |
|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 3 | Laptop VPN access issue | Unable to connect to VPN from home network after update. | IT | HIGH | RESOLVED | 2026-10-01 14:46:50 |
| 2 | 3 | 2 | New joiner onboarding setup | Complete laptop, ID card and workspace setup for onboarding. | ONBOARDING | MEDIUM | RESOLVED | 2026-10-01 14:46:50 |
| 3 | 1 |  | VPN test environment unavailability | Create a high-priority IT ticket about VPN test environment unavailability. | IT | HIGH | IN_PROGRESS | 2026-10-20 19:52:33 |

### Foreign Keys

| column | references | referenced column | on update | on delete |
|---|---|---|---|---|
| `employee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |
| `assignee_id` | `employees` | `id` | `NO ACTION` | `NO ACTION` |

### Indexes

| name | unique | origin |
|---|---:|---|
| `ix_tickets_created_at` | 0 | c |
| `ix_tickets_status` | 0 | c |
| `ix_tickets_priority` | 0 | c |
| `ix_tickets_category` | 0 | c |
| `ix_tickets_assignee_id` | 0 | c |
| `ix_tickets_employee_id` | 0 | c |
| `ix_tickets_id` | 0 | c |
