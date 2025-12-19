"""
Authentication Service

Provides user authentication via HTC Staff database (HTC000_Data_Staff.accdb).
Supports two authentication methods:
1. Auto-login via WhosLoggedIn table (checks if user is logged into HTC system)
2. Manual login via Staff table credentials

Uses the same pattern as HtcIntegrationService for Access database access.
"""

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from shared.logging import get_logger

if TYPE_CHECKING:
    from shared.database.data_database_manager import DataDatabaseManager

logger = get_logger(__name__)


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user."""
    staff_emp_id: int
    username: str  # Staff_Login - used for audit trail (Orders_UpdtLID)
    display_name: str
    first_name: str
    last_name: str


class AuthService:
    """
    Authentication service for user login.

    Queries the HTC000_Data_Staff Access database for:
    - Auto-login: Check WhosLoggedIn table for active sessions by PC name/login ID
    - Manual login: Validate username/password against Staff table
    """

    # Database name (auto-discovered from HTC_000_DATA_STAFF_CONNECTION_STRING env var)
    DATABASE_NAME = "htc_000_data_staff"

    def __init__(
        self,
        data_database_manager: 'DataDatabaseManager',
    ) -> None:
        """
        Initialize the auth service.

        Args:
            data_database_manager: DataDatabaseManager for Access database access
        """
        logger.debug("Initializing AuthService...")
        self._data_database_manager = data_database_manager

    def _get_connection(self) -> Any:
        """Get database connection for staff database."""
        return self._data_database_manager.get_connection(self.DATABASE_NAME)

    def attempt_auto_login(self, pc_name: str, pc_lid: str) -> Optional[AuthenticatedUser]:
        """
        Attempt automatic login by checking WhosLoggedIn table.

        Looks for an active session matching the given computer name and Windows login ID.
        If found, retrieves the staff details for that user.

        Args:
            pc_name: Computer/hostname name (from os.hostname())
            pc_lid: Windows login ID / username (from os.userInfo().username)

        Returns:
            AuthenticatedUser if a matching session found, None otherwise
        """
        logger.info(f"Attempting auto-login for PCName='{pc_name}', PCLid='{pc_lid}'")

        try:
            # Step 1: Query WhosLoggedIn for matching session
            staff_id = self._get_staff_id_from_session(pc_name, pc_lid)

            if staff_id is None:
                return None

            # Step 2: Get staff details (separate cursor operation)
            return self.get_staff_by_id(staff_id)

        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return None

    def _get_staff_id_from_session(self, pc_name: str, pc_lid: str) -> Optional[int]:
        """
        Query WhosLoggedIn table for a matching session.

        Args:
            pc_name: Computer/hostname name
            pc_lid: Windows login ID / username

        Returns:
            Staff ID if found, None otherwise
        """
        connection = self._get_connection()

        with connection.cursor() as cursor:
            query = """
                SELECT [WLI_StaffID]
                FROM [HTC000 WhosLoggedIn]
                WHERE [PCName] = ? AND [PCLid] = ?
            """
            cursor.execute(query, (pc_name, pc_lid))
            row = cursor.fetchone()

            if row is None:
                logger.info(f"No active session found for PCName='{pc_name}', PCLid='{pc_lid}'")
                return None

            staff_id = int(row[0]) if row[0] is not None else None

            if staff_id is None or staff_id == 0:
                logger.info(f"Session found but no valid staff ID (StaffID={staff_id})")
                return None

            logger.info(f"Found active session for staff ID {staff_id}")
            return staff_id

    def validate_credentials(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        """
        Validate username and password against Staff table.

        Args:
            username: Staff login name
            password: Staff password (plain text)

        Returns:
            AuthenticatedUser if credentials valid, None otherwise
        """
        logger.info(f"Validating credentials for username='{username}'")

        try:
            connection = self._get_connection()

            with connection.cursor() as cursor:
                # Query Staff table for matching credentials
                query = """
                    SELECT [Staff_EmpID], [Staff_Login], [Staff_FirstName], [Staff_LastName]
                    FROM [HTC000_G090_T010 Staff]
                    WHERE [Staff_Login] = ?
                      AND [Staff_Password] = ?
                      AND [Staff_Active] = True
                """
                cursor.execute(query, (username, password))
                row = cursor.fetchone()

                if row is None:
                    logger.info(f"Invalid credentials for username='{username}'")
                    return None

                staff_emp_id = int(row[0])
                staff_login = str(row[1]).strip() if row[1] else username
                first_name = str(row[2]).strip() if row[2] else ""
                last_name = str(row[3]).strip() if row[3] else ""
                display_name = f"{first_name} {last_name}".strip()

                logger.info(f"Credentials valid for username='{username}' (EmpID={staff_emp_id})")

                return AuthenticatedUser(
                    staff_emp_id=staff_emp_id,
                    username=staff_login,
                    display_name=display_name,
                    first_name=first_name,
                    last_name=last_name,
                )

        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return None

    def get_staff_by_id(self, emp_id: int) -> Optional[AuthenticatedUser]:
        """
        Get staff details by employee ID.

        Args:
            emp_id: Staff employee ID

        Returns:
            AuthenticatedUser if found, None otherwise
        """
        logger.debug(f"Looking up staff by ID {emp_id}")

        try:
            connection = self._get_connection()

            with connection.cursor() as cursor:
                query = """
                    SELECT [Staff_EmpID], [Staff_Login], [Staff_FirstName], [Staff_LastName]
                    FROM [HTC000_G090_T010 Staff]
                    WHERE [Staff_EmpID] = ?
                      AND [Staff_Active] = True
                """
                cursor.execute(query, (emp_id,))
                row = cursor.fetchone()

                if row is None:
                    logger.warning(f"Staff ID {emp_id} not found or inactive")
                    return None

                staff_emp_id = int(row[0])
                staff_login = str(row[1]).strip() if row[1] else ""
                first_name = str(row[2]).strip() if row[2] else ""
                last_name = str(row[3]).strip() if row[3] else ""
                display_name = f"{first_name} {last_name}".strip()

                return AuthenticatedUser(
                    staff_emp_id=staff_emp_id,
                    username=staff_login,
                    display_name=display_name,
                    first_name=first_name,
                    last_name=last_name,
                )

        except Exception as e:
            logger.error(f"Staff lookup failed for ID {emp_id}: {e}")
            return None

    def is_available(self) -> bool:
        """
        Check if the auth service is available (database configured and accessible).

        Returns:
            True if staff database is accessible, False otherwise
        """
        try:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Auth service not available: {e}")
            return False
