import { BaseModuleTemplate } from '../types/modules';

// Export empty test modules array since mock extraction and order generation modules are being removed
export const testModules: BaseModuleTemplate[] = [];

// Keep mockExtractedFields for backward compatibility with existing pipeline execution code
// TODO: Remove this once custom input/output definers are implemented
export const mockExtractedFields = [
  { name: 'hawb', displayName: 'HAWB Number', sampleValue: 'HAW123456789' },
  { name: 'carrier_name', displayName: 'Carrier Name', sampleValue: 'Forward Air, Inc' },
  { name: 'pickup_address', displayName: 'Pickup Address', sampleValue: '1234 Main St, Dallas, TX 75201' },
  { name: 'pickup_phone', displayName: 'Pickup Phone', sampleValue: '(555) 123-4567' },
  { name: 'delivery_address', displayName: 'Delivery Address', sampleValue: '5678 Oak Ave, Houston, TX 77001' },
  { name: 'delivery_phone', displayName: 'Delivery Phone', sampleValue: '(555) 987-6543' },
  { name: 'weight', displayName: 'Weight', sampleValue: '25.5' },
  { name: 'dimensions', displayName: 'Dimensions', sampleValue: '12x8x6' },
  { name: 'service_type', displayName: 'Service Type', sampleValue: 'Standard Ground' },
  { name: 'tracking_number', displayName: 'Tracking Number', sampleValue: 'TRK987654321' }
];

