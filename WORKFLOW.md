# Electricity Billing System - Workflow Documentation

## Overview
This system manages electricity billing with complete workflow: Customer → Contract → Meter → Reading → Invoice → Payment

## Data Models

### 1. Customer (الزبون)
- Basic customer information
- Account balance tracking
- Multiple contracts allowed

### 2. Contract (العقد)
- Links customer to subscription type
- Has multiple meters
- Status: active, suspended, terminated, expired

### 3. Meter (العداد)
- Belongs to one contract
- Tracks last approved reading
- Status: active, defective, replaced, removed

### 4. Billing Period (الفترة)
- Monthly/bi-monthly/quarterly cycles
- Status flow: Draft → Reading Open → Reading Closed → Billing In Progress → Billing Completed → Closed

### 5. Meter Reading Submission (قراءة العداد)
- Links to: meter, contract, customer, period
- Tracks: previous_reading, submitted_reading, approved_reading
- Status: pending, approved, rejected, flagged_review
- Auto-links to active billing period

### 6. Invoice (الفاتورة)
- Generated from approved readings
- Uses InvoiceLineTemplate for calculation
- Status: draft, issued, paid, partially_paid, overdue, cancelled

### 7. Invoice Line (بند الفاتورة)
- Calculated from template formula
- Types: fixed, percentage, tiered_kwh, single_rate_kwh

### 8. Payment (الدفعة)
- Can be linked to: invoice, contract, or customer
- Auto-links customer/invoice from contract
- Methods: cash, bank_transfer, card, online, cheque

---

## Complete Workflow

### Step 1: Create Customer
```
POST /billing/customers/create/
```
Fields: name_ar, id_number, phone, area, etc.

### Step 2: Create Contract
```
POST /billing/contracts/create/
```
Links customer to subscription type (residential, commercial, etc.)

### Step 3: Create Meter
```
POST /billing/meters/create/
```
Each contract can have multiple meters

### Step 4: Create Billing Period
```
POST /billing/periods/create/
```
Set status to "reading_open" when ready for readings

### Step 5: Submit Reading
```
POST /billing/readings/create/
```
- Select contract (meter auto-selected)
- Shows previous reading from meter
- Auto-links to active billing period

### Step 6: Approve Reading
```
POST /billing/readings/{id}/approve/
```
- Admin reviews and approves
- Sets final_consumption
- Updates meter.last_approved_reading

### Step 7: Generate Invoice
```
POST /billing/periods/{id}/close/
```
- Generates invoices for all approved readings
- Uses InvoiceLineTemplate formulas:
  - Fixed: flat fee
  - Percentage: % of subtotal
  - Tiered kWh: graduated rates
  - Single rate: flat rate per kWh

### Step 8: Record Payment
```
POST /billing/payments/create/
```
Three modes:
- By Invoice: link to specific invoice
- By Contract: auto-link open invoice
- By Customer: direct to customer account

---

## URL Routes

| Route | Description |
|-------|------------|
| `/billing/` | Dashboard |
| `/billing/customers/` | Customer list |
| `/billing/customers/create/` | Add customer |
| `/billing/contracts/` | Contract list |
| `/billing/contracts/create/` | Add contract |
| `/billing/meters/` | Meter list |
| `/billing/meters/create/` | Add meter |
| `/billing/periods/` | Billing periods |
| `/billing/periods/create/` | Create period |
| `/billing/periods/{id}/edit/` | Edit period |
| `/billing/periods/{id}/close/` | Generate invoices |
| `/billing/readings/` | Reading list |
| `/billing/readings/create/` | Submit reading |
| `/billing/readings/{id}/approve/` | Approve reading |
| `/billing/invoices/` | Invoice list |
| `/billing/invoices/{id}/` | Invoice detail |
| `/billing/payments/` | Payment list |
| `/billing/payments/create/` | Record payment |
| `/billing/payments/{id}/` | Payment detail |
| `/billing/collectors/` | Collector list |
| `/billing/collectors/create/` | Add collector |
| `/billing/settings/` | System settings |
| `/billing/settings/templates/` | Invoice templates |

---

## Invoice Calculation

### Tiered kWh Example (استهلاك كهرباء)
```
First 100 kWh:    0.08 per kWh
101-300 kWh:    0.12 per kWh
301-600 kWh:    0.18 per kWh
601+ kWh:       0.25 per kWh
```

For 500 kWh consumption:
- 100 × 0.08 = 8.00
- 200 × 0.12 = 24.00
- 200 × 0.18 = 36.00
- **Subtotal: 68.00**

### Additional Lines
1. **Fixed Service Fee (رسم خدمة ثابت)**: 5.00
2. **Municipality Fee (رسم بلدي)**: 5% of subtotal
3. **VAT (ضريبة القيمة المضافة)**: 16% of (subtotal + municipality)

---

## System Settings

Access: `/billing/settings/`

- Company information
- Subscription types management
- Invoice line templates with formula details
- Template detail: `/billing/settings/templates/{id}/`

---

## Key Features

1. **Auto-generated Numbers**: Customer, Contract, Meter, Payment all auto-number
2. **Period Auto-linking**: Readings auto-link to open billing period
3. **Flexible Payments**: Pay by invoice, contract, or customer
4. **Payment Auto-linking**: Payment via contract auto-links customer & invoice
5. **Approval Workflow**: Readings require approval before invoicing
6. **Tiered Pricing**: Multiple rate tiers for consumption

---

## Database Schema Key Fields

### Customer
- customer_number (auto-generated)
- full_name_ar
- mobile_phone
- current_balance
- credit_limit

### Contract
- contract_number (auto-generated)
- customer (FK)
- type (subscription_type FK)
- contract_status
- connection_load

### Meter
- meter_number (auto-generated)
- contract (FK)
- last_approved_reading
- meter_status

### MeterReadingSubmission
- meter (FK)
- contract (FK)
- customer (FK)
- period (FK, auto-linked)
- previous_reading
- submitted_reading
- approved_reading
- approval_status

### Invoice
- invoice_number
- contract (FK)
- total_amount
- paid_amount
- invoice_status

### Payment
- payment_number (auto-generated)
- contract (FK, optional)
- invoice (FK, optional)
- customer (FK)
- amount
- payment_method