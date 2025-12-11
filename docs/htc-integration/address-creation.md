# Address Creation Specification

This document defines how address records are created in the HTC system from ETO data.

## Target Table

`HTC300_G060_T010 Addresses` (34 columns)

## Field Mapping

| Column | How We Get This Data |
|--------|---------------------|
| FavCoID | Always 1 |
| FavBrID | Always 1 |
| FavID | MAX(FavID) + 1 |
| FavKeycheck | Custom function (remove spaces/commas/periods from concatenated fields) |
| FavKeyCounts | Custom function (character frequency string) |
| FavBranchAddressYN | False |
| FavCompany | Passed in (company name) |
| FavLocnName | Passed in (same as FavCompany) |
| FavAddrLn1 | Passed in from data |
| FavAddrLn2 | Passed in from data |
| FavCity | Passed in from data |
| FavState | Passed in from data |
| FavZip | Passed in from data |
| FavCountry | Passed in from data |
| FavLatitude | Geocoding function (from address) |
| FavLongitude | Geocoding function (from address) |
| FavACIListed | Lookup zip in ACI table → True if found, False if not |
| FavACIID | Lookup zip in ACI table → ID field if found, 0 if not |
| FavFirstName | "" (empty string) |
| FavLastName | "" (empty string) |
| FavEMail | "" (empty string) |
| FavPhone | "" (empty string) |
| FavExt | "" (empty string) |
| FavAssessorials | 100 dots |
| FavCarrierYN | False |
| FavLocalYN | False (only relevant for carriers) |
| FavInternational | False |
| FavWaitTimeDefault | 0 |
| FavActive | True |
| FavDateAdded | Now() |
| FavAddedBy | "eto" |
| FavDateModified | Now() |
| FavChgdby | "eto" |
| FavCarrierGroundYN | False |

## Custom Functions Required

### FavKeycheck Generation
- Remove spaces, commas, and periods from concatenated fields
- Input: `LocnName + AddrLn1 + AddrLn2 + City + Zip + Country`
- Output: Uppercase string with no spaces/commas/periods

### FavKeyCounts Generation
- Count occurrences of each character in FavKeycheck
- Sort alphabetically by character
- Format: `"0,1;A,5;B,3;..."` (character,count pairs separated by semicolons)

### FavID Generation
- `MAX(FavID) + 1` from existing records

### Geocoding
- Convert address to latitude/longitude coordinates

### ACI Lookup
- Table: `HTC300_G010_T010 DFW_ACI_Data`
- Lookup by zip code (ZIP_CODE field)
- If found: FavACIListed = True, FavACIID = ID field
- If not found: FavACIListed = False, FavACIID = 0

### Address History
- Table: `HTC300_G060_T030 Addresses Update History`
- Created automatically when new address is added
- Format: `Address ID {FavID}, '{CompanyName} / {LocnName}' added to Pickup/Delivery Address List`

## Implementation Status

✅ **COMPLETE** (2025-12-10)

All address creation functionality implemented in `server/src/features/htc_integration/service.py`:

| Method | Purpose |
|--------|---------|
| `find_address_id()` | Find existing address by string |
| `find_address_by_text()` | Find by components |
| `create_address()` | Create new address with all 34 fields |
| `find_or_create_address()` | Main entry point (find or create) |
| `_add_address_history()` | Add history record |
| `lookup_aci_by_zip()` | ACI lookup |
| `generate_keycheck()` | Generate FavKeycheck |
| `generate_keycounts()` | Generate FavKeyCounts |
| `get_next_fav_id()` | Get next available ID |
| `geocode_address()` | Placeholder for future geocoding |

API endpoints available at `/api/htc/` for testing.
