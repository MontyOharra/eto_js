"""
HTC Address Utilities

Provides address-related operations for the HTC database:
- Address parsing and normalization
- Address lookup/resolution
- Address creation
"""

import re
import usaddress
from datetime import datetime
from typing import Any, Callable

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError

logger = get_logger(__name__)


# ==================== Address Utils Class ====================

class HtcAddressUtils:
    """
    Utility class for HTC address operations.

    Provides methods for address parsing, normalization, lookup, and creation.
    """

    # Street type abbreviations - map full names to standard abbreviations
    STREET_TYPE_ABBREV = {
        'STREET': 'ST',
        'AVENUE': 'AVE',
        'BOULEVARD': 'BLVD',
        'PARKWAY': 'PKWY',
        'DRIVE': 'DR',
        'ROAD': 'RD',
        'LANE': 'LN',
        'COURT': 'CT',
        'CIRCLE': 'CIR',
        'PLACE': 'PL',
        'HIGHWAY': 'HWY',
        'FREEWAY': 'FWY',
        'EXPRESSWAY': 'EXPY',
        'TERRACE': 'TER',
        'TRAIL': 'TRL',
        'WAY': 'WAY',
        'LOOP': 'LOOP',
        'CROSSING': 'XING',
        'SQUARE': 'SQ',
        'PASS': 'PASS',
        'PATH': 'PATH',
        'PIKE': 'PIKE',
        'ALLEY': 'ALY',
        'BEND': 'BND',
        'COVE': 'CV',
        'CREEK': 'CRK',
        'ESTATE': 'EST',
        'ESTATES': 'ESTS',
        'FALLS': 'FLS',
        'FERRY': 'FRY',
        'FIELD': 'FLD',
        'FIELDS': 'FLDS',
        'FLAT': 'FLT',
        'FLATS': 'FLTS',
        'FORD': 'FRD',
        'FOREST': 'FRST',
        'FORGE': 'FRG',
        'FORK': 'FRK',
        'FORKS': 'FRKS',
        'GARDEN': 'GDN',
        'GARDENS': 'GDNS',
        'GATEWAY': 'GTWY',
        'GLEN': 'GLN',
        'GREEN': 'GRN',
        'GROVE': 'GRV',
        'HARBOR': 'HBR',
        'HAVEN': 'HVN',
        'HEIGHTS': 'HTS',
        'HILL': 'HL',
        'HILLS': 'HLS',
        'HOLLOW': 'HOLW',
        'INLET': 'INLT',
        'ISLAND': 'IS',
        'ISLANDS': 'ISS',
        'JUNCTION': 'JCT',
        'KEY': 'KY',
        'KNOLL': 'KNL',
        'LAKE': 'LK',
        'LAKES': 'LKS',
        'LANDING': 'LNDG',
        'MEADOW': 'MDW',
        'MEADOWS': 'MDWS',
        'MILL': 'ML',
        'MILLS': 'MLS',
        'MISSION': 'MSN',
        'MOUNT': 'MT',
        'MOUNTAIN': 'MTN',
        'ORCHARD': 'ORCH',
        'PARK': 'PARK',
        'PARKS': 'PARK',
        'POINT': 'PT',
        'POINTS': 'PTS',
        'PORT': 'PRT',
        'PRAIRIE': 'PR',
        'RANCH': 'RNCH',
        'RAPIDS': 'RPDS',
        'RIDGE': 'RDG',
        'RIVER': 'RIV',
        'RUN': 'RUN',
        'SHORE': 'SHR',
        'SHORES': 'SHRS',
        'SPRING': 'SPG',
        'SPRINGS': 'SPGS',
        'STATION': 'STA',
        'STREAM': 'STRM',
        'SUMMIT': 'SMT',
        'TRACE': 'TRCE',
        'TRACK': 'TRAK',
        'TURNPIKE': 'TPKE',
        'VALLEY': 'VLY',
        'VIEW': 'VW',
        'VIEWS': 'VWS',
        'VILLAGE': 'VLG',
        'VISTA': 'VIS',
        'WALK': 'WALK',
        'WELL': 'WL',
        'WELLS': 'WLS',
    }

    # Directional abbreviations
    DIRECTIONAL_ABBREV = {
        'NORTH': 'N',
        'SOUTH': 'S',
        'EAST': 'E',
        'WEST': 'W',
        'NORTHEAST': 'NE',
        'NORTHWEST': 'NW',
        'SOUTHEAST': 'SE',
        'SOUTHWEST': 'SW',
    }

    # Unit type abbreviations
    UNIT_TYPE_ABBREV = {
        'APARTMENT': 'APT',
        'BUILDING': 'BLDG',
        'DEPARTMENT': 'DEPT',
        'FLOOR': 'FL',
        'SUITE': 'STE',
        'UNIT': 'UNIT',
        'ROOM': 'RM',
        'SPACE': 'SPC',
        'STOP': 'STOP',
        'TRAILER': 'TRLR',
        'BOX': 'BOX',
        'LOBBY': 'LBBY',
        'LOWER': 'LOWR',
        'OFFICE': 'OFC',
        'PENTHOUSE': 'PH',
        'PIER': 'PIER',
        'REAR': 'REAR',
        'SIDE': 'SIDE',
        'SLIP': 'SLIP',
        'UPPER': 'UPPR',
        'HANGAR': 'HNGR',
        'BASEMENT': 'BSMT',
        'FRONT': 'FRNT',
    }

    # Unit type designators to strip during normalization (we keep only the identifier)
    UNIT_DESIGNATORS_TO_STRIP = {
        '#', 'SUITE', 'STE', 'UNIT', 'APT', 'APARTMENT', 'BLDG', 'BUILDING',
        'FL', 'FLOOR', 'RM', 'ROOM', 'SPC', 'SPACE', 'DEPT', 'DEPARTMENT',
        'OFC', 'OFFICE', 'TRLR', 'TRAILER', 'LOT', 'SLIP', 'PIER', 'HNGR',
        'HANGAR', 'LBBY', 'LOBBY', 'PH', 'PENTHOUSE', 'BSMT', 'BASEMENT',
        'FRNT', 'FRONT', 'REAR', 'SIDE', 'LOWR', 'LOWER', 'UPPR', 'UPPER',
    }

    def __init__(
        self,
        get_connection: Callable[[], Any],
        co_id: int,
        br_id: int,
    ):
        """
        Initialize address utils.

        Args:
            get_connection: Callable that returns the database connection
            co_id: Company ID for HTC queries
            br_id: Branch ID for HTC queries
        """
        self._get_connection = get_connection
        self.CO_ID = co_id
        self.BR_ID = br_id

    # ==================== Address Normalization ====================

    def normalize_address_component(self, text: str) -> str:
        """
        Normalize a single address component (street name, city, etc).

        Normalization steps:
        1. Uppercase
        2. Remove periods
        3. Collapse multiple spaces
        4. Strip whitespace

        This does NOT expand/abbreviate - that's done separately for matching.
        """
        if not text:
            return ''

        result = text.upper()
        result = result.replace('.', '')
        result = ' '.join(result.split())  # Collapse multiple spaces
        return result.strip()

    def normalize_street_for_matching(self, street: str) -> str:
        """
        Normalize a street address for comparison matching.

        Steps:
        1. Basic normalization (uppercase, remove periods, collapse spaces)
        2. Expand all abbreviations to full forms for consistent comparison
        3. Strip unit type designators (keep only the identifier)
           So "#106D", "Suite 106D", "Ste 106D" all become just "106D"

        Args:
            street: Street address string (e.g., "123 N. Main St. #100")

        Returns:
            Normalized string (e.g., "123 NORTH MAIN STREET 100")
        """
        if not street:
            return ''

        # Basic normalization
        result = self.normalize_address_component(street)

        # Handle "#" attached to identifier (e.g., "#106D" -> "# 106D")
        # This ensures we can strip the "#" as a separate word
        result = re.sub(r'#(\w)', r'# \1', result)

        # Build reverse mappings (abbrev -> full) for expansion
        street_expand = {v: k for k, v in self.STREET_TYPE_ABBREV.items()}
        dir_expand = {v: k for k, v in self.DIRECTIONAL_ABBREV.items()}

        # Split into words and process each
        words = result.split()
        normalized_words = []

        for word in words:
            # Skip unit type designators entirely (we keep only the identifier)
            if word in self.UNIT_DESIGNATORS_TO_STRIP:
                continue
            # Try to expand street types
            elif word in street_expand:
                normalized_words.append(street_expand[word])
            # Try to expand directionals
            elif word in dir_expand:
                normalized_words.append(dir_expand[word])
            else:
                normalized_words.append(word)

        return ' '.join(normalized_words)

    # ==================== Address Parsing ====================

    def parse_address_string(self, address_string: str) -> dict[str, str] | None:
        """
        Parse a US address string into components using the usaddress library.

        Args:
            address_string: Full address string to parse
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"

        Returns:
            Dictionary with parsed components:
            - street: Full street line including suite/unit (e.g., "123 Main St Suite 100")
            - city: City name
            - state: State abbreviation
            - zip_code: ZIP code (without +4)
            Returns None if parsing fails or essential components missing.
        """

        if not address_string or not address_string.strip():
            logger.debug("Empty address string provided")
            return None

        logger.debug(f"Parsing address: '{address_string}'")

        try:
            parsed, address_type = usaddress.tag(address_string)
        except RepeatedLabelError as e:
            logger.warning(f"Address parsing ambiguous (repeated labels): {e}")
            return None

        # Build full street line (everything before city/state/zip)
        # This includes suite/unit info since that's how DB stores it
        street_parts = []

        # Street number
        if 'AddressNumber' in parsed:
            street_parts.append(parsed['AddressNumber'])

        # Pre-directional (N, S, E, W)
        if 'StreetNamePreDirectional' in parsed:
            street_parts.append(parsed['StreetNamePreDirectional'])

        # Street name
        if 'StreetName' in parsed:
            street_parts.append(parsed['StreetName'])

        # Street type (St, Ave, Blvd)
        if 'StreetNamePostType' in parsed:
            street_parts.append(parsed['StreetNamePostType'])

        # Post-directional
        if 'StreetNamePostDirectional' in parsed:
            street_parts.append(parsed['StreetNamePostDirectional'])

        # Suite/unit/apt - append to street line (matches DB storage)
        if 'OccupancyType' in parsed:
            street_parts.append(parsed['OccupancyType'])
        if 'OccupancyIdentifier' in parsed:
            street_parts.append(parsed['OccupancyIdentifier'])
        if 'SubaddressType' in parsed:
            street_parts.append(parsed['SubaddressType'])
        if 'SubaddressIdentifier' in parsed:
            street_parts.append(parsed['SubaddressIdentifier'])

        street = ' '.join(street_parts)

        # Extract location components
        city = parsed.get('PlaceName', '')
        state = parsed.get('StateName', '')
        zip_code = parsed.get('ZipCode', '')

        # Validate we have minimum required components
        if not street or not city or not state or not zip_code:
            logger.debug(f"Missing required components - street: '{street}', "
                        f"city: '{city}', state: '{state}', zip: '{zip_code}'")
            return None

        result = {
            'street': street,
            'city': city,
            'state': state,
            'zip_code': zip_code,
        }

        logger.debug(f"Parsed address: {result}")
        return result

    # ==================== Address Lookup ====================

    def find_address_by_text(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> float | None:
        """
        Search for an existing address in the database using normalized matching.

        Strategy:
        1. Filter candidates by city/state/zip (exact match after basic normalization)
        2. Load all matching addresses
        3. Normalize both input street and DB streets
        4. Find exact match after normalization

        Args:
            street: Full street line including suite (e.g., "123 Main St Suite 100")
            city: City name
            state: State abbreviation (e.g., "TX")
            zip_code: ZIP code (e.g., "75201")

        Returns:
            Address ID (FavID as float) if found, None otherwise.
        """
        connection = self._get_connection()

        # Normalize location components for filtering
        norm_city = self.normalize_address_component(city)
        norm_state = self.normalize_address_component(state)
        # For zip, just take first 5 digits
        norm_zip = zip_code[:5] if zip_code else ''

        # Normalize input street for comparison
        norm_input_street = self.normalize_street_for_matching(street)

        logger.debug(f"Searching for address - normalized street: '{norm_input_street}', "
                     f"city: '{norm_city}', state: '{norm_state}', zip: '{norm_zip}'")

        # Query: filter by city/state/zip (case-insensitive via UCASE - Access syntax)
        # We'll normalize the street comparison in Python for more control
        query = """
            SELECT FavID, FavAddrLn1, FavAddrLn2
            FROM [HTC300_G060_T010 Addresses]
            WHERE UCASE(FavCity) = ?
              AND UCASE(FavState) = ?
              AND LEFT(FavZip, 5) = ?
              AND FavActive = 1
        """
        params = (norm_city, norm_state, norm_zip)

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    logger.debug(f"No addresses found for {norm_city}, {norm_state} {norm_zip}")
                    return None

                logger.debug(f"Found {len(rows)} candidate addresses in {norm_city}, {norm_state}")

                # Check each candidate for normalized match
                for row in rows:
                    # Combine FavAddrLn1 and FavAddrLn2 for comparison
                    db_street_parts = [row.FavAddrLn1 or '']
                    if row.FavAddrLn2:
                        db_street_parts.append(row.FavAddrLn2)
                    db_street = ' '.join(db_street_parts)

                    # Normalize DB street
                    norm_db_street = self.normalize_street_for_matching(db_street)

                    # Exact match after normalization
                    if norm_input_street == norm_db_street:
                        address_id = float(row.FavID)
                        logger.debug(f"Found matching address: ID={address_id}, "
                                    f"DB street='{db_street}'")
                        return address_id

                logger.debug(f"No normalized match found for '{norm_input_street}'")
                return None

        except Exception as e:
            logger.error(f"Failed to search for address: {e}")
            raise

    def find_address_id(self, address_string: str) -> float | None:
        """
        Find an address ID from a full address string.

        This is the main entry point for address lookup.
        It parses the address string and searches for a normalized match.

        Strategy: Precision over recall
        - We normalize for valid variations (abbreviations, punctuation, case)
        - We do NOT fuzzy match - if it doesn't match, return None
        - False negatives are OK (caller can create new correct address)
        - False positives are NOT OK (we don't match to bad data)

        Args:
            address_string: Full address string to check
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"

        Returns:
            Address ID (FavID as float) if found, None otherwise.
        """
        logger.info(f"[FIND_ADDRESS_ID] Input: '{address_string}'")

        # Step 1: Parse the address string
        parsed = self.parse_address_string(address_string)

        if not parsed:
            logger.info(f"[FIND_ADDRESS_ID] Parse FAILED for: '{address_string}'")
            return None

        logger.info(
            f"[FIND_ADDRESS_ID] Parsed: street='{parsed['street']}', "
            f"city='{parsed['city']}', state='{parsed['state']}', zip='{parsed['zip_code']}'"
        )

        # Step 2: Search for the address in the database
        result = self.find_address_by_text(
            street=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
        )

        logger.info(f"[FIND_ADDRESS_ID] find_address_by_text returned: {result}")
        return result

    def find_or_create_address(
        self,
        address_string: str,
        company_name: str,
        country: str = "USA",
    ) -> float:
        """
        Find an existing address or create a new one.

        This is the main entry point for address resolution with creation fallback.

        Process:
        1. Parse the address string
        2. Search for existing address
        3. If found, return existing FavID
        4. If not found, create new address and return new FavID

        Args:
            address_string: Full address string to find/create
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"
            company_name: Company name to use if creating new address
            country: Country name (default: "USA")

        Returns:
            Address ID (FavID) as float - either existing or newly created

        Raises:
            ValueError: If address cannot be parsed
            OutputExecutionError: If address creation fails
        """
        logger.info(f"Finding or creating address: '{address_string}'")

        # Step 1: Parse the address string
        parsed = self.parse_address_string(address_string)

        if not parsed:
            raise ValueError(f"Could not parse address: '{address_string}'")

        # Step 2: Search for existing address
        existing_id = self.find_address_by_text(
            street=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
        )

        if existing_id is not None:
            logger.info(f"Found existing address with FavID: {existing_id}")
            return existing_id

        # Step 3: Create new address
        logger.info(f"Address not found, creating new address")
        new_id = self.create_address(
            company_name=company_name,
            addr_ln1=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
            country=country,
        )

        return new_id

    # ==================== Address Creation ====================

    def generate_keycheck(
        self,
        locn_name: str,
        addr_ln1: str,
        addr_ln2: str,
        city: str,
        zip_code: str,
        country: str,
    ) -> str:
        """
        Generate the FavKeycheck value for an address.

        Replicates VBA SpComPer_Removed function:
        - Concatenates: LocnName + AddrLn1 + AddrLn2 + City + Zip + Country
        - Removes spaces, commas, and periods
        - Returns uppercase string

        Args:
            locn_name: Location name
            addr_ln1: Address line 1
            addr_ln2: Address line 2
            city: City name
            zip_code: ZIP code
            country: Country name

        Returns:
            Keycheck string (max 100 chars to fit VARCHAR(100))
        """
        # Concatenate all parts
        combined = f"{locn_name}{addr_ln1}{addr_ln2}{city}{zip_code}{country}"

        # Remove spaces, commas, periods and uppercase
        result = combined.upper()
        result = result.replace(' ', '')
        result = result.replace(',', '')
        result = result.replace('.', '')

        # Truncate to 100 chars (VARCHAR(100) limit)
        return result[:100]

    def generate_keycounts(self, keycheck: str) -> str:
        """
        Generate the FavKeyCounts value from a keycheck string.

        Algorithm (replicates VBA logic):
        1. Count occurrences of each character in keycheck
        2. Sort alphabetically by character
        3. Format as: "A,5;B,3;C,1;..." (character,count pairs separated by semicolons)

        Args:
            keycheck: The keycheck string to analyze

        Returns:
            Formatted character count string (max 255 chars to fit VARCHAR(255))
        """
        if not keycheck:
            return ''

        # Count character occurrences
        char_counts: dict[str, int] = {}
        for char in keycheck:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Sort alphabetically by character
        sorted_chars = sorted(char_counts.keys())

        # Build result string: "A,5;B,3;..."
        parts = [f"{char},{char_counts[char]}" for char in sorted_chars]
        result = ';'.join(parts) + ';'

        # Truncate to 255 chars (VARCHAR(255) limit)
        return result[:255]

    def get_next_fav_id(self) -> float:
        """
        Get the next available FavID for a new address.

        Replicates VBA HTC200_GetNewAddrID function:
        - Query MAX(FavID) from addresses table
        - Return MAX + 1

        Returns:
            Next available FavID as float
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = "SELECT MAX(FavID) FROM [HTC300_G060_T010 Addresses]"
                cursor.execute(query)
                row = cursor.fetchone()

                if row is None or row[0] is None:
                    # No addresses exist yet
                    return 1.0

                return float(row[0]) + 1

        except Exception as e:
            logger.error(f"Failed to get next FavID: {e}")
            raise

    def lookup_aci_by_zip(self, zip_code: str) -> tuple:
        """
        Look up ACI data by ZIP code.

        Queries the DFW_ACI_Data table to find the ACI ID for a given ZIP code.

        Args:
            zip_code: ZIP code to look up (uses first 5 characters)

        Returns:
            Tuple of (aci_listed: bool, aci_id: int)
            - (True, ID) if found
            - (False, 0) if not found
        """
        connection = self._get_connection()

        # Normalize zip to first 5 digits
        norm_zip = zip_code[:5] if zip_code else ''

        if not norm_zip:
            return (False, 0)

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT ID
                    FROM [HTC300_G010_T010 DFW_ACI_Data]
                    WHERE ZIP_CODE = ?
                      AND Active = 1
                """
                cursor.execute(query, (norm_zip,))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"No ACI data found for ZIP {norm_zip}")
                    return (False, 0)

                aci_id = int(row[0])
                logger.debug(f"Found ACI ID {aci_id} for ZIP {norm_zip}")
                return (True, aci_id)

        except Exception as e:
            logger.error(f"Failed to lookup ACI for ZIP {zip_code}: {e}")
            # Fail gracefully - return not found
            return (False, 0)

    def geocode_address(
        self,
        addr_ln1: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> tuple:
        """
        Geocode an address to get latitude/longitude.

        PLACEHOLDER: Returns empty strings for now.
        Will be implemented with actual geocoding service later.

        Args:
            addr_ln1: Street address
            city: City name
            state: State abbreviation
            zip_code: ZIP code

        Returns:
            Tuple of (latitude: str, longitude: str)
            Currently returns ("", "") as placeholder.
        """
        # TODO: Implement actual geocoding (Google Maps, Nominatim, etc.)
        logger.debug(f"Geocoding placeholder called for: {addr_ln1}, {city}, {state} {zip_code}")
        return ("", "")

    def create_address(
        self,
        company_name: str,
        addr_ln1: str,
        city: str,
        state: str,
        zip_code: str,
        country: str = "USA",
        addr_ln2: str = "",
    ) -> float:
        """
        Create a new address record in the HTC database.

        See docs/htc-integration/address-creation.md for full field mapping.

        Args:
            company_name: Company/location name (used for both FavCompany and FavLocnName)
            addr_ln1: Address line 1
            city: City name
            state: State abbreviation
            zip_code: ZIP code
            country: Country name (default: "USA")
            addr_ln2: Address line 2 (optional)

        Returns:
            The new FavID (address ID) as float

        Raises:
            OutputExecutionError: If address creation fails
        """
        logger.info(f"Creating new address: {addr_ln1}, {city}, {state} {zip_code}")

        # Generate keycheck and keycounts
        keycheck = self.generate_keycheck(
            locn_name=company_name,
            addr_ln1=addr_ln1,
            addr_ln2=addr_ln2,
            city=city,
            zip_code=zip_code,
            country=country,
        )
        keycounts = self.generate_keycounts(keycheck)

        # Get next FavID
        fav_id = self.get_next_fav_id()

        # Lookup ACI data
        aci_listed, aci_id = self.lookup_aci_by_zip(zip_code)

        # Geocode address (placeholder)
        latitude, longitude = self.geocode_address(addr_ln1, city, state, zip_code)

        # Current timestamp and user
        now = datetime.now()
        added_by = "eto"

        # Default values
        assessorials = "." * 100  # 100 dots

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO [HTC300_G060_T010 Addresses] (
                        FavCoID,
                        FavBrID,
                        FavID,
                        FavKeycheck,
                        FavKeyCounts,
                        FavBranchAddressYN,
                        FavCompany,
                        FavLocnName,
                        FavAddrLn1,
                        FavAddrLn2,
                        FavCity,
                        FavState,
                        FavZip,
                        FavCountry,
                        FavLatitude,
                        FavLongitude,
                        FavACIListed,
                        FavACIID,
                        FavFirstName,
                        FavLastName,
                        FavEMail,
                        FavPhone,
                        FavExt,
                        FavAssessorials,
                        FavCarrierYN,
                        FavLocalYN,
                        FavInternational,
                        FavWaitTimeDefault,
                        FavActive,
                        FavDateAdded,
                        FavAddedBy,
                        FavDateModified,
                        FavChgdby,
                        FavCarrierGroundYN
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                """

                params = (
                    self.CO_ID,              # FavCoID = 1
                    self.BR_ID,              # FavBrID = 1
                    fav_id,                  # FavID
                    keycheck,                # FavKeycheck
                    keycounts,               # FavKeyCounts
                    False,                   # FavBranchAddressYN
                    company_name,            # FavCompany
                    company_name,            # FavLocnName (same as company)
                    addr_ln1,                # FavAddrLn1
                    addr_ln2,                # FavAddrLn2
                    city,                    # FavCity
                    state,                   # FavState
                    zip_code,                # FavZip
                    country,                 # FavCountry
                    latitude,                # FavLatitude
                    longitude,               # FavLongitude
                    aci_listed,              # FavACIListed
                    aci_id,                  # FavACIID
                    "",                      # FavFirstName
                    "",                      # FavLastName
                    "",                      # FavEMail
                    "",                      # FavPhone
                    "",                      # FavExt
                    assessorials,            # FavAssessorials
                    False,                   # FavCarrierYN
                    False,                   # FavLocalYN
                    False,                   # FavInternational
                    0,                       # FavWaitTimeDefault
                    True,                    # FavActive
                    now,                     # FavDateAdded
                    added_by,                # FavAddedBy
                    now,                     # FavDateModified
                    added_by,                # FavChgdby
                    False,                   # FavCarrierGroundYN
                )

                cursor.execute(query, params)

            # Add history record for the new address
            self._add_address_history(
                fav_id=fav_id,
                company_name=company_name,
                addr_ln1=addr_ln1,
                addr_ln2=addr_ln2,
                city=city,
                state=state,
                zip_code=zip_code,
                action="added",
            )

            logger.info(f"Created new address with FavID: {fav_id}")
            return fav_id

        except Exception as e:
            logger.error(f"Failed to create address: {e}")
            raise OutputExecutionError(f"Failed to create address: {e}") from e

    def _add_address_history(
        self,
        fav_id: float,
        company_name: str,
        addr_ln1: str,
        addr_ln2: str,
        city: str,
        state: str,
        zip_code: str,
        action: str = "added",
    ) -> None:
        """
        Add a record to the Addresses Update History table.

        Args:
            fav_id: The FavID of the address
            company_name: Company/location name
            addr_ln1: Address line 1
            addr_ln2: Address line 2
            city: City name
            state: State abbreviation
            zip_code: ZIP code
            action: Description of action (e.g., "added", "updated")
        """
        connection = self._get_connection()

        # Build the change description (matches existing records format)
        # Format: "Address ID {FavID}, '{CompanyName} / {LocnName}' added to Pickup/Delivery Address List"
        change_desc = f"Address ID {int(fav_id)}, '{company_name} / {company_name}' {action} to Pickup/Delivery Address List"

        now = datetime.now()
        user_id = "eto"

        try:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO [HTC300_G060_T030 Addresses Update History] (
                        Addr_UpdtDate,
                        Addr_UpdtLID,
                        Addr_UpdtCoID,
                        Addr_UpdtBrID,
                        Addr_ID,
                        Addr_Chgs
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    now,
                    user_id,
                    self.CO_ID,
                    self.BR_ID,
                    fav_id,
                    change_desc,
                ))

            logger.debug(f"Added address history record for FavID: {fav_id}")

        except Exception as e:
            # Log but don't fail the address creation if history fails
            logger.warning(f"Failed to add address history for FavID {fav_id}: {e}")
