# Pretoria Municipality — Water Leak Reporting Portal

A full-stack water leak reporting application for the Pretoria Municipality, built as a
testable target for Selenium + Cucumber test automation.

## Tech stack

| Layer    | Technology                                      |
|----------|--------------------------------------------------|
| Frontend | HTML, JavaScript (vanilla), Tailwind CSS, custom toast notifications |
| Backend  | Python (Flask REST API)                          |
| Database | SQLite (`backend/water_leaks.db`, auto-created)  |

## Features

- Submit a water leak report (name, email, phone, address, Pretoria area, severity, description)
- Server-side validation with per-field inline error messages
- Toast notifications for success/error/info/warning actions
- View, filter (status/area), search, update status of, and delete reports
- Dashboard with totals, status/area breakdowns and recent reports
- 3 sample reports seeded on first run for demo/testing data

## Project structure

```
water-leak-report/
├── backend/
│   ├── app.py              # Flask app: REST API + static file serving
│   ├── requirements.txt
│   └── water_leaks.db      # SQLite database (created automatically)
├── frontend/
│   ├── index.html          # Report submission form
│   ├── reports.html        # Reports list, filters, status update, delete
│   ├── dashboard.html      # Statistics dashboard
│   └── js/
│       ├── shared.js       # Toast system + API client + shared helpers
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

Then open http://127.0.0.1:5000

- To reset the database, stop the app and delete `backend/water_leaks.db`.
- Tailwind CSS is loaded from the CDN, so the browser needs internet access.

## API reference

| Method | Endpoint                | Description                                      |
|--------|-------------------------|--------------------------------------------------|
| GET    | `/api/health`           | Health check                                     |
| GET    | `/api/areas`            | List of Pretoria areas                           |
| GET    | `/api/reports`          | List reports. Query params: `status`, `area`, `q` |
| POST   | `/api/reports`          | Create a report (422 + `errors` map on invalid)  |
| GET    | `/api/reports/<id>`     | Get one report (404 if missing)                  |
| PUT    | `/api/reports/<id>`     | Update status (`{"status": "in_progress"}`)      |
| DELETE | `/api/reports/<id>`     | Delete a report                                  |
| GET    | `/api/stats`            | Dashboard statistics                             |

Status values: `submitted`, `in_progress`, `resolved`, `rejected`
Severity values: `low`, `medium`, `high`, `critical`

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/reports \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@example.com","phone":"0821234567","address":"12 Stanza Bopape Street","area":"Hatfield","severity":"high","description":"Large leak on the pavement outside my gate"}'
```

## Selenium / Cucumber testing notes

The UI was built with stable, predictable locators in mind.

### Pages

| Page          | URL                             |
|---------------|---------------------------------|
| Report form   | `http://127.0.0.1:5000/`        |
| Reports list  | `http://127.0.0.1:5000/reports.html` |
| Dashboard     | `http://127.0.0.1:5000/dashboard.html` |

### Key locators (`data-testid` and `id`)

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
| Reports table | `#reports-table`, rows: `data-testid="report-row"` (`data-id` = report id) |
| Row ID cell | `data-testid="report-id"` (text like `#4`) |
| Status badge / select | `data-testid="status-badge"`, `data-testid="status-select"` |
| Delete button | `data-testid="delete-report"` |
| Filters | `#filter-status`, `#filter-area`, `#search-reports`, `#search-button`, `#refresh-reports` |
| Count / empty state | `#reports-count`, `data-testid="empty-state"` |
| Dashboard stats | `#stat-total`, `#stat-submitted`, `#stat-in-progress`, `#stat-resolved`, `#stat-critical-open` |
| Dashboard panels | `data-testid="status-breakdown"`, `data-testid="area-breakdown"`, `data-testid="recent-reports"` |
| Refresh | `data-testid="refresh-dashboard"` |

### Behaviour designed for testing

- **Validation is server-side only.** The form uses `novalidate` and inputs have no
  `required` attributes, so submitting an invalid form always triggers a real API call
  (422) and renders inline errors — no native browser validation bubbles to deal with.
- **Error messages** are rendered per field under `#<field>-error` and summarised in
  `#form-error-summary`.
- **Toasts** auto-dismiss after ~4.5s but can also be closed with the button carrying
  `data-testid="toast-close"`; assert quickly or look for the toast container.
- **Delete asks for confirmation** via a native `window.confirm()` dialog — accept it
  with `driver.switch_to.alert.accept()`.
- **Status updates are optimistic-free**: the badge only changes after the API confirms,
  and on failure the select reverts to its previous value.
- **Deterministic data**: the DB is seeded with 3 sample reports on first creation only.
  For a clean slate, delete `backend/water_leaks.db` before starting the server.
- New report IDs are sequential from 1 after a DB reset, so assertions on `#1` style
  references are stable when you reset the DB in your test suite setup.

### Example Gherkin scenarios to get you started

```gherkin
Feature: Submit a water leak report
  Scenario: Successful submission shows a success panel and toast
    Given I am on the report page
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
    Given I am on the report page
    When I fill in "email" with "not-an-email"
    And I submit the form with otherwise valid data
    Then the "email-error" element should be visible with text "Enter a valid email address"

Feature: Manage reported leaks
  Scenario: Filter reports by status
    Given I am on the reports page
    When I select "resolved" from "filter-status"
    Then all visible rows should show the status badge "Resolved"

  Scenario: Update a report status
    Given I am on the reports page
    When I change the status select of the first row to "in_progress"
    Then I should see a success toast
    And the first row status badge should show "In Progress"

  Scenario: Delete a report
    Given I am on the reports page
    When I click delete on a report and accept the confirmation
    Then the row should be removed and a success toast should appear
```
