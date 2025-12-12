/**
 * CustomerSelect
 * Searchable autocomplete dropdown component for selecting a customer
 * Fetches customers from the Access database via API
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { useCustomers } from '../../api/hooks';

interface CustomerSelectProps {
  value: number | null;
  onChange: (customerId: number | null) => void;
  disabled?: boolean;
}

export function CustomerSelect({ value, onChange, disabled = false }: CustomerSelectProps) {
  const { data: customers, isLoading, error } = useCustomers();

  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Get the selected customer's name for display
  const selectedCustomer = useMemo(() => {
    if (value === null || !customers) return null;
    return customers.find((c) => c.id === value) ?? null;
  }, [value, customers]);

  // Filter customers based on search text
  const filteredCustomers = useMemo(() => {
    if (!customers) return [];
    if (!searchText.trim()) return customers;

    const search = searchText.toLowerCase();
    return customers.filter((customer) =>
      customer.name.toLowerCase().includes(search)
    );
  }, [customers, searchText]);

  // Reset highlight when filtered list changes
  useEffect(() => {
    setHighlightedIndex(0);
  }, [filteredCustomers.length]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlightedElement = listRef.current.children[highlightedIndex] as HTMLElement;
      if (highlightedElement) {
        highlightedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        // Reset search text to selected customer name when closing
        setSearchText('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
    if (!isOpen) setIsOpen(true);
  };

  const handleInputFocus = () => {
    setIsOpen(true);
    // Select all text on focus for easy replacement
    inputRef.current?.select();
  };

  const handleSelect = (customerId: number) => {
    onChange(customerId);
    setSearchText('');
    setIsOpen(false);
    inputRef.current?.blur();
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(null);
    setSearchText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredCustomers.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredCustomers[highlightedIndex]) {
          handleSelect(filteredCustomers[highlightedIndex].id);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSearchText('');
        inputRef.current?.blur();
        break;
      case 'Tab':
        setIsOpen(false);
        setSearchText('');
        break;
    }
  };

  const isDisabled = isLoading || disabled;

  // Display text: search text when typing, otherwise selected customer name
  const displayText = isOpen ? searchText : (selectedCustomer?.name ?? '');

  return (
    <div>
      <label className="block text-xs font-medium text-gray-300 mb-1.5">
        Customer {disabled && <span className="text-gray-500 font-normal">(locked)</span>}
      </label>

      <div ref={dropdownRef} className="relative">
        {/* Input with dropdown arrow */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={displayText}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onKeyDown={handleKeyDown}
            disabled={isDisabled}
            placeholder={isLoading ? 'Loading customers...' : error ? 'Error loading customers' : 'Search or select customer...'}
            className="w-full px-3 py-2 pr-16 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />

          {/* Clear button (when value selected) */}
          {value !== null && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-8 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-white transition-colors"
              tabIndex={-1}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          {/* Dropdown arrow */}
          <button
            type="button"
            onClick={() => !isDisabled && setIsOpen(!isOpen)}
            disabled={isDisabled}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
            tabIndex={-1}
          >
            <svg
              className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Dropdown list */}
        {isOpen && !isDisabled && (
          <ul
            ref={listRef}
            className="absolute z-50 w-full mt-1 max-h-60 overflow-auto bg-gray-800 border border-gray-600 rounded shadow-lg"
          >
            {filteredCustomers.length === 0 ? (
              <li className="px-3 py-2 text-sm text-gray-400 italic">
                {searchText ? 'No customers found' : 'No customers available'}
              </li>
            ) : (
              filteredCustomers.map((customer, index) => (
                <li
                  key={customer.id}
                  onClick={() => handleSelect(customer.id)}
                  className={`px-3 py-2 text-sm cursor-pointer transition-colors ${
                    index === highlightedIndex
                      ? 'bg-blue-600 text-white'
                      : customer.id === value
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-200 hover:bg-gray-700'
                  }`}
                >
                  {customer.name}
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
