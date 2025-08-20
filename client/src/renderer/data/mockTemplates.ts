export interface Template {
  id: string;
  name: string;
  customerId?: string;
  customerName?: string;
  description?: string;

  // Signature information
  signatureId: string;
  signatureName: string;
  signatureVersion: number;
  signatureAnchors: SignatureAnchor[];

  // Extraction rules
  extractionRuleId: string;
  extractionRuleVersion: number;
  extractionFields: ExtractionFieldSpec[];

  // Metadata
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  lastModifiedBy: string;
  isActive: boolean;

  // Usage statistics
  usageCount: number;
  lastUsedAt?: Date;
  successRate?: number;

  // Template status
  status: "draft" | "active" | "archived" | "testing";

  // Tags for organization
  tags: string[];

  // Preview/thumbnail
  previewImageUrl?: string;
  samplePdfUrl?: string;
}

export interface SignatureAnchor {
  type:
    | "word"
    | "text_line"
    | "table"
    | "rect"
    | "curve"
    | "graphic_line"
    | "image";
  page: number;
  bbox: [number, number, number, number];
  text?: string;
}

export interface ExtractionFieldSpec {
  method: "text_from_anchor" | "text_in_bbox";
  fieldName: string;
  page: number;
  anchorText?: string;
  anchorBBox?: [number, number, number, number];
  direction?: "right" | "below";
  bbox?: [number, number, number, number];
}

export const mockTemplates: Template[] = [
  {
    id: "1",
    name: "Standard BOL Template",
    customerName: "ABC Logistics",
    description: "Standard Bill of Lading template for ABC Logistics shipments",
    signatureId: "sig-001",
    signatureName: "ABC_BOL_v1",
    signatureVersion: 1,
    signatureAnchors: [
      {
        type: "text_line",
        page: 0,
        bbox: [100, 200, 300, 220],
        text: "Bill of Lading",
      },
      { type: "word", page: 0, bbox: [150, 250, 200, 270], text: "BOL#" },
    ],
    extractionRuleId: "rule-001",
    extractionRuleVersion: 1,
    extractionFields: [
      {
        method: "text_from_anchor",
        fieldName: "bol_number",
        page: 0,
        anchorText: "BOL#",
        direction: "right",
      },
      {
        method: "text_in_bbox",
        fieldName: "shipper_name",
        page: 0,
        bbox: [100, 300, 400, 320],
      },
    ],
    createdAt: new Date("2024-01-15"),
    updatedAt: new Date("2024-03-20"),
    createdBy: "admin@company.com",
    lastModifiedBy: "admin@company.com",
    isActive: true,
    usageCount: 1250,
    lastUsedAt: new Date("2024-03-19"),
    successRate: 94.2,
    status: "active",
    tags: ["BOL", "logistics", "standard"],
  },
  {
    id: "2",
    name: "Custom Receipt Template",
    customerName: "XYZ Manufacturing",
    description: "Custom receipt template for manufacturing parts",
    signatureId: "sig-002",
    signatureName: "XYZ_Receipt_v2",
    signatureVersion: 2,
    signatureAnchors: [
      {
        type: "text_line",
        page: 0,
        bbox: [50, 100, 250, 120],
        text: "Receipt for Parts",
      },
      { type: "word", page: 0, bbox: [200, 150, 250, 170], text: "PO#" },
    ],
    extractionRuleId: "rule-002",
    extractionRuleVersion: 2,
    extractionFields: [
      {
        method: "text_from_anchor",
        fieldName: "po_number",
        page: 0,
        anchorText: "PO#",
        direction: "right",
      },
      {
        method: "text_in_bbox",
        fieldName: "part_number",
        page: 0,
        bbox: [100, 200, 300, 220],
      },
    ],
    createdAt: new Date("2024-02-01"),
    updatedAt: new Date("2024-03-15"),
    createdBy: "user@company.com",
    lastModifiedBy: "admin@company.com",
    isActive: true,
    usageCount: 567,
    lastUsedAt: new Date("2024-03-18"),
    successRate: 87.5,
    status: "active",
    tags: ["receipt", "manufacturing", "parts"],
  },
  {
    id: "3",
    name: "Draft Template - New Customer",
    customerName: "NewCorp Industries",
    description: "Template in development for new customer onboarding",
    signatureId: "sig-003",
    signatureName: "NewCorp_Invoice_v1",
    signatureVersion: 1,
    signatureAnchors: [
      {
        type: "text_line",
        page: 0,
        bbox: [100, 100, 300, 120],
        text: "Invoice",
      },
    ],
    extractionRuleId: "rule-003",
    extractionRuleVersion: 1,
    extractionFields: [
      {
        method: "text_in_bbox",
        fieldName: "invoice_number",
        page: 0,
        bbox: [150, 150, 250, 170],
      },
    ],
    createdAt: new Date("2024-03-10"),
    updatedAt: new Date("2024-03-21"),
    createdBy: "admin@company.com",
    lastModifiedBy: "admin@company.com",
    isActive: false,
    usageCount: 0,
    status: "draft",
    tags: ["invoice", "new-customer", "draft"],
  },
  {
    id: "4",
    name: "Archived - Old Format",
    customerName: "Legacy Corp",
    description: "Archived template for old document format",
    signatureId: "sig-004",
    signatureName: "Legacy_Format_v1",
    signatureVersion: 1,
    signatureAnchors: [
      {
        type: "text_line",
        page: 0,
        bbox: [50, 50, 200, 70],
        text: "Legacy Document",
      },
    ],
    extractionRuleId: "rule-004",
    extractionRuleVersion: 1,
    extractionFields: [
      {
        method: "text_in_bbox",
        fieldName: "document_id",
        page: 0,
        bbox: [100, 100, 200, 120],
      },
    ],
    createdAt: new Date("2023-06-15"),
    updatedAt: new Date("2024-01-10"),
    createdBy: "admin@company.com",
    lastModifiedBy: "admin@company.com",
    isActive: false,
    usageCount: 2340,
    lastUsedAt: new Date("2024-01-05"),
    successRate: 92.1,
    status: "archived",
    tags: ["legacy", "archived", "old-format"],
  },
];
