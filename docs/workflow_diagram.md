# Workflow Diagram: Olist Delivery Reliability Pipeline

## Entity-Relationship Diagram

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER_ITEM }o--|| SELLER : sold_by
    ORDER_ITEM }o--|| PRODUCT : includes
    ORDER ||--o{ ORDER_PAYMENT : paid_by
    ORDER ||--o{ ORDER_REVIEW : receives
    CUSTOMER }o--|| GEOLOCATION : located_in
    SELLER }o--|| GEOLOCATION : located_in
    PRODUCT ||--o{ CATEGORY_TRANSLATION : has_translation

    CUSTOMER {
        string customer_id PK
        string customer_unique_id
        string customer_zip_code_prefix FK
        string customer_city
        string customer_state
    }

    ORDER {
        string order_id PK
        string customer_id FK
        string order_status
        timestamp order_purchase_timestamp
        timestamp order_approved_at
        timestamp order_delivered_carrier_date
        timestamp order_delivered_customer_date
        timestamp order_estimated_delivery_date
    }

    ORDER_ITEM {
        string order_item_id PK
        string order_id FK
        string product_id FK
        string seller_id FK
        float price
        float freight_value
    }

    SELLER {
        string seller_id PK
        string seller_zip_code_prefix FK
        string seller_city
        string seller_state
    }

    PRODUCT {
        string product_id PK
        string product_category_name FK
        float product_weight_g
        float product_length_cm
        float product_height_cm
        float product_width_cm
    }

    ORDER_PAYMENT {
        int payment_sequential PK
        string order_id FK
        string payment_type
        int payment_installments
        float payment_value
    }

    ORDER_REVIEW {
        string review_id PK
        string order_id FK
        int review_score
        timestamp review_creation_date
        timestamp review_answer_timestamp
    }

    GEOLOCATION {
        string geolocation_zip_code_prefix PK
        float geolocation_lat
        float geolocation_lng
        string geolocation_city
        string geolocation_state
    }

    CATEGORY_TRANSLATION {
        string product_category_name PK
        string product_category_name_english
    }
```

---

## Order Event Workflow (State Machine)

```mermaid
stateDiagram-v2
    [*] --> PLACED: order_purchase_timestamp
    
    PLACED --> APPROVED: order_approved_at
    PLACED --> CANCELLED: order_status = 'canceled'
    
    APPROVED --> SHIPPED: order_delivered_carrier_date
    APPROVED --> CANCELED: order_status = 'canceled'
    
    SHIPPED --> DELIVERED: order_delivered_customer_date
    SHIPPED --> CANCELED: order_status = 'canceled'
    
    DELIVERED --> REVIEWED: review_creation_date
    DELIVERED --> [*]
    
    REVIEWED --> [*]
    CANCELED --> [*]
```

---

## Delivery Reliability KPI Flow

```mermaid
flowchart LR
    subgraph Raw Data
        A[orders.csv] --> B{Valid Delivery?}
        A --> C[delivery_status_unclear]
    end
    
    B -->|Yes| D[On-Time Check]
    B -->|No| E[Late Delivery]
    
    D -->|delivered <= estimated| F[ON TIME]
    D -->|delivered > estimated| E
    
    F --> G[On-Time Rate %]
    E --> H[Avg Delay Days]
    
    G --> I[Metrics Evidence Table]
    H --> I
    
    C --> J[Excluded from KPI]
    J --> K[Logged Separately]
```

---

## Pipeline Stage Diagram

```mermaid
flowchart TD
    subgraph Stage 1 [INGEST]
        A1[Olist CSV Files] --> A2[Verify Completeness]
        B1[Brasil API /feriados] --> B2[Cache JSON]
        A2 --> A3[Raw Data in data/raw/]
        B2 --> A3
    end
    
    subgraph Stage 2 [VALIDATE]
        A3 --> C1[Profile Tables]
        C1 --> C2[Apply Validation Rules]
        C2 --> C3[Flag Bad Records]
        C3 --> C4[Validated Data in data/validated/]
    end
    
    subgraph Stage 3 [TRANSFORM]
        C4 --> D1[Reconstruct Events]
        D1 --> D2[Calculate Outcomes]
        D2 --> D3[Build State Aggregates]
        D3 --> D4[Modeled Data in data/modeled/]
    end
    
    subgraph Stage 4 [METRICS]
        D4 --> E1[Compute 5 KPIs]
        E1 --> E2[Generate Evidence Table]
        E2 --> E3[Output to data/modeled/output/]
    end
```

---

## Key Field Lineage for Delivery Reliability

| Event/Field | Source Table | Used For |
|-------------|--------------|----------|
| Order Placed | `orders.order_purchase_timestamp` | Event reconstruction, denominator |
| Order Approved | `orders.order_approved_at` | Pre-ship delay calculation |
| Order Shipped | `orders.order_delivered_carrier_date` | In-transit delay calculation |
| Order Delivered | `orders.order_delivered_customer_date` | On-time check, denominator |
| Estimated Delivery | `orders.order_estimated_delivery_date` | On-time check baseline |
| Customer State | `customers.customer_state` | Geographic segmentation |
| Review Score | `order_reviews.review_score` | Review correlation metric |
| Holiday Proximity | `brasil_holidays.json` | Context flag (not KPI reclassification) |