# Cloud-Hosted ETO Architecture – Three Zoom Levels
_All services run in the cloud; clients connect over the public Internet._

---

## Level 1 • High-Level Cloud View
<pre class="mermaid">
flowchart LR
    subgraph CLOUD["Cloud Infrastructure"]
        direction LR
        Mail["Outlook 365<br/><i>Webhook / Poll</i>"]
        Watcher["Watcher Container<br/><i>Graph / IMAP listener</i>"]
        Queue["Message Queue<br/><i>SQS / Service Bus</i>"]
        Extractor["Extractor Workers<br/><i>ECS / AKS / Fargate</i>"]
        Blob["Object Storage<br/><i>S3 / Azure Blob</i>"]
        SQL["Managed SQL&nbsp;DB<br/><i>Orders &amp; Customers</i>"]
        API["REST / GraphQL API<br/><i>API Gateway + Lambda</i>"]
    end
    subgraph INTERNET[" "]
        UI["ETO Web&nbsp;App<br/><i>React / Electron shell</i>"]
    end

    Mail --> Watcher
    Watcher --> Blob
    Watcher --> Queue
    Queue --> Extractor
    Extractor --> Blob
    Extractor --> SQL
    UI -->|HTTPS| API
    API --> SQL
    UI -->|Fetch PDFs| Blob
</pre>

---

## Level 2 • Component Breakdown
<pre class="mermaid">
flowchart TD
    subgraph Messaging
        Watcher["Watcher<br/>Container"]
        Queue[(Queue)]
        Extractor["Extractor<br/>Worker x N"]
        Watcher -->|enqueue| Queue
        Queue -->|dequeue| Extractor
    end

    subgraph Storage
        Blob["Object<br/>Storage"]
        SQL["Managed<br/>SQL DB"]
    end

    subgraph API["Public API"]
        Gateway["API&nbsp;Gateway"]
        Lambda["Auth Layer<br/>(&nbsp;Lambda&nbsp;/&nbsp;Container&nbsp;)"]
        Gateway --> Lambda --> SQL
    end

    Mail["Outlook 365 Webhook"] --> Watcher
    Extractor --> Blob
    Extractor --> SQL
    UI["Client&nbsp;App"] -->|HTTPS| Gateway
    UI -->|GET PDF| Blob
</pre>

---

## Level 3 • Data Model & Cloud Workflow

### 3 A – Entity-Relationship (unchanged)
<pre class="mermaid">
erDiagram
    RUN_LOG ||--o{ PDF_FILE : stores
    SIGNATURE ||--o{ EXTRACTION_RULE : defines
    CUSTOMER ||--|{ SIGNATURE : default_for
    RUN_LOG ||--o{ ORDERS : created_from

    RUN_LOG {
        bigint run_id PK
        datetime received_ts
        varchar sender
        varchar subject
        int pdf_id FK
        int signature_id FK
        varchar status
        text error_msg
    }
    PDF_FILE {
        int pdf_id PK
        varchar object_url
        int run_id FK
        varchar sha256
    }
    SIGNATURE {
        int signature_id PK
        varchar pattern_desc
        varchar pattern_type
        int customer_id FK
        float accuracy_score
        datetime last_used
    }
    EXTRACTION_RULE {
        int rule_id PK
        int signature_id FK
        varchar field_name
        varchar method
        text params
    }
    CUSTOMER {
        int customer_id PK
        varchar name
        varchar email_domain
    }
    ORDERS {
        int order_id PK
        int customer_id FK
        datetime created_ts
    }
</pre>

### 3 B – Sequence Workflow (cloud variant)
<pre class="mermaid">
sequenceDiagram
    autonumber
    participant O365 as "Outlook 365"
    participant W as "Watcher Container"
    participant Q as "Queue"
    participant X as "Extractor Worker"
    participant B as "Blob Storage"
    participant DB as "SQL"
    participant API as "API Gateway"
    participant UI as "Client UI"

    O365 ->> W: Mail webhook payload
    W ->> B: PUT PDF
    W ->> Q: enqueue run_id

    loop parallel workers
        X ->> Q: poll message
        X ->> B: GET PDF
        alt signature known
            X ->> DB: INSERT Orders
            X ->> DB: UPDATE Run_Log status=SUCCESS
        else signature missing
            X ->> DB: UPDATE Run_Log status=UNRECOGNIZED
        end
    end

    UI ->> API: GET /runs?status!=SUCCESS
    API ->> DB: SELECT
    DB -->> API: rows
    API -->> UI: JSON
    UI ->> B: GET PDF object
    UI ->> API: POST /templates
    API ->> DB: INSERT Signature & Rules
    API ->> DB: UPDATE Run_Log status=SUCCESS
</pre>
