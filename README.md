# Pretoria Municipality — Water Leak Reporting Portal

A full-stack water leak reporting application for the Pretoria Municipality, built as a
testable target for Selenium + Cucumber test automation. Includes sign-in with two roles
(**admin** and **citizen**) and ownership-based permissions.

## Tech stack

| Layer    | Technology                                      |
|----------|--------------------------------------------------|
| Frontend | HTML, JavaScript (vanilla), Tailwind CSS, custom toast notifications |
| Backend  | Python (Flask REST API), cookie sessions, hashed passwords (Werkzeug) |
| Database | SQLite (`backend/water_leaks.db`, auto-created)  |

## Features

- Sign in, register, and sign out (session cookie based)
- Two roles:
  - **admin** — can view, update the status of, and delete *every* report
  - **citizen** — can submit reports and view all reports, but can only update/delete
    reports they created (other reports are read-only in the UI and blocked by the API)
- Submit a water leak report (name, email, phone, address, Pretoria area, severity, description)
- Server-side validation with per-field inline error messages
- Toast notifications for success/error/info/warning actions
- View, filter (status/area), search, update status of, and delete reports
- Dashboard with totals, status/area breakdowns and recent reports
- 3 sample reports + 3 users seeded on first run for demo/testing data

## Demo accounts (seeded on first run)

| Username | Password      | Role    | Owns          |
|----------|---------------|---------|---------------|
| `admin`  | `admin123`    | admin   | — (can manage all) |
| `thabo`  | `password123` | citizen | report #1     |
| `lerato` | `password123` | citizen | report #2     |

Report #3 has no owner, so only an admin can modify it. Change these accounts before any
real use; passwords are stored as Werkzeug hashes.

> Session secret: set the `SECRET_KEY` environment variable in production. A development
> fallback is used otherwise.

## Project structure

```
water-leak-report/
├── backend/
│   ├── app.py              # Flask app: auth, REST API + static file serving
│   ├── requirements.txt
│   └── water_leaks.db      # SQLite database (created automatically)
├── frontend/
│   ├── signin.html         # Sign-in page
│   ├── register.html       # Create-account page
│   ├── index.html          # Report submission form
│   ├── reports.html        # Reports list, filters, status update, delete
│   ├── dashboard.html      # Statistics dashboard
│   └── js/
│       ├── shared.js       # Toast system + API client + auth helpers
│       ├── signin.js       # Sign-in logic
│       ├── register.js     # Registration logic
│       ├── index.js        # Form logic
│       ├── reports.js      # Table/filter/status/delete logic
│       └── dashboard.js    # Dashboard logic
└── README.md
```

## Getting started

Requirements: Python 3.10+

```bash
cd water-leak-report
pip install -r backend/requirements.txt
python backend/app.py
```

Then open http://127.0.0.1:5000 — you will be sent to the sign-in page.

- To reset the database (restores the seeded users and reports), stop the app and delete
  `backend/water_leaks.db`.
- Tailwind CSS is loaded from the CDN, so the browser needs internet access.

## API reference

All `/api/reports` and `/api/stats` endpoints require a signed-in session; otherwise they
return `401`. `/api/health` and `/api/areas` are public.

### Authentication

| Method | Endpoint             | Description                                              |
|--------|----------------------|----------------------------------------------------------|
| POST   | `/api/auth/register` | Create a citizen account and sign in (422/409 on error) |
| POST   | `/api/auth/login`    | Sign in (`{"username","password"}`; 401 if wrong)        |
| POST   | `/api/auth/logout`   | Sign out                                                 |
| GET    | `/api/auth/me`       | Current user, or 401 when signed out                     |

### Reports

| Method | Endpoint                | Description |
|--------|-------------------------|-------------|
| GET    | `/api/reports`          | List reports. Query params: `status`, `area`, `q`. Each report includes `user_id`, `reporter_username` and `can_edit`. |
| POST   | `/api/reports`          | Create a report owned by the signed-in user (422 + `errors` map on invalid) |
| GET    | `/api/reports/<id>`     | Get one report (404 if missing) |
| PUT    | `/api/reports/<id>`     | Update status. Admin, or the owner only (403 otherwise) |
| DELETE | `/api/reports/<id>`     | Delete. Admin, or the owner only (403 otherwise) |
| GET    | `/api/stats`            | Dashboard statistics |

Status values: `submitted`, `in_progress`, `resolved`, `on_hold`, `rejected`
Severity values: `low`, `medium`, `high`, `critical`
Roles: `citizen`, `admin`

Example (sign in first so the session cookie is kept):

```bash
curl -c cookies.txt -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"thabo","password":"password123"}'

curl -b cookies.txt -X POST http://127.0.0.1:5000/api/reports \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@example.com","phone":"0821234567","address":"12 Stanza Bopape Street","area":"Hatfield","severity":"high","description":"Large leak on the pavement outside my gate"}'
```

## Selenium / Cucumber testing notes

The UI was built with stable, predictable locators in mind.

### Pages

| Page          | URL                                     |
|---------------|-----------------------------------------|
| Sign in       | `http://127.0.0.1:5000/signin.html`     |
| Register      | `http://127.0.0.1:5000/register.html`   |
| Report form   | `http://127.0.0.1:5000/`                |
| Reports list  | `http://127.0.0.1:5000/reports.html`    |
| Dashboard     | `http://127.0.0.1:5000/dashboard.html`  |

### Sign-in / auth locators

| Element | Locator |
|---------|---------|
| Sign-in form | `#signin-form` / `data-testid="signin-form"` |
| Username / password | `#signin-username`, `#signin-password` |
| Sign-in button | `#signin-button` / `data-testid="signin-button"` |
| Sign-in error box | `#signin-error` / `data-testid="signin-error"` |
| Link to register | `#goto-register` |
| Register form | `#register-form` / `data-testid="register-form"` |
| Register inputs | `#register-username`, `#register-email`, `#register-password`, `#register-confirm` |
| Register field errors | `#register-<field>-error` (e.g. `#register-email-error`) |
| Register button | `#register-button` / `data-testid="register-button"` |
| Link to sign in | `#goto-signin` |
| Signed-in user (header) | `#current-user` / `data-testid="current-user"` (text `username (role)`) |
| Sign out | `#signout-button` / `data-testid="signout-button"` |

### Report / dashboard locators

| Element | Locator |
|---------|---------|
| Form | `#report-form` / `data-testid="report-form"` |
| Inputs | `#full-name`, `#email`, `#phone`, `#address`, `#area`, `#severity`, `#description` |
| Field errors | `#<field>-error` (e.g. `#email-error`), `data-testid="error-email"` |
| Error summary | `#form-error-summary` |
| Success panel | `#success-panel` |
| Submit button | `#submit-report` / `data-testid="submit-report"` |
| Toast container | `#toast-container`; each toast has `data-testid="toast"` with `data-type="success"\|"error"\|"info"\|"warning"` |
| Toast message | `data-testid="toast-message"` |
| Reports table | `#reports-table`, rows: `data-testid="report-row"` (`data-id` = report id, `data-can-edit="true"\|"false"`) |
| Row ID cell | `data-testid="report-id"` (text like `#4`) |
| Owner username | `data-testid="owner-username"` (text `@thabo` or `(unassigned)`) |
| Status badge / select | `data-testid="status-badge"`, `data-testid="status-select"` |
| Read-only marker | `data-testid="readonly-lock"` (shown instead of the select when not editable) |
| Delete button | `data-testid="delete-report"` (only rendered for editable rows) |
| Filters | `#filter-status`, `#filter-area`, `#search-reports`, `#search-button`, `#refresh-reports` |
| Role notice | `#role-notice` / `data-testid="role-notice"` |
| Count / empty state | `#reports-count`, `data-testid="empty-state"` |
| Dashboard stats | `#stat-total`, `#stat-submitted`, `#stat-in-progress`, `#stat-resolved`, `#stat-critical-open` |
| Dashboard panels | `data-testid="status-breakdown"`, `data-testid="area-breakdown"`, `data-testid="recent-reports"` |
| Refresh | `data-testid="refresh-dashboard"` |

### Behaviour designed for testing

- **Authentication is required to view any app page.** Visiting `index.html`, `reports.html`
  or `dashboard.html` while signed out redirects the browser to `signin.html`. Log in first
  in your step definitions.
- **The sign-in form uses `novalidate`** and relies on the API, so wrong credentials always
  produce a real `401` shown in `#signin-error` plus an error toast — no client-side blocks.
- **Permissions are enforced server-side** (not just hidden in the UI): a citizen editing or
  deleting someone else's report gets `403` and the select reverts to its previous value.
- **Read-only rows**: for reports you cannot edit, the row has `data-can-edit="false"`, shows
  `data-testid="readonly-lock"` in place of the status select, and renders no delete button.
  Editable rows have `data-can-edit="true"`.
- **Validation is server-side only.** The report form uses `novalidate` and inputs have no
  `required` attributes, so submitting an invalid form always triggers a real API call (422)
  and renders inline errors.
- **Delete asks for confirmation** via a native `window.confirm()` dialog — accept it with
  `driver.switch_to.alert.accept()`.
- **Toasts** auto-dismiss after ~4.5s but can also be closed with the button carrying
  `data-testid="toast-close"`.
- **Deterministic data**: the DB is seeded with 3 users and 3 reports on first creation only.
  For a clean slate, delete `backend/water_leaks.db` before starting the server. New report
  IDs are sequential from 1 after a DB reset.

### Example Gherkin scenarios to get you started

```gherkin
Feature: Authentication

  Scenario: Sign in as an administrator
    Given I am on the sign in page
    When I sign in as "admin" with password "admin123"
    Then the header should show "admin (admin)"
    And I should see the report form page

  Scenario: Sign in with invalid credentials
    Given I am on the sign in page
    When I sign in as "thabo" with password "wrong-password"
    Then the sign-in error should read "Invalid username or password"

  Scenario: Register a new account
    Given I am on the register page
    When I register with username "new_user", email "new@example.com" and password "secret123"
    Then the header should show "new_user (citizen)"

  Scenario: Signed-out users are redirected to sign in
    Given I am not signed in
    When I open the dashboard page
    Then I should land on the sign in page

Feature: Role-based access to reports

  Background:
    Given the database has been reset

  Scenario: Citizen sees other reports as read-only
    Given I am signed in as "thabo" with password "password123"
    When I open the reports page
    Then report #1 should have data-can-edit "true"
    And report #2 should have data-can-edit "false"
    And report #2 should show the read-only marker

  Scenario: Citizen cannot change someone else's report
    Given I am signed in as "thabo" with password "password123"
    When I open the reports page
    Then report #2 should have no status select and no delete button

  Scenario: Admin can manage every report
    Given I am signed in as "admin" with password "admin123"
    When I open the reports page
    Then every report should have data-can-edit "true"
    And I can change report #2 status to "on_hold"
    And I should see a success toast

Feature: Submit a water leak report

  Scenario: Successful submission shows a success panel and toast
    Given I am signed in as "thabo" with password "password123"
    And I am on the report page
    When I fill in "full-name" with "Sipho Dlamini"
    And I fill in "email" with "sipho@example.com"
    And I fill in "phone" with "0821234567"
    And I fill in "address" with "251 Stanza Bopape Street"
    And I select "Hatfield" from "area"
    And I select "high" from "severity"
    And I fill in "description" with "Water pooling on the sidewalk outside the clinic"
    And I click the "submit-report" button
    Then I should see a success panel containing "was submitted"
    And I should see a success toast

  Scenario: Invalid email shows an inline error
    Given I am signed in as "thabo" with password "password123"
    And I am on the report page
    When I fill in "email" with "not-an-email"
    And I submit the form with otherwise valid data
    Then the "email-error" element should be visible with text "Enter a valid email address"

Feature: Delete a report

  Scenario: Citizen deletes their own report
    Given I am signed in as "thabo" with password "password123"
    And I am on the reports page
    When I click delete on report #1 and accept the confirmation
    Then report #1 should be removed and a success toast should appear
```
