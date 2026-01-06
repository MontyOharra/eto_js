"""
HTC Attachment Utilities
Handles copying PDF files to HTC attachment storage and creating attachment records
"""
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from shared.database.access_connection import AccessConnection

logger = logging.getLogger(__name__)


@dataclass
class PdfSource:
    """Information about a source PDF file for attachment processing"""
    pdf_file_id: int
    original_filename: str
    file_path: str  # Relative path in ETO storage (e.g., "2024/12/19/abc123.pdf")


@dataclass
class AttachmentResult:
    """Result of processing a single attachment"""
    success: bool
    source_path: str
    dest_path: str
    file_size_kb: float
    error_message: str | None = None


class AttachmentManager:
    """
    Manages HTC attachment storage and database records.

    Handles:
    - Building attachment directory paths following HTC convention
    - Copying PDF files from ETO storage to HTC attachment storage
    - Creating records in HTC300_G040_T014A Open Order Attachments table
    """

    # Default company and branch IDs (matching order_utils.py)
    CO_ID = 1
    BR_ID = 1

    def __init__(
        self,
        htc_apps_dir: str,
        eto_storage_path: str,
        connection: AccessConnection,
        co_id: int = 1,
        br_id: int = 1,
    ):
        """
        Initialize the attachment manager.

        Args:
            htc_apps_dir: Root HTC apps directory (e.g., "C:/HTC_Apps")
            eto_storage_path: Root ETO PDF storage path (e.g., "C:/ETO_Storage")
            connection: AccessConnection to HTC Access database
            co_id: Company ID (default 1)
            br_id: Branch ID (default 1)
        """
        self.htc_apps_dir = Path(htc_apps_dir)
        self.eto_storage_path = Path(eto_storage_path)
        self.connection = connection
        self.CO_ID = co_id
        self.BR_ID = br_id

    def build_attachment_dir(self, customer_id: int, order_number: float) -> Path:
        """
        Build the HTC attachment directory path.

        Format: {htc_apps_dir}/HTCAttach-{CoID}-{BrID}/Co{CoID}Br{BrID}/Cust{CustID}/Order_{OrderNo}/

        Root folder uses 2-digit padding for both CoID and BrID.
        Subdirectory uses 3-digit CoID and 5-digit BrID.

        Example: C:/HTC_Apps/HTCAttach-01-01/Co001Br00001/Cust00195/Order_0106299/

        Args:
            customer_id: Customer ID
            order_number: HTC order number

        Returns:
            Path object for the attachment directory
        """
        # Format IDs with padding
        cust_id_padded = f"{customer_id:05d}"
        order_no_padded = f"{int(order_number):07d}"

        # Build path components
        # Root folder: HTCAttach-XX-XX (2-digit padding for both)
        attach_folder = f"HTCAttach-{self.CO_ID:02d}-{self.BR_ID:02d}"
        # Subdirectory: CoXXXBrXXXXX (3-digit CoID, 5-digit BrID)
        co_br_folder = f"Co{self.CO_ID:03d}Br{self.BR_ID:05d}"
        cust_folder = f"Cust{cust_id_padded}"
        order_folder = f"Order_{order_no_padded}"

        return self.htc_apps_dir / attach_folder / co_br_folder / cust_folder / order_folder

    def build_attachment_filename(
        self,
        original_filename: str,
        hawb: str,
        timestamp: datetime | None = None,
    ) -> str:
        """
        Build the attachment filename with HAWB and timestamp.

        Format: {original_name}.{hawb}.{MM-DD-YYYY}_{HH-MM-SS}.pdf

        Example: airway_bill.00455831.12-19-2024_14-30-22.pdf

        Args:
            original_filename: Original PDF filename (with or without .pdf extension)
            hawb: HAWB identifier
            timestamp: Timestamp for filename (defaults to now)

        Returns:
            Formatted filename string
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Remove .pdf extension if present
        base_name = original_filename
        if base_name.lower().endswith('.pdf'):
            base_name = base_name[:-4]

        # Format timestamp as MM-DD-YYYY_HH-MM-SS
        time_str = timestamp.strftime("%m-%d-%Y_%H-%M-%S")

        return f"{base_name}.{hawb}.{time_str}.pdf"

    def copy_attachment(self, source_path: Path, dest_path: Path) -> float:
        """
        Copy a PDF file from source to destination.

        Creates destination directory if it doesn't exist.

        Args:
            source_path: Full path to source PDF file
            dest_path: Full path to destination PDF file

        Returns:
            File size in KB

        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If copy operation fails
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source PDF not found: {source_path}")

        # Create destination directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(source_path, dest_path)

        # Get file size in KB
        file_size_kb = dest_path.stat().st_size / 1024

        logger.debug(f"Copied attachment: {source_path} -> {dest_path} ({file_size_kb:.1f} KB)")

        return file_size_kb

    def create_attachment_record(
        self,
        order_number: float,
        customer_id: int,
        file_path: str,
        file_size_kb: float,
    ) -> None:
        """
        Create a record in the HTC attachments table.

        Table: HTC300_G040_T014A Open Order Attachments

        Args:
            order_number: HTC order number
            customer_id: Customer ID
            file_path: Full path to the attachment file
            file_size_kb: File size in KB
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T014A Open Order Attachments]
                    ([Att_CoID], [Att_BrID], [Att_OrderNo], [Att_CustID], [Att_Path], [ATT_Size])
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.CO_ID,
                    self.BR_ID,
                    order_number,
                    customer_id,
                    file_path,
                    file_size_kb,
                ))

            logger.debug(f"Created attachment record for order {order_number}: {file_path}")

        except Exception as e:
            logger.error(f"Failed to create attachment record: {e}")
            raise

    def process_attachments_for_order(
        self,
        order_number: float,
        customer_id: int,
        hawb: str,
        pdf_sources: list[PdfSource],
    ) -> list[AttachmentResult]:
        """
        Process all PDF attachments for an order.

        For each unique PDF:
        1. Build destination path
        2. Copy file from ETO storage to HTC attachment storage
        3. Create record in HTC attachments table

        Args:
            order_number: HTC order number
            customer_id: Customer ID
            hawb: HAWB identifier (used in filename)
            pdf_sources: List of source PDF files to attach

        Returns:
            List of AttachmentResult for each processed attachment
        """
        results: list[AttachmentResult] = []

        # Track processed PDF file IDs to avoid duplicates
        processed_ids: set = set()

        # Build destination directory (same for all attachments)
        dest_dir = self.build_attachment_dir(customer_id, order_number)

        for pdf_source in pdf_sources:
            # Skip duplicates
            if pdf_source.pdf_file_id in processed_ids:
                logger.debug(f"Skipping duplicate PDF {pdf_source.pdf_file_id}")
                continue

            processed_ids.add(pdf_source.pdf_file_id)

            # Build paths
            source_path = self.eto_storage_path / pdf_source.file_path
            dest_filename = self.build_attachment_filename(
                pdf_source.original_filename,
                hawb,
            )
            dest_path = dest_dir / dest_filename

            try:
                # Copy file
                file_size_kb = self.copy_attachment(source_path, dest_path)

                # Create database record
                self.create_attachment_record(
                    order_number=order_number,
                    customer_id=customer_id,
                    file_path=str(dest_path),
                    file_size_kb=file_size_kb,
                )

                results.append(AttachmentResult(
                    success=True,
                    source_path=str(source_path),
                    dest_path=str(dest_path),
                    file_size_kb=file_size_kb,
                ))

                logger.info(f"Processed attachment for order {order_number}: {dest_filename}")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to process attachment {pdf_source.original_filename}: {error_msg}")

                results.append(AttachmentResult(
                    success=False,
                    source_path=str(source_path),
                    dest_path=str(dest_path),
                    file_size_kb=0,
                    error_message=error_msg,
                ))

        successful = sum(1 for r in results if r.success)
        logger.info(f"Processed {successful}/{len(results)} attachments for order {order_number}")

        return results
