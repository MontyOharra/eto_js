/**
 * AddressSearchPicker Component
 *
 * Searchable dropdown for selecting an address from the HTC database.
 * Features debounced search, paginated results, and infinite-scroll-style loading.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { useAddresses } from '../../api/hooks';

const PAGE_SIZE = 50;
const DEBOUNCE_MS = 300;

interface AddressOption {
  id: number;
  name: string;
  address: string;
}

interface AddressSearchPickerProps {
  selectedAddressId?: number;
  onSelect: (addressId: number | undefined) => void;
}

export function AddressSearchPicker({
  selectedAddressId,
  onSelect,
}: AddressSearchPickerProps) {
  const [searchText, setSearchText] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [accumulated, setAccumulated] = useState<AddressOption[]>([]);
  // Store the full selected address so it persists after search/accumulated resets
  const [selectedAddress, setSelectedAddress] = useState<AddressOption | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchText);
      setOffset(0);
      setAccumulated([]);
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchText]);

  // Fetch addresses with current search and offset
  const { data, isFetching } = useAddresses(
    {
      search: debouncedSearch || undefined,
      limit: PAGE_SIZE,
      offset,
    },
    isOpen
  );

  // Accumulate pages of results
  useEffect(() => {
    if (data?.addresses) {
      if (offset === 0) {
        setAccumulated(data.addresses);
      } else {
        setAccumulated((prev) => {
          // Avoid duplicates from race conditions
          const existingIds = new Set(prev.map((a) => a.id));
          const newItems = data.addresses.filter((a) => !existingIds.has(a.id));
          return [...prev, ...newItems];
        });
      }
    }
  }, [data, offset]);

  const total = data?.total ?? 0;
  const hasMore = accumulated.length < total;

  // Load next page
  const loadMore = useCallback(() => {
    if (!isFetching && hasMore) {
      setOffset((prev) => prev + PAGE_SIZE);
    }
  }, [isFetching, hasMore]);

  // Scroll handler for infinite scroll
  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    // Load more when within 50px of bottom
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
      loadMore();
    }
  }, [loadMore]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (addr: AddressOption) => {
    setSelectedAddress(addr);
    onSelect(addr.id);
    setIsOpen(false);
    setSearchText('');
  };

  const handleClear = () => {
    setSelectedAddress(null);
    onSelect(undefined);
    setSearchText('');
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Selected address display / Search input */}
      {selectedAddress ? (
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm">
          <div className="flex-1 min-w-0">
            <div className="text-white font-medium truncate">{selectedAddress.name}</div>
            <div className="text-gray-400 text-xs truncate">{selectedAddress.address}</div>
          </div>
          <button
            type="button"
            onClick={handleClear}
            className="text-gray-400 hover:text-white shrink-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ) : (
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onFocus={() => setIsOpen(true)}
            placeholder="Search by company name or address..."
            className="w-full px-3 py-2 pr-8 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <svg
            className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      )}

      {/* Dropdown results */}
      {isOpen && (
        <div className="absolute z-10 left-0 right-0 top-full mt-1 bg-gray-700 border border-gray-600 rounded-lg shadow-xl overflow-hidden">
          <div
            ref={listRef}
            onScroll={handleScroll}
            className="max-h-48 overflow-y-auto"
          >
            {accumulated.length === 0 && !isFetching && (
              <div className="px-3 py-4 text-center text-gray-400 text-sm">
                {debouncedSearch ? 'No addresses found' : 'Type to search addresses...'}
              </div>
            )}

            {accumulated.map((addr) => (
              <button
                key={addr.id}
                type="button"
                onClick={() => handleSelect(addr)}
                className={`w-full text-left px-3 py-2 hover:bg-gray-600 transition-colors border-b border-gray-600/50 last:border-b-0 ${
                  addr.id === selectedAddressId ? 'bg-blue-600/20' : ''
                }`}
              >
                <div className="text-white text-sm font-medium truncate">{addr.name}</div>
                <div className="text-gray-400 text-xs truncate">{addr.address}</div>
              </button>
            ))}

            {isFetching && (
              <div className="px-3 py-2 text-center text-gray-400 text-xs">
                Loading...
              </div>
            )}

            {hasMore && !isFetching && (
              <button
                type="button"
                onClick={loadMore}
                className="w-full px-3 py-2 text-center text-blue-400 hover:text-blue-300 text-xs hover:bg-gray-600/50 transition-colors"
              >
                Load more ({accumulated.length} of {total})
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
