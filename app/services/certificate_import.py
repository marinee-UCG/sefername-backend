from app.services.sea_service_import import ImportFormatError, read_sheet, text, to_date

REQUIRED_HEADERS = {"Sertifika Durumu", "Sertifika Tipi", "Belge No", "Veriliş Tarihi", "Geçerlilik Tarihi"}

ACCEPTED_STATUSES = {"Aktif"}

# Turkish characters folded to plain capitals, spaces squeezed: the file's spelling varies a little
_FOLD = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "CGIIOSUCGIIOSU")


def _key(name: str) -> str:
    return " ".join(name.translate(_FOLD).upper().split())


# e-Devlet's certificate types -> the names the app lists (frontend utils/certificates.js).
# A type not here keeps its Turkish name; the user can pick the right one before saving.
CERTIFICATE_NAMES = {
    _key(tr): en
    for tr, en in {
        "TEMEL İLKYARDIM EĞİTİMİ BELGESİ": "Elementary First Aid",
        "DENİZDE KİŞİSEL CAN KURTARMA TEKNİKLERİ EĞİTİM BELGESİ": "Personal Survival Techniques",
        "YANGIN ÖNLEME VE YANGINLA MÜCADELE EĞİTİMİ BELGESİ": "Fire Prevention and Fire Fighting",
        "KİŞİSEL EMNİYET VE SOSYAL SORUMLULUK EĞİTİMİ BELGESİ": "Personal Safety and Social Responsibilities",
        "GÜVENLİK FARKINDALIK BELGESİ": "Security Awareness",
        "GÜVENLİKLE İLGİLİ TANITIM BELGESİ": "Security-Related Familiarization",
        "BELİRLENMİŞ GÜVENLİK GÖREVLERİ EĞİTİMİ BELGESİ": "Designated Security Duties",
        "GEMİ GÜVENLİK ZABİTİ BELGESİ": "Ship Security Officer",
        "İLERİ YANGINLA MÜCADELE BELGESİ": "Advanced Fire Fighting",
        "CANKURTARMA ARAÇLARINI KULLANMA YETERLİĞİ EĞİTİMİ BELGESİ": "Survival Craft and Rescue Boats",
        "HIZLI CANKURTARMA BOTLARI EĞİTİMİ BELGESİ": "Fast Rescue Boats",
        "TIBBİ İLKYARDIM EĞİTİMİ BELGESİ": "Medical First Aid",
        "TIBBİ BAKIM EĞİTİMİ BELGESİ": "Medical Care",
        "YÜKSEK VOLTAJ EĞİTİMİ(1000 V VE ÜZERİ)": "High Voltage",
        "PETROL VE KİMYASAL MADDE TANKERLERİNDE YÜK İŞLEMLERİ İÇİN TEMEL EĞİTİM BELGESİ": "Basic Oil and Chemical Tanker",
        "PETROL TANKERLERİNDE YÜK İŞLEMLERİ İÇİN İLERİ EĞİTİM BELGESİ": "Advanced Oil Tanker",
        "KİMYASAL MADDE TANKERLERİNDE YÜK İŞLEMLERİ İÇİN İLERİ EĞİTİM BELGESİ": "Advanced Chemical Tanker",
        "SIVILAŞTIRILMIŞ GAZ TANKERLERİNDE YÜK İŞLEMLERİ İÇİN TEMEL EĞİTİM BELGESİ": "Basic Liquefied Gas Tanker",
        "SIVILAŞTIRILMIŞ GAZ TANKERLERİNDE YÜK İŞLEMLERİ İÇİN İLERİ EĞİTİM BELGESİ": "Advanced Liquefied Gas Tanker",
    }.items()
}

# The ministry's record is the source; the user can change it (a training centre, say) before saving
ISSUING_INSTITUTION = "T.C. Ulaştırma ve Altyapı Bakanlığı"


def parse_certificates(content: bytes) -> list[dict]:
    columns, rows = read_sheet(content, REQUIRED_HEADERS, "This is not the certificate file from e-Devlet.")

    certificates = []
    for row in rows:
        status = text(row[columns["Sertifika Durumu"]])
        if status not in ACCEPTED_STATUSES:
            continue
        source_name = text(row[columns["Sertifika Tipi"]])
        number = text(row[columns["Belge No"]])
        issue_date = to_date(row[columns["Veriliş Tarihi"]])
        if source_name is None or number is None or issue_date is None:
            raise ImportFormatError("A certificate in this file has no type, number or issue date.")
        certificates.append({
            "cert_name": CERTIFICATE_NAMES.get(_key(source_name), source_name),
            "source_name": source_name,
            "cert_number": number,
            "issue_date": issue_date,
            # Empty for a certificate without an end date
            "expiry_date": to_date(row[columns["Geçerlilik Tarihi"]]),
            "issuing_inst": ISSUING_INSTITUTION,
        })
    return certificates
