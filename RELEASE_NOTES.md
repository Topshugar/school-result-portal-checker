# v1.0.0 — Initial Multi-Tenant SaaS Release

## Overview

This release converts the ResultPro prototype into a multi-tenant Flask SaaS platform for schools.

## Added

- Multi-school tenant architecture with school-specific data isolation.
- School registration with automatic slug generation.
- School login with hashed passwords.
- Superadmin login using environment-configured credentials.
- Superadmin dashboard for approving schools and settling school balances.
- School dashboard for managing students and viewing results.
- Manual student creation.
- Excel result uploads using the required columns:
  - `reg_number`
  - `full_name`
  - `class_name`
  - `subject`
  - `ca1`
  - `ca2`
  - `exam`
- Automatic result total calculation.
- Public approved-school directory with search.
- School-specific public result pages.
- Paystack inline payment flow for ₦500 result PINs.
- Payment verification through the Paystack API.
- Unique paid PIN generation and one-time PIN usage.
- School-specific PIN validation to prevent cross-school access.
- School balance tracking at ₦200 per paid PIN.
- Paid PIN sales count for each school.
- PostgreSQL and Render deployment configuration support.
- Proprietary permission-based license.

## Configuration

Set these environment variables before deployment:

```env
SECRET_KEY=your-secure-secret
DATABASE_URL=your-postgresql-database-url
PAYSTACK_SECRET_KEY=sk_live_xxx
PAYSTACK_PUBLIC_KEY=pk_live_xxx
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-admin-password
RENDER=true
```

## Deployment Notes

Install dependencies with:

```bash
pip install -r requirements.txt
```

Start the application with:

```bash
python app.py
```

For production, use a WSGI server such as Gunicorn and configure the Render start command accordingly.

## Security Notice

This software is proprietary. Use, deployment, modification, distribution, hosting, or commercial exploitation requires prior written permission or a valid paid license agreement from Topshugar. See `LICENSE` for the full terms.
