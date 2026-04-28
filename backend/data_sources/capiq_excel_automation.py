"""
Capital IQ Excel COM Automation — drives Excel + CIQ plugin via pywin32.

Flow:
  1. Launch Excel (or connect to running instance)
  2. Create a new workbook
  3. Write CIQ formulas into cells
  4. Wait for the CIQ plugin to resolve formulas (polling)
  5. Read resolved numeric values
  6. Close workbook (without saving)

Requirements:
  - Windows with Excel installed
  - S&P Capital IQ Excel plugin installed and logged in
  - pywin32 (win32com) Python package
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Delay import so the module can be imported on non-Windows for testing
_com_available = False
try:
    import win32com.client
    import pythoncom
    _com_available = True
except ImportError:
    pass


@dataclass
class CIQFetchResult:
    """Result of a single CIQ formula resolution."""
    variable: str
    mnemonic: str
    period: str
    fiscal_year_offset: int
    value: float | None
    raw_value: object = None
    error: str | None = None


@dataclass
class ExcelCOMDriver:
    """Drives Excel via COM to resolve CIQ formulas."""

    poll_interval_sec: float = 2.0
    max_wait_sec: float = 90.0
    visible: bool = False  # Set True for debugging (shows Excel window)

    _excel: object = field(default=None, init=False, repr=False)
    _workbook: object = field(default=None, init=False, repr=False)

    def fetch_via_template(self, template_path: str, ticker: str, save_path: str) -> str:
        """
        Open the CIQ template, set ticker in B1, wait for all formulas to resolve,
        save the resolved file, and close Excel.

        This is MUCH faster than cell-by-cell because CIQ plugin resolves all
        formulas in parallel when the file opens.

        Args:
            template_path: Path to CIQ_Fetch_Template.xlsx
            ticker: e.g. "NVDA"
            save_path: Where to save the resolved file

        Returns:
            save_path (for chaining)
        """
        if not _com_available:
            raise RuntimeError("pywin32 is not installed. Install with: pip install pywin32")

        try:
            self._open_excel()
            # Open the template file (not create a new workbook)
            self._workbook = self._excel.Workbooks.Open(template_path)
            ws = self._workbook.Sheets("CIQ_Data")

            # Set ticker in B1
            ws.Range("B1").Value = ticker
            logger.info(f"Set ticker to {ticker} in template")

            # Force recalculation
            self._workbook.Application.CalculateFull()

            # Wait for all CIQ formulas to resolve
            self._wait_for_template_resolution(ws)

            # Save to the output path
            # Use xlOpenXMLWorkbook (51) format for .xlsx
            self._workbook.SaveAs(save_path, FileFormat=51)
            logger.info(f"Saved resolved template to {save_path}")

            return save_path
        except Exception as e:
            logger.error(f"CIQ template fetch failed: {e}")
            raise
        finally:
            self._cleanup()

    def _wait_for_template_resolution(self, ws) -> None:
        """Poll the template worksheet until no cells show #GETTING_DATA."""
        start = time.time()
        # Check column D (resolved values) for unresolved markers
        max_row = ws.UsedRange.Rows.Count

        while time.time() - start < self.max_wait_sec:
            unresolved = 0
            # Read column C (formulas) in batch
            rng = ws.Range(ws.Cells(5, 3), ws.Cells(max_row, 3))
            values = rng.Value
            if values:
                for row_tuple in values:
                    cell_val = row_tuple[0] if row_tuple else None
                    text = str(cell_val) if cell_val is not None else ""
                    if "GETTING" in text.upper() or "LOADING" in text.upper():
                        unresolved += 1

            if unresolved == 0:
                elapsed = time.time() - start
                logger.info(f"All template formulas resolved in {elapsed:.1f}s")
                return

            logger.debug(f"Waiting... {unresolved} cells still resolving")
            time.sleep(self.poll_interval_sec)

        elapsed = time.time() - start
        logger.warning(f"Template timeout after {elapsed:.1f}s — some formulas may not have resolved")

    def fetch(self, formulas: list[dict]) -> list[CIQFetchResult]:
        """
        Write CIQ formulas to Excel, wait for resolution, read values.

        Args:
            formulas: List of formula dicts from capiq_formula_map.generate_ciq_formulas()

        Returns:
            List of CIQFetchResult with resolved values.
        """
        if not _com_available:
            raise RuntimeError(
                "pywin32 is not installed. Install with: pip install pywin32"
            )

        results = []
        try:
            self._open_excel()
            self._write_formulas(formulas)
            self._wait_for_resolution(len(formulas))
            results = self._read_values(formulas)
        except Exception as e:
            logger.error(f"CIQ Excel automation failed: {e}")
            raise
        finally:
            self._cleanup()

        return results

    def _open_excel(self) -> None:
        """Launch or connect to Excel."""
        pythoncom.CoInitialize()
        try:
            # Try to connect to an existing Excel instance
            self._excel = win32com.client.GetActiveObject("Excel.Application")
            logger.info("Connected to existing Excel instance")
        except Exception:
            # Launch a new instance
            self._excel = win32com.client.Dispatch("Excel.Application")
            logger.info("Launched new Excel instance")

        self._excel.Visible = self.visible
        self._excel.DisplayAlerts = False
        self._workbook = self._excel.Workbooks.Add()

    def _write_formulas(self, formulas: list[dict]) -> None:
        """Write CIQ formulas into cells using batch Range assignment."""
        ws = self._workbook.Sheets(1)
        ws.Name = "CIQ_Fetch"

        n = len(formulas)
        if n == 0:
            return

        # Build 2D arrays for batch write (COM expects list-of-lists for Range.Value)
        labels = [[f"{f['variable']}|{f['period']}"] for f in formulas]

        # Batch write labels (column A) in one COM call
        rng_a = ws.Range(ws.Cells(1, 1), ws.Cells(n, 1))
        rng_a.Value = labels

        # Formulas must be written individually (Range.Formula with array
        # doesn't reliably set per-cell formulas in COM), but we can still
        # minimize overhead by avoiding repeated Cells() lookups
        for i, f in enumerate(formulas):
            ws.Cells(i + 1, 2).Formula = f["formula"]

        logger.info(f"Wrote {n} CIQ formulas to worksheet")

    def _wait_for_resolution(self, num_formulas: int) -> None:
        """Poll until all CIQ formulas have resolved (no more #GETTING_DATA)."""
        ws = self._workbook.Sheets(1)
        start = time.time()

        while time.time() - start < self.max_wait_sec:
            # Batch-read entire column B as array (1 COM call per poll cycle)
            rng = ws.Range(ws.Cells(1, 2), ws.Cells(num_formulas, 2))
            texts = rng.Text  # may not work as array; fall back to Value
            values = rng.Value  # 2D tuple: ((val1,), (val2,), ...)

            unresolved = 0
            if values:
                for row_tuple in values:
                    cell_val = row_tuple[0] if row_tuple else None
                    text = str(cell_val) if cell_val is not None else ""
                    if isinstance(text, str) and (
                        "GETTING" in text.upper()
                        or "LOADING" in text.upper()
                        or "CALCULATING" in text.upper()
                    ):
                        unresolved += 1

            if unresolved == 0:
                elapsed = time.time() - start
                logger.info(f"All formulas resolved in {elapsed:.1f}s")
                return

            logger.debug(f"Waiting... {unresolved}/{num_formulas} unresolved")
            time.sleep(self.poll_interval_sec)

        elapsed = time.time() - start
        logger.warning(f"Timeout after {elapsed:.1f}s — some formulas may not have resolved")

    def _read_values(self, formulas: list[dict]) -> list[CIQFetchResult]:
        """Read resolved values from the worksheet."""
        ws = self._workbook.Sheets(1)
        results = []

        for i, f in enumerate(formulas):
            row = i + 1
            raw_val = ws.Cells(row, 2).Value
            text = ws.Cells(row, 2).Text or ""

            result = CIQFetchResult(
                variable=f["variable"],
                mnemonic=f["mnemonic"],
                period=f["period"],
                fiscal_year_offset=f["fiscal_year_offset"],
                value=None,
                raw_value=raw_val,
            )

            # Parse the resolved value
            if isinstance(raw_val, (int, float)):
                result.value = float(raw_val)
            elif raw_val is None or text.strip() == "":
                result.error = "empty"
            elif "N/A" in text.upper() or "NA" in text.upper():
                result.error = "N/A"
            elif "ERROR" in text.upper() or "#" in text:
                result.error = f"excel_error: {text}"
            else:
                # Try to parse as float (some values come as strings)
                try:
                    result.value = float(str(raw_val).replace(",", ""))
                except (ValueError, TypeError):
                    result.error = f"unparseable: {raw_val!r}"

            results.append(result)

        resolved = sum(1 for r in results if r.value is not None)
        errors = sum(1 for r in results if r.error)
        logger.info(f"Read {len(results)} cells: {resolved} resolved, {errors} errors")

        return results

    def _cleanup(self) -> None:
        """Close workbook and optionally quit Excel."""
        try:
            if self._workbook:
                self._workbook.Close(SaveChanges=False)
                self._workbook = None
        except Exception as e:
            logger.warning(f"Error closing workbook: {e}")

        # Don't quit Excel — the user may have it open for other work
        # If we launched it, we could quit, but it's safer to leave it.
        self._excel = None

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
