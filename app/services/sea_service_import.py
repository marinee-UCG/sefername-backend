from datetime import date, datetime
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class ImportFormatError(Exception):
    pass

REQUIRED_HEADERS={"Hizmet Durumu","Gemi Adı","Gemi/IMO No","Bayrak","Başlama Tarihi","Bitiş Tarihi","Hizmet Türü"}

ACCEPTED_STATUSES={"Yüklendi","Doğrulandı"}

# A file's rows are read only this far: a real record has tens of rows, not thousands
MAX_ROWS = 2000


def read_sheet(content: bytes, required: set[str], wrong_file: str) -> tuple[dict, list[tuple]]:
    """The first sheet of an e-Devlet xlsx: ({header: column index}, data rows).
    Shared by the sea service and certificate imports."""
    # Not an Excel file at all (a photo, a PDF, a broken download)
    try:
        wb=load_workbook(BytesIO(content),read_only=True,data_only=True)
    except (BadZipFile,InvalidFileException,KeyError,ValueError):
        raise ImportFormatError("This file could not be read as an Excel file.")

    sheet=wb.active
    # e-Devlet writes a wrong size into the file ("A1:C1"); without this only the header row is read
    sheet.reset_dimensions()
    rows=sheet.iter_rows(values_only=True)
    # An empty sheet has no header row
    header=next(rows,None)
    if header is None:
        raise ImportFormatError("This file is empty.")

    columns={}
    for i,name in enumerate(header):
        if isinstance(name,str):
            columns[name.strip()]=i

    missing=required-set(columns)
    if missing:
        raise ImportFormatError(wrong_file)

    data=[]
    for row in rows:
        if len(data)>=MAX_ROWS:
            raise ImportFormatError("This file has too many rows.")
        # Short rows (trailing empty cells) are padded, so every column can be read
        data.append(tuple(row)+(None,)*(len(header)-len(row)))
    return columns,data


def to_date(value) -> date | None:
    """A date cell: a real date in e-Devlet's files, "26.07.2026" text in some exports, or empty."""
    if value is None or value=="":
        return None
    if isinstance(value,datetime):
        return value.date()
    if isinstance(value,date):
        return value
    try:
        return datetime.strptime(str(value).strip(),"%d.%m.%Y").date()
    except ValueError:
        raise ImportFormatError("A date in this file could not be read.")


def text(value) -> str | None:
    # " MV NAME " -> "MV NAME"; numbers (an IMO typed as a number) become text; empty -> None
    if value is None:
        return None
    value=str(value).strip()
    return value or None


def parse_sea_service(content:bytes) ->list[dict]:
    columns,rows=read_sheet(content,REQUIRED_HEADERS,"This is not the sea service file from e-Devlet.")

    services=[]
    for row in rows:
        status=text(row[columns["Hizmet Durumu"]])
        if status not in ACCEPTED_STATUSES:
            continue
        start_date=to_date(row[columns["Başlama Tarihi"]])
        vessel_name=text(row[columns["Gemi Adı"]])
        if start_date is None or vessel_name is None:
            raise ImportFormatError("A service in this file has no vessel or no start date.")
        services.append({
            "vessel_name":vessel_name,
            "imo":text(row[columns["Gemi/IMO No"]]),
            "flag":text(row[columns["Bayrak"]]),
            "service_type":text(row[columns["Hizmet Türü"]]),
            "start_date":start_date,
            # Empty while the service is still going on (on board now)
            "end_date":to_date(row[columns["Bitiş Tarihi"]]),
        })
    return services
