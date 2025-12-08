/**
 * CustomerSelect
 * Reusable dropdown component for selecting a customer
 * Fetches customers from the Access database via API
 */

import { useCustomers } from '../../api/hooks';

interface CustomerSelectProps {
  value: number | null;
  onChange: (customerId: number | null) => void;
  disabled?: boolean;
}

export function CustomerSelect({ value, onChange, disabled = false }: CustomerSelectProps) {
  const { data: customers, isLoading, error } = useCustomers();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = e.target.value;
    // Convert empty string to null, otherwise parse as number
    onChange(selectedValue === '' ? null : parseInt(selectedValue, 10));
  };

  const isDisabled = isLoading || disabled;

  return (
    <div>
      <label className="block text-xs font-medium text-gray-300 mb-1.5">
        Customer {disabled && <span className="text-gray-500 font-normal">(locked)</span>}
      </label>
      <select
        value={value === null ? '' : value}
        onChange={handleChange}
        disabled={isDisabled}
        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <option value="">Loading customers...</option>
        ) : error ? (
          <option value="">Error loading customers</option>
        ) : (
          <>
            <option value="">Select Customer</option>
            {customers?.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name}
              </option>
            ))}
          </>
        )}
      </select>
    </div>
  );
}
