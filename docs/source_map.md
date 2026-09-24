# Source Map: Olist Brazilian E-Commerce Dataset

## Overview

This document catalogs all data sources used in the Olist Delivery Reliability Pipeline, documenting their business purpose, owning system, grain, key fields, and known gaps.

---

## Primary Sources: Olist Dataset (Kaggle)

### 1. `orders` — Core Order Lifecycle

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Master record of every order placed through the Olist platform |
| **Owning System** | Order Management System |
| **Grain** | One row = one unique order (`order_id`) |
| **Key Fields** | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date` |
| **Known Gaps** | No carrier tracking information; no live GPS; no carrier SLA data; delivery timestamps are batch-updated rather than real-time |
| **Used For** | Core event reconstruction (placed → approved → shipped → delivered), on-time delivery calculation |

---

### 2. `order_items` — Line Items Per Order

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Individual items within each order, linking orders to products and sellers |
| **Owning System** | Order Management System |
| **Grain** | One row = one line item (one product in one order) |
| **Key Fields** | `order_id`, `product_id`, `seller_id`, `price`, `freight_value`, `order_item_id` |
| **Known Gaps** | No per-item delivery tracking; freight is order-level, not item-level; no carrier assignment per item |
| **Used For** | Order-to-seller joins, total order value calculation, price validation against payments |

---

### 3. `order_payments` — Payment Details

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Record of payments received, including installment details |
| **Owning System** | Billing/Payments System |
| **Grain** | One row = one payment installment (an order may have multiple rows) |
| **Key Fields** | `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value` |
| **Known Gaps** | Payment timestamps not tracked (only order timestamps); approval timestamp is in `orders` table; installment data may not align perfectly with order value due to rounding |
| **Used For** | Payment validation (total per order vs. item totals); payment type analysis |

---

### 4. `order_reviews` — Customer Feedback

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Customer-submitted reviews and satisfaction scores |
| **Owning System** | Customer Feedback System |
| **Grain** | One row = one review (some orders have no review, some may have multiple) |
| **Key Fields** | `review_id`, `order_id`, `review_score` (1-5), `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp` |
| **Known Gaps** | Reviews are optional — not every order has one; review submission timing is independent of delivery (customers may review before receiving); no verification that reviewer actually received the order |
| **Used For** | Review score correlation with delivery performance; customer satisfaction metrics |

---

### 5. `products` — Product Catalog

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Master product catalog with attributes |
| **Owning System** | Catalog System |
| **Grain** | One row = one unique product (`product_id`) |
| **Key Fields** | `product_id`, `product_category_name`, `product_name_length`, `product_description_length`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm` |
| **Known Gaps** | Some product attributes are sparse (e.g., many NULLs in description length); product photos not available; no inventory levels |
| **Used For** | Product category analysis; freight/weight correlation with delivery time |

---

### 6. `product_category_name_translation` — Category Names

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Portuguese-to-English translation for product categories |
| **Owning System** | Catalog System |
| **Grain** | One row = one category name |
| **Key Fields** | `product_category_name`, `product_category_name_english` |
| **Known Gaps** | Only English translation; no other languages; categories are high-level (e.g., "perfumaria" = beauty) |
| **Used For** | Human-readable category names in reports |

---

### 7. `sellers` — Seller Registry

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Registry of all sellers on the Olist marketplace |
| **Owning System** | Marketplace/Seller System |
| **Grain** | One row = one unique seller (`seller_id`) |
| **Key Fields** | `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state` |
| **Known Gaps** | No seller performance metrics (e.g., on-time shipping rate, avg rating); only location data; seller ID in `order_items` but no activity history |
| **Used For** | Seller location analysis; geographic distribution of fulfillment |

---

### 8. `customers` — Customer Registry

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Registry of customers with anonymized PII |
| **Owning System** | CRM/Logistics |
| **Grain** | One row = one unique customer (`customer_id`) |
| **Key Fields** | `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| **Known Gaps** | No personal identifiers (name, email, address); customer_unique_id allows tracking repeat purchases but actual PII is removed; ZIP prefixes are coarse (cover multiple addresses) |
| **Used For** | Customer location analysis; repeat customer identification; delivery geography |

---

### 9. `geolocation` — ZIP Prefix Geography

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Reference table mapping ZIP code prefixes to geographic coordinates |
| **Owning System** | Logistics/Geography Reference |
| **Grain** | One row = one ZIP prefix + city/state combination (multiple rows per prefix due to spelling variations) |
| **Key Fields** | `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state` |
| **Known Gains** | Provides lat/lng for distance calculations; city/spelling normalization helps with data quality |
| **Known Gaps** | Coarse geography (ZIP prefix covers ~10,000+ addresses); some valid ZIP prefixes in customer/seller data may not exist in this table; no street-level accuracy |
| **Used For** | Customer-seller distance estimation; state-level aggregations |

---

## Secondary Source: Brazilian Holidays API

### 10. `brasil_holidays_{year}.json` — National Holidays

| Attribute | Value |
|-----------|-------|
| **Business Purpose** | Brazilian national holidays for delivery expectation context |
| **Owning System** | External API (Brasil API) |
| **Source URL** | `https://brasilapi.com.br/api/feriados/v1/{year}` |
| **Grain** | One row = one holiday date + name |
| **Key Fields** | `date` (YYYY-MM-DD), `name`, `type` (national, state, municipal) |
| **Known Gaps** | Only national holidays included (no state/municipal); no observed-date logic (if holiday falls Sunday, Monday may not be a day off); no carrier-specific close days |
| **Used For** | Context column in delivery analysis (holiday proximity flag); NOT used to reclassify on-time status |

---

## Business Question → Source Mapping

| Business Question | Primary Source(s) | Why |
|-------------------|-------------------|-----|
| **What % of orders were delivered on time?** | `orders` | `order_delivered_customer_date` vs `order_estimated_delivery_date` |
| **How long does shipping take on average by state?** | `orders`, `customers`, `geolocation` | Join delivery timestamps to customer state via `customer_id` |
| **Does late delivery correlate with bad reviews?** | `orders`, `order_reviews` | Compare `on_time` flag to `review_score` |
| **What portion of delay is pre-ship vs. in-transit?** | `orders` | `order_delivered_carrier_date - order_approved_at` (pre-ship) vs `order_delivered_customer_date - order_delivered_carrier_date` (in-transit) |
| **Which sellers have the longest order-to-ship times?** | `orders`, `order_items`, `sellers` | Calculate `shipped - approved` by `seller_id` |
| **Do holidays affect delivery performance?** | `orders`, `brasil_holidays` | Flag orders with `holiday_within_3_days` and compare delivery rates |
| **What is the average order value?** | `order_payments`, `order_items` | Sum `payment_value` per order; validate against sum of `price` + `freight` |
| **Which product categories have the worst delivery times?** | `orders`, `order_items`, `products` | Join delivery times to `product_category_name` |

---

## Data Quality Notes

### Referential Integrity Issues (Expected)
- Some `order_id`s in `order_items` may not exist in `orders` (data entry issues)
- Some `order_id`s in `order_reviews` may not exist in `orders` (orphaned reviews)
- Some `order_id`s in `order_payments` may not exist in `orders` (orphaned payments)

### Timestamp Anomalies (Expected)
- `delivered_customer_date` may be earlier than `delivered_carrier_date` (impossible timeline)
- `delivered_customer_date` may be earlier than `order_purchase_timestamp` (impossible)
- `order_approved_at` may be earlier than `order_purchase_timestamp` (impossible)

### Nulls (Expected)
- `order_delivered_customer_date` may be NULL for orders not yet delivered
- `order_delivered_carrier_date` may be NULL for orders not yet shipped
- `order_approved_at` may be NULL for orders pending payment approval
- `review_comment_message` may be NULL for reviews with only a score

### Geographic Incompleteness
- Not all `customer_zip_code_prefix` values may have entries in `geolocation`
- Some `geolocation` entries may have NULL lat/lng values