# Halleluyah Optical Laboratory POS - Upgraded Render Version

A GitHub + Render ready Flask POS/inventory application for Halleluyah Optical Laboratory.

## Included features
- Online POS for multiple branches
- Manager/staff login system
- Manager-only stock creation and stock adjustment
- Lens stock by power range and quantity
- Bulk lens power upload for many powers at once
- Products for frames, cases, cleaners, cloth, accessories, and more
- Wholesale and retail pricing in naira
- End-user and wholesaler sales mode
- Discount, amount paid, balance, and debtor tracking
- Debtor payment update page
- Sales history and sale detail page
- Staff management by manager
- Branch management for multi-branch setup
- CSV export for manager backup/data safety

## Default login
- Username: `manager`
- Password: `admin1234`

Change it immediately after first login.

## Run locally
```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Deploy on Render
1. Create a new GitHub repository.
2. Upload all files in this project.
3. On Render, click **New +** -> **Blueprint**.
4. Connect your GitHub repo.
5. Render will read `render.yaml`, create the web service and PostgreSQL database, and deploy automatically.

## Notes
- The app uses PostgreSQL on Render through `DATABASE_URL`.
- For local testing, it falls back to SQLite.
- Manager can export sales data as CSV from the navbar.
- Sales page supports unlimited rows with dynamic item addition in the browser.


## Render Python version
This project pins Render to Python 3.11.11 using both `.python-version` and the `PYTHON_VERSION` environment variable in `render.yaml`. If Render cached an older build, use **Manual Deploy -> Clear build cache & deploy**.
