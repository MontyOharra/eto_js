<!-- eto_architecture.md  —  ALL diagrams in one file -->

# ETO Architecture – Three Zoom Levels
_A single Markdown file containing every diagram._

---

## Level 1 • High-Level Architecture
<pre class="mermaid">
flowchart LR
    subgraph LAN["Local Network"]
        direction LR
        Outlook["Outlook Client<br/><i>Server&nbsp;PC</i>"]
        ETO["ETO Python Service<br/><i>Watcher&nbsp;+&nbsp;Extractor</i>"]
        DB["Access&nbsp;/&nbsp;SQL&nbsp;Server<br/>&ldquo;Orders&rdquo;&nbsp;&amp;&nbsp;&ldquo;Customers&rdquo;"]
        Clients["User Frontend App<br/><i>Client&nbsp;PCs&nbsp;&times;&nbsp;N</i>"]
    end
    Outlook -->|Emails&nbsp;+&nbsp;Attachments| ETO
    ETO -->|SQL&nbsp;/&nbsp;ODBC| DB
    Clients -->|Queries&nbsp;&amp;&nbsp;Updates| DB
    Clients -->|Fetch&nbsp;PDF| ETO
</pre>

---

## Level 2 • Component Breakdown
<pre class="mermaid">
flowchart TD
    subgraph SERVER["Server&nbsp;PC"]
        direction TB
        Outlook["Outlook<br/>Folder&nbsp;Rules"]
        Watcher["Outlook Watcher<br/><i>win32com&nbsp;hook</i>"]
        Ingest["ETO_Run_Log<br/><i>insert&nbsp;row</i>"]
        Extractor["PDF Extractor<br/><i>signature&nbsp;→&nbsp;data</i>"]
        Storage["PDF Store<br/><i>share&nbsp;or&nbsp;BLOB</i>"]
        DB["SQL&nbsp;Server<br/>Production&nbsp;DB"]
    end
    subgraph CLIENTS["Client&nbsp;PCs"]
        UI["ETO&nbsp;UI<br/>(Electron&nbsp;/&nbsp;Web)"]
    end
    Outlook -->|New&nbsp;mail| Watcher
    Watcher -->|Insert&nbsp;run&nbsp;+&nbsp;PDF| Ingest
    Ingest --> Storage
    Extractor -->|Extract&nbsp;fields| DB
    Extractor -->|Update&nbsp;status| Ingest
    UI -->|Query&nbsp;runs&nbsp;&amp;&nbsp;orders| DB
    UI -->|Fetch&nbsp;PDF| Storage
    UI -->|Save&nbsp;templates| DB
</pre>

---

## Level 3 • Data Model & Workflow

### 3 A – Entity-Relationship Diagram
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
        varchar path_or_blob
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

### 3 B – Sequence Workflow
<pre class="mermaid">
sequenceDiagram
    autonumber
    participant OL as "Outlook Folder"
    participant W  as "Watcher"
    participant DB as "SQL DB"
    participant E  as "Extractor"
    participant UI as "Client UI"
    participant U  as "User"

    %% --- Mail arrives ---
    OL ->> W : Mail received
    W  ->> DB: INSERT RUN_LOG status=PENDING
    W  ->> DB: INSERT PDF_FILE record
    Note over W : Attachment saved to share or BLOB

    %% --- Background processing loop ---
    loop every N seconds
        E ->> DB: SELECT pending runs
        alt Signature known
            E ->> DB: SELECT extraction rules
            E ->> DB: INSERT ORDERS row
            E ->> DB: UPDATE RUN_LOG status=SUCCESS
        else Signature unknown
            E ->> DB: UPDATE RUN_LOG status=UNRECOGNIZED
        end
    end

    %% --- User review ---
    UI ->> DB: SELECT runs where status!=SUCCESS
    UI ->> DB: SELECT PDF_FILE by run_id
    UI ->> U : Display PDF and form
    U  -->> UI: Save mapping
    UI ->> DB: INSERT new SIGNATURE and RULES
    UI ->> DB: UPDATE RUN_LOG status=SUCCESS
</pre>
