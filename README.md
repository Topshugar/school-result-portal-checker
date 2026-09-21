# ResultPro — School Result Checker Portal

A lightweight ResultPro prototype for private schools: admins can manage students, import scores from CSV/Excel, generate ₦500 result PINs, and parents can validate a registration number + PIN and print/download the result as PDF.

## Run

Open `index.html` in a browser or serve it with any static web server. Data is stored in browser `localStorage` for this prototype.

**Demo admin login**

- Email: `admin@resultpro.ng`
- Password: `password123`

**Demo parent lookup**

- Registration number: `RP/2025/001`
- PIN: `RP-AB12-CD34`

## Import format

CSV and Excel files should include these columns:

```text
Registration Number,Subject,CA1,CA2,Exam
RP/2025/001,Mathematics,18,17,55
```

## Production hardening

This frontend prototype intentionally uses local storage and a demo login. Before charging schools or parents, add a server-side API and database, hashed admin passwords, role-based access, one-time PIN transactions, Paystack server-side webhook verification, rate limiting, audit logs, and server-generated PDFs. Set a real Paystack public key and never expose secret keys in browser code.
