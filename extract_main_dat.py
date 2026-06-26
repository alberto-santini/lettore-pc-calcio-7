#!/usr/bin/env python3
"""Extract the current PC Calcio 7 player table to a compact CSV."""

from __future__ import annotations

import argparse
import csv
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


DEFAULT_INPUT = Path("SAVE/PROMANAG/036-0/main.dat")
DEFAULT_OUTPUT = Path("editor/main_dat_extract/current_players_simple.csv")
DEFAULT_STATIC_DB = Path("DBDAT/jug99036.fdi")
DEFAULT_TEAM_DB = Path("DBDAT/eq99036.fdi")
DEFAULT_SEASON_YEAR = 1999
SAVE_CURRENT_DATE_OFFSETS = (0x32, 0x3A)
DISPLAY_MONEY_MULTIPLIER = 10
MISSING_BIRTHDATE_HASH_SALT = "pc-calcio-7-missing-birthdate-v1"

ROLE_BY_DEFINITION = {
    0: "POR",
    1: "DIF",
    2: "MED",
    3: "ATT",
}

TEXT_BYTE_MAP = {
    0x01: "'",
    0x41: " ",
    0x43: '"',
    0x46: "'",
    0x47: "&",
    0x48: ")",
    0x49: "(",
    0x4B: " ",
    0x4C: "-",
    0x4D: ",",
    0x4F: ".",
    0x50: "1",
    0x51: "0",
    0x52: "3",
    0x53: "2",
    0x54: "5",
    0x55: "4",
    0x56: "7",
    0x57: "6",
    0x58: "9",
    0x59: "8",
    0x5D: "",
    0x80: "á",
    0x81: "á",
    0x83: "â",
    0x85: "ä",
    0x86: "ç",
    0x88: "é",
    0x89: "è",
    0x8A: "ë",
    0x8C: "í",
    0x8E: "ï",
    0x8F: "î",
    0x90: "ñ",
    0x92: "ó",
    0x93: "ò",
    0x95: "ô",
    0x97: "ö",
    0x9B: "ú",
    0x9C: "ý",
    0x9D: "ü",
    0xA0: "Á",
    0xA1: "Á",
    0xA3: "Â",
    0xA5: "Ä",
    0xA6: "Ç",
    0xA8: "É",
    0xA9: "È",
    0xAA: "É",
    0xAC: "Í",
    0xAE: "Ï",
    0xB0: "Ñ",
    0xB2: "Ó",
    0xB3: "Ò",
    0xB7: "Ö",
    0xBB: "Ú",
    0xBC: "Ý",
    0xBD: "Ü",
    0xCB: "ª",
    0xD5: "'",
}

TEXT_REPLACEMENTS = (
    ("Conceiçao", "Conceição"),
    ("CONCEIÇAO", "CONCEIÇÃO"),
    ("LOND0NO", "LONDOÑO"),
    ("CARL0S", "CARLOS"),
    ("S nchez", "Sánchez"),
    ("S Nchez", "Sánchez"),
    ("SÁNCHEZ", "SÁNCHEZ"),
    ("Gïnther", "Günther"),
    ("GÏNTHER", "GÜNTHER"),
    ("Jèrome", "Jérôme"),
    ("Stèphane", "Stéphane"),
    ("Hamòet", "Hamlet"),
    ("Siniça", "Siniša"),
    ("SINIÇA", "SINIŠA"),
    ("Franck MATONGOU", "Franck MATINGOU"),
)

NATIONALITY_NAMES = {
    0x01: "Albania",
    0x02: "Germania",
    0x03: "Argentina",
    0x04: "Australia",
    0x05: "Austria",
    0x06: "Azerbaigian",
    0x07: "Bielorussia",
    0x08: "Bolivia",
    0x09: "Bosnia-Erzegovina",
    0x0A: "Brasile",
    0x0B: "Bulgaria",
    0x0C: "Belgio",
    0x0D: "Camerun",
    0x0E: "Cile",
    0x0F: "Cipro",
    0x10: "Colombia",
    0x11: "Croazia",
    0x12: "Danimarca",
    0x13: "Scozia",
    0x14: "Slovacchia",
    0x15: "Slovenia",
    0x16: "Spagna",
    0x17: "Finlandia",
    0x18: "Francia",
    0x19: "Ghana",
    0x1A: "Grecia",
    0x1B: "Paesi Bassi",
    0x1C: "Honduras",
    0x1D: "Ungheria",
    0x1E: "Inghilterra",
    0x1F: "Irlanda",
    0x20: "Irlanda del Nord",
    0x21: "Islanda",
    0x22: "Isole Faroe",
    0x23: "Israele",
    0x24: "Italia",
    0x25: "Lituania",
    0x26: "Lussemburgo",
    0x27: "Macedonia",
    0x28: "Malta",
    0x29: "Marocco",
    0x2A: "Moldavia",
    0x2B: "Nigeria",
    0x2C: "Norvegia",
    0x2D: "Galles",
    0x2E: "Polonia",
    0x2F: "Portogallo",
    0x30: "Repubblica Ceca",
    0x31: "Romania",
    0x32: "Russia",
    0x33: "Serbia",
    0x34: "Sudafrica",
    0x35: "Svezia",
    0x36: "Svizzera",
    0x37: "Turchia",
    0x38: "Ucraina",
    0x39: "Uruguay",
    0x3A: "Jugoslavia",
    0x3B: "Perù",
    0x3C: "Canada",
    0x3D: "Stati Uniti",
    0x3E: "Georgia",
    0x3F: "Costa Rica",
    0x40: "Paraguay",
    0x41: "Giappone",
    0x42: "Algeria",
    0x43: "Trinidad e Tobago",
    0x44: "Senegal",
    0x45: "Suriname",
    0x47: "Capo Verde",
    0x48: "Venezuela",
    0x4B: "Andorra",
    0x4C: "Mozambico",
    0x4D: "Liechtenstein",
    0x4E: "Liberia",
    0x4F: "Panama",
    0x50: "RD Congo",
    0x51: "Tagikistan",
    0x52: "Uzbekistan",
    0x53: "Messico",
    0x54: "Guinea",
    0x55: "Angola",
    0x56: "Zimbabwe",
    0x57: "Sierra Leone",
    0x59: "Ecuador",
    0x5A: "Estonia",
    0x5B: "Guinea-Bissau",
    0x5D: "Egitto",
    0x5E: "Giamaica",
    0x60: "Bermuda",
    0x61: "Nuova Zelanda",
    0x63: "Saint Vincent e Grenadine",
    0x64: "Camerun",
    0x65: "Togo",
    0x66: "Guinea",
    0x68: "Burkina Faso",
    0x69: "Gambia",
    0x6A: "Ucraina",
    0x6B: "Kenya",
    0x6D: "Mali",
    0x6E: "Uganda",
    0x6F: "Repubblica del Congo",
    0x70: "Lettonia",
    0x71: "Costa d'Avorio",
    0x72: "Armenia",
    0x76: "Barbados",
    0x77: "Iran",
    0x79: "Tunisia",
    0x7A: "Gabon",
    0x7C: "Mauritius",
    0x7E: "Réunion",
    0x85: "Benin",
    0x89: "RD Congo",
    0x8C: "Cina",
    0x93: "El Salvador",
    0x9D: "Indonesia",
    0xA0: "Kazakistan",
    0xA8: "Malawi",
    0xAF: "Namibia",
    0xB9: "Santa Lucia",
    0xC1: "Corea del Sud",
    0xC5: "Siria",
}

TEAM_COUNTRY_RANGES = (
    (1, 199, "Spagna"),
    (201, 299, "Italia"),
    (301, 399, "Inghilterra"),
    (401, 499, "Germania"),
    (501, 599, "Francia"),
    (601, 699, "Portogallo"),
    (701, 749, "Jugoslavia"),
    (751, 799, "Russia"),
    (801, 849, "Paesi Bassi"),
    (851, 899, "Belgio"),
    (901, 949, "Croazia"),
    (951, 999, "Svezia"),
    (1001, 1049, "Turchia"),
    (1051, 1099, "Polonia"),
    (1101, 1149, "Svizzera"),
    (1151, 1199, "Austria"),
    (1201, 1249, "Danimarca"),
    (1251, 1299, "Scozia"),
    (1301, 1349, "Grecia"),
    (1351, 1399, "Norvegia"),
    (1401, 1449, "Romania"),
    (1451, 1499, "Repubblica Ceca"),
    (1501, 1549, "Bulgaria"),
    (1551, 1599, "Slovacchia"),
    (1601, 1649, "Slovenia"),
    (1651, 1699, "Cipro"),
    (1701, 1749, "Ungheria"),
    (1751, 1799, "Ucraina"),
    (1801, 1849, "Lussemburgo"),
    (1851, 1899, "Irlanda"),
    (1901, 1949, "Irlanda del Nord"),
    (1951, 1999, "Islanda"),
    (2001, 2049, "Finlandia"),
    (2051, 2099, "Galles"),
    (2101, 2149, "Israele"),
    (2151, 2199, "Malta"),
    (2201, 2249, "Isole Faroe"),
    (2251, 2299, "Lituania"),
    (2401, 2449, "Albania"),
    (2501, 2549, "Georgia"),
    (2551, 2599, "Moldavia"),
    (2601, 2649, "Bolivia"),
    (2651, 2699, "Ecuador"),
    (2701, 2749, "Bielorussia"),
    (2751, 2799, "Perù"),
    (2800, 2849, "Brasile"),
    (2900, 2949, "Uruguay"),
    (2951, 2999, "Venezuela"),
    (3000, 3049, "Cile"),
    (3100, 3149, "Colombia"),
    (3200, 3249, "Paraguay"),
    (3300, 3399, "Inghilterra"),
    (4000, 4024, "Lettonia"),
    (4025, 4049, "Armenia"),
    (4050, 4074, "Macedonia"),
    (4075, 4099, "Bielorussia"),
    (4100, 4124, "Estonia"),
    (4125, 4149, "Azerbaigian"),
    (4301, 4349, "Australia"),
    (4401, 4449, "Corea del Sud"),
    (4501, 4599, "Stati Uniti"),
    (4601, 4649, "Indonesia"),
    (4701, 4749, "Iran"),
    (4801, 4899, "Giappone"),
    (4901, 4949, "Marocco"),
    (5001, 5099, "Messico"),
    (5101, 5149, "Nigeria"),
    (5201, 5249, "Sudafrica"),
    (5301, 5349, "Tunisia"),
    (5401, 5449, "Jugoslavia"),
    (9001, 9099, "Argentina"),
)

TEAM_COUNTRY_OVERRIDES = {
    1805: "Liechtenstein",
    4200: "Andorra",
    4201: "Algeria",
    8800: "Selezione Europa",
    8801: "Selezione America",
    9900: "Speciale",
    9950: "Svincolati",
    9957: "Settore giovanile",
}

TEAM_LEAGUE_BY_ID = {
    **dict.fromkeys(
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 15, 17, 18, 19, 21, 25, 48, 52, 129),
        "Primera División",
    ),
    **dict.fromkeys(
        (201, 202, 204, 205, 207, 208, 212, 213, 215, 216, 219, 220, 225, 227, 228, 236, 238, 246),
        "Serie A",
    ),
    **dict.fromkeys(
        (203, 206, 211, 217, 221, 222, 223, 226, 229, 231, 234, 237, 247, 250, 251, 253, 265, 269, 275, 281),
        "Serie B",
    ),
    **dict.fromkeys(
        (210, 214, 233, 239, 242, 254, 256, 257, 258, 262, 263, 278, 279, 280, 283, 287, 288, 289),
        "Serie C1 A",
    ),
    **dict.fromkeys(
        (224, 230, 232, 235, 243, 245, 249, 268, 270, 272, 273, 274, 284, 285, 286, 290, 291, 292),
        "Serie C1 B",
    ),
    **dict.fromkeys(
        (302, 303, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 332, 365),
        "Premier League",
    ),
    **dict.fromkeys(
        (301, 304, 321, 322, 323, 325, 326, 327, 328, 329, 330, 331, 333, 334, 336, 337, 340, 342, 343, 344, 353, 363, 364, 379),
        "First Division",
    ),
    **dict.fromkeys(
        (335, 338, 339, 341, 345, 346, 347, 348, 349, 350, 351, 352, 354, 355, 356, 357, 360, 366, 367, 371, 372, 375, 392),
        "Second Division",
    ),
    **dict.fromkeys(
        (324, 358, 359, 361, 362, 368, 369, 370, 373, 374, 376, 378, 380, 382, 383, 384, 385, 386, 387, 390, 391, 393, 3306, 3311),
        "Third Division",
    ),
    **dict.fromkeys(
        (401, 403, 404, 405, 406, 408, 409, 410, 411, 412, 415, 418, 419, 420, 421, 422, 429, 436),
        "Bundesliga",
    ),
    **dict.fromkeys(
        (402, 407, 413, 416, 417, 423, 425, 426, 427, 428, 430, 433, 434, 435, 438, 439, 442, 465),
        "2. Bundesliga",
    ),
    **dict.fromkeys(
        (501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 513, 515, 517, 520, 521, 535, 538, 558),
        "Division 1",
    ),
    **dict.fromkeys(
        (511, 512, 514, 516, 518, 519, 522, 523, 524, 526, 527, 528, 529, 530, 533, 536, 539, 540, 541, 547),
        "Division 2",
    ),
}

SAVE_BASE_LEAGUE_BLOCKS = (
    (b"LIGA1", "Primera División", "spain"),
    (b"LIGA2", "Segunda División", "spain"),
    (b"LIGA2B", "Segunda División B", "spain_2b"),
    (b"SERIEA", "Serie A", "base"),
    (b"SERIEB", "Serie B", "base"),
    (b"SERIEC1X", "Serie C1 A", "base"),
    (b"SERIEC1X", "Serie C1 B", "base"),
    (b"PREMIERLEAGUE", "Premier League", "base"),
    (b"FIRSTDIVISION", "First Division", "base"),
    (b"SECONDDIVISION", "Second Division", "base"),
    (b"THIRDDIVISION", "Third Division", "base"),
    (b"FRANCE1", "Division 1", "base"),
    (b"FRANCE2", "Division 2", "base"),
    (b"BUNDES1", "Bundesliga", "base"),
    (b"BUNDES2", "2. Bundesliga", "base"),
)


@dataclass(frozen=True)
class GameDate:
    day: int
    month: int
    year: int


@dataclass(frozen=True)
class StaticPlayer:
    player_id: int
    name: str
    display_name: str
    surname: str
    age: int | str
    role: str
    nationality: str
    nationality_code: int | str
    base_stats: list[int] | None


@dataclass(frozen=True)
class TeamInfo:
    team_id: int
    name: str
    country: str
    league: str


@dataclass(frozen=True)
class StatRow:
    offset: int
    context_id: int
    next_player_id: int
    stat_pack: list[int]
    extra_pack: list[int]
    position_pack: list[int]

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:x}"


@dataclass(frozen=True)
class LivePlayerRecord:
    offset: int
    context_id: int
    source_player_id: int
    live_player_id: int
    full_name: str
    birth_day: int
    birth_month: int
    birth_year: int
    stat_pack: list[int]
    team_id: int
    current_yearly_salary: int
    contract_years_left: int | str
    contract_years_total: int | str
    contract_current_years_left: int | str
    contract_renewal_years: int | str
    contract_renewal_yearly_salary: int | str

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:x}"


@dataclass(frozen=True)
class ContractCandidate:
    offset: int
    team_id: int
    team: TeamInfo
    market_value: float
    yearly_salary: float
    years_left: int | str
    years_total: int | str
    legacy_years_hint: int | str


def little_u16(data: bytes) -> int:
    return int.from_bytes(data, "little")


def little_u32(data: bytes) -> int:
    return int.from_bytes(data, "little")


def little_f32(data: bytes) -> float:
    return struct.unpack("<f", data)[0]


def valid_date_parts(day: int, month: int, year: int) -> bool:
    return 1 <= day <= 31 and 1 <= month <= 12 and 1800 <= year <= 2100


def save_current_date(data: bytes) -> GameDate | None:
    for offset in SAVE_CURRENT_DATE_OFFSETS:
        if offset + 5 > len(data):
            continue
        day = data[offset + 1]
        month = data[offset + 2]
        year = little_u16(data[offset + 3 : offset + 5])
        if valid_date_parts(day, month, year):
            return GameDate(day=day, month=month, year=year)
    return None


def player_age(
    birth_day: int,
    birth_month: int,
    birth_year: int,
    season_year: int,
    reference_date: GameDate | None,
) -> int | str:
    if not valid_date_parts(birth_day, birth_month, birth_year):
        return ""
    if reference_date is None:
        return season_year - birth_year if birth_year <= season_year else ""

    age = reference_date.year - birth_year
    if (reference_date.month, reference_date.day) < (birth_month, birth_day):
        age -= 1
    return age if age >= 0 else ""


def game_missing_birthdate_year(birth_year: int) -> bool:
    return birth_year <= 1900 or birth_year >= 2000


def missing_birthdate_draw(record_id: int, display_name: str) -> int:
    key = f"{record_id}:{display_name}:{MISSING_BIRTHDATE_HASH_SALT}".encode("utf-8")
    return zlib.crc32(key) % 5


def missing_birthdate_age(
    record_id: int,
    display_name: str,
    birth_day: int,
    birth_month: int,
    season_year: int,
    reference_date: GameDate | None,
) -> int | str:
    reference_year = reference_date.year if reference_date is not None else season_year
    day = birth_day if 1 <= birth_day <= 31 else (reference_date.day if reference_date is not None else 1)
    month = birth_month if 1 <= birth_month <= 12 else (reference_date.month if reference_date is not None else 1)

    # MANAGCAL.EXE replaces invalid birth years with current_year - 25 - rand(5).
    # The real rand() draw is time-seeded at runtime and is not stored in the save,
    # so the extractor uses a stable per-player draw in the same 0..4 range.
    birth_year = reference_year - 25 - missing_birthdate_draw(record_id, display_name)
    return player_age(day, month, birth_year, season_year, reference_date)


def decode_pc_calcio_text(data: bytes) -> str:
    table: dict[int, str] = dict(TEXT_BYTE_MAP)
    for index, letter in enumerate("abcdefghijklmnopqrstuvwxyz"):
        table[(index + 1) ^ 1] = letter
    for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        table[0x20 + ((index + 1) ^ 1)] = letter
    text = "".join(table.get(byte, f"<{byte:02x}>") for byte in data).strip()
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def load_dmfi_records(path: Path) -> dict[int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"DMFIv1.0":
        raise ValueError(f"{path} is not a DMFIv1.0 file")

    count = little_u32(data[0x10:0x14])
    records: dict[int, bytes] = {}
    for index in range(count):
        pos = 0x14 + index * 13
        record_id = little_u32(data[pos : pos + 4])
        offset = little_u32(data[pos + 5 : pos + 9])
        length = little_u32(data[pos + 9 : pos + 13])
        records[record_id] = data[offset : offset + length]
    return records


def player_name_fields(record: bytes) -> dict[str, Any]:
    if len(record) < 12:
        return {"surname": "", "display_name": "", "joined_name": "", "name_fields_end": 0}

    surname_len = record[8]
    surname_start = 10
    surname_end = min(len(record), surname_start + surname_len)
    surname_raw = record[surname_start:surname_end]

    display_raw = b""
    name_fields_end = surname_end
    display_len_pos = surname_end
    if (
        display_len_pos + 2 < len(record)
        and record[display_len_pos + 1] == 0
        and 1 <= record[display_len_pos] <= 64
    ):
        display_len = record[display_len_pos]
        display_start = display_len_pos + 2
        display_end = display_start + display_len
        if display_end <= len(record):
            display_raw = record[display_start:display_end]
            name_fields_end = display_end

    joined_raw = b"\x41".join(part for part in (surname_raw, display_raw) if part)
    return {
        "surname": decode_pc_calcio_text(surname_raw),
        "display_name": decode_pc_calcio_text(display_raw),
        "joined_name": decode_pc_calcio_text(joined_raw),
        "name_fields_end": name_fields_end,
    }


def static_stat_pack(record: bytes) -> list[int] | None:
    if len(record) < 16:
        return None
    pack = list(record[-16:])
    return pack if all(value <= 99 for value in pack) else None


def static_player(
    record_id: int,
    record: bytes,
    season_year: int,
    reference_date: GameDate | None = None,
) -> StaticPlayer:
    names = player_name_fields(record)
    field_start = int(names["name_fields_end"])

    role = ""
    age: int | str = ""
    nationality_code: int | str = ""
    nationality = ""
    if field_start + 18 <= len(record):
        nationality_code = record[field_start + 8]
        role_code = record[field_start + 11]
        birth_day = record[field_start + 12]
        birth_month = record[field_start + 13]
        birth_year = little_u16(record[field_start + 14 : field_start + 16])
        role = ROLE_BY_DEFINITION.get(role_code, f"code_{role_code:02x}")
        nationality = NATIONALITY_NAMES.get(nationality_code, f"code_{nationality_code:02x}")
        display_name = str(names["display_name"] or names["joined_name"] or names["surname"])
        if game_missing_birthdate_year(birth_year):
            age = missing_birthdate_age(record_id, display_name, birth_day, birth_month, season_year, reference_date)
        else:
            age = player_age(birth_day, birth_month, birth_year, season_year, reference_date)

    return StaticPlayer(
        player_id=record_id,
        name=str(names["joined_name"]),
        display_name=str(names["display_name"]),
        surname=str(names["surname"]),
        age=age,
        role=role,
        nationality=nationality,
        nationality_code=nationality_code,
        base_stats=static_stat_pack(record),
    )


def load_static_players(
    path: Path,
    season_year: int,
    reference_date: GameDate | None = None,
) -> dict[int, StaticPlayer]:
    return {
        record_id: static_player(record_id, record, season_year, reference_date)
        for record_id, record in load_dmfi_records(path).items()
    }


def static_team_name(record: bytes) -> str:
    marker = record.find(b"\x00\xbc\x02\x00")
    if marker < 0:
        return ""

    body = marker + 4
    if body + 3 > len(record) or record[body + 2] != 0:
        return ""

    name_len = record[body + 1]
    name_start = body + 3
    name_end = name_start + name_len
    if name_end > len(record):
        return ""
    return decode_pc_calcio_text(record[name_start:name_end])


def team_country(team_id: int) -> str:
    if team_id in TEAM_COUNTRY_OVERRIDES:
        return TEAM_COUNTRY_OVERRIDES[team_id]
    for start, end, country in TEAM_COUNTRY_RANGES:
        if start <= team_id <= end:
            return country
    return ""


def find_nth(data: bytes, needle: bytes, occurrence: int) -> int:
    start = 0
    for _ in range(occurrence + 1):
        pos = data.find(needle, start)
        if pos < 0:
            return -1
        start = pos + len(needle)
    return pos


def read_u16_list(data: bytes, start: int, count: int) -> list[int]:
    if count <= 0 or start < 0 or start + count * 2 > len(data):
        return []
    return [little_u16(data[start + index * 2 : start + index * 2 + 2]) for index in range(count)]


def save_base_league_ids(data: bytes, label: bytes, occurrence: int) -> list[int]:
    pos = find_nth(data, label + b"\x1a", occurrence)
    if pos < 0:
        return []

    first_sep = data.find(b"\x1a", pos)
    second_sep = data.find(b"\x1a", first_sep + 1)
    if first_sep < 0 or second_sep < 0:
        return []

    count_pos = second_sep + 1
    if count_pos + 3 > len(data) or data[count_pos] not in (0, 1):
        return []

    count = little_u16(data[count_pos + 1 : count_pos + 3])
    if count > 128:
        return []
    return read_u16_list(data, count_pos + 3, count)


def save_spanish_league_ids(data: bytes, label: bytes, group_count: int = 1) -> list[int]:
    pos = find_nth(data, label + b"\x1a", 0)
    if pos < 0:
        return []

    count_pos = pos + len(label) + 1
    if count_pos + 3 > len(data) or data[count_pos] != 1:
        return []

    target_count = little_u16(data[count_pos + 1 : count_pos + 3]) * group_count
    if target_count <= 0 or target_count > 128:
        return []

    ids: list[int] = []
    seen: set[int] = set()
    read_start = count_pos + 3
    for offset in range(read_start, min(len(data) - 1, read_start + target_count * 8), 2):
        team_id = little_u16(data[offset : offset + 2])
        if not (1 <= team_id <= 199) or team_id in seen:
            continue
        ids.append(team_id)
        seen.add(team_id)
        if len(ids) == target_count:
            break
    return ids


def league_membership_from_save(data: bytes) -> dict[int, str]:
    league_by_id: dict[int, str] = {}
    occurrence_by_label: dict[bytes, int] = {}

    for label, league, layout in SAVE_BASE_LEAGUE_BLOCKS:
        if layout == "base":
            occurrence = occurrence_by_label.get(label, 0)
            ids = save_base_league_ids(data, label, occurrence)
            occurrence_by_label[label] = occurrence + 1
        elif layout == "spain_2b":
            ids = save_spanish_league_ids(data, label, group_count=4)
        else:
            ids = save_spanish_league_ids(data, label)

        for team_id in ids:
            league_by_id[team_id] = league

    return league_by_id


def static_team(record_id: int, record: bytes, league_by_id: dict[int, str] | None = None) -> TeamInfo:
    leagues = TEAM_LEAGUE_BY_ID if league_by_id is None else league_by_id
    return TeamInfo(
        team_id=record_id,
        name=static_team_name(record),
        country=team_country(record_id),
        league=leagues.get(record_id, ""),
    )


def load_teams(path: Path, league_by_id: dict[int, str] | None = None) -> dict[int, TeamInfo]:
    return {
        record_id: static_team(record_id, record, league_by_id)
        for record_id, record in load_dmfi_records(path).items()
    }


def find_stat_rows(data: bytes) -> list[StatRow]:
    rows: list[StatRow] = []
    for offset in range(0, len(data) - 48):
        if data[offset : offset + 2] != data[offset + 2 : offset + 4]:
            continue
        if data[offset + 4] != 0:
            continue
        if data[offset + 21 : offset + 23] != data[offset + 23 : offset + 25]:
            continue

        stat_pack = list(data[offset + 5 : offset + 21])
        extra_pack = list(data[offset + 25 : offset + 30])
        position_pack = list(data[offset + 30 : offset + 34])
        if not all(value <= 99 for value in stat_pack):
            continue
        if not all(value <= 99 for value in extra_pack):
            continue
        if max(stat_pack[:10]) < 20:
            continue

        rows.append(
            StatRow(
                offset=offset,
                context_id=little_u16(data[offset : offset + 2]),
                next_player_id=little_u16(data[offset + 21 : offset + 23]),
                stat_pack=stat_pack,
                extra_pack=extra_pack,
                position_pack=position_pack,
            )
        )
    return rows


def looks_like_player_row(
    data: bytes,
    offset: int,
    players: dict[int, StaticPlayer],
    teams: dict[int, TeamInfo],
) -> StatRow | None:
    if offset + 48 > len(data):
        return None
    if data[offset + 4] != 0:
        return None
    if data[offset + 21 : offset + 23] != data[offset + 23 : offset + 25]:
        return None

    first_team_id = little_u16(data[offset : offset + 2])
    second_team_id = little_u16(data[offset + 2 : offset + 4])
    next_player_id = little_u16(data[offset + 21 : offset + 23])
    if first_team_id not in teams or second_team_id not in teams:
        return None
    if next_player_id not in players:
        return None

    stat_pack = list(data[offset + 5 : offset + 21])
    extra_pack = list(data[offset + 25 : offset + 30])
    position_pack = list(data[offset + 30 : offset + 34])
    if not all(value <= 99 for value in stat_pack):
        return None
    if not all(value <= 99 for value in extra_pack):
        return None
    if max(stat_pack[:10]) < 20:
        return None
    if stat_pack[:10].count(0) >= 3:
        return None

    return StatRow(
        offset=offset,
        context_id=first_team_id,
        next_player_id=next_player_id,
        stat_pack=stat_pack,
        extra_pack=extra_pack,
        position_pack=position_pack,
    )


def find_player_rows(data: bytes, players: dict[int, StaticPlayer], teams: dict[int, TeamInfo]) -> list[StatRow]:
    rows: list[StatRow] = []
    for offset in range(0, len(data) - 48):
        row = looks_like_player_row(data, offset, players, teams)
        if row is not None:
            rows.append(row)
    return rows


def static_stats_in_save_order(base_stats: list[int]) -> list[int]:
    return [
        base_stats[0],
        base_stats[1],
        base_stats[2],
        base_stats[3],
        base_stats[5],
        base_stats[4],
        base_stats[6],
        base_stats[7],
        base_stats[8],
        base_stats[9],
    ]


def row_header_bytes(row: StatRow) -> list[int]:
    return list(row.context_id.to_bytes(2, "little") * 2 + b"\x00")


def embeds_following_header(row: StatRow, next_row: StatRow | None) -> bool:
    return next_row is not None and next_row.offset == row.offset + 5 and row.stat_pack[:5] == row_header_bytes(next_row)


def displayed_me(stats: Sequence[int]) -> int:
    return sum(stats[:4]) // 4


def score_stat_candidate(
    candidate: StatRow,
    next_candidate: StatRow | None,
    expected_stats: list[int],
    distance: int,
) -> tuple[int, str]:
    if expected_stats and candidate.stat_pack[:10] == expected_stats:
        return 1000 - distance, "base_match"
    if embeds_following_header(candidate, next_candidate):
        return -1000 - distance, "embedded_header"

    current_me = displayed_me(candidate.stat_pack)
    score = -distance
    if current_me >= 20:
        score += 50
    if candidate.stat_pack[:4].count(0) >= 3:
        score -= 100
    if candidate.stat_pack[:5].count(0) >= 4:
        score -= 100
    return score, "fallback"


def choose_current_stat_row(marker_index: int, rows: list[StatRow], expected_stats: list[int]) -> StatRow | None:
    marker = rows[marker_index]
    best_row: StatRow | None = None
    best_score = -10_000

    for candidate_index in range(marker_index + 1, min(len(rows), marker_index + 10)):
        candidate = rows[candidate_index]
        if candidate.offset - marker.offset >= 512:
            break
        next_candidate = rows[candidate_index + 1] if candidate_index + 1 < len(rows) else None
        score, _reason = score_stat_candidate(candidate, next_candidate, expected_stats, candidate_index - marker_index)
        if score > best_score:
            best_row = candidate
            best_score = score
    return best_row


def looks_like_money(value: float, maximum: int) -> bool:
    return (
        math.isfinite(value)
        and 1_000 <= value < maximum
        and abs(value - round(value)) <= max(1.0, abs(value) * 0.000001)
    )


def display_money(value: float) -> int:
    return int(round(value * DISPLAY_MONEY_MULTIPLIER))


def repeated_nibble_years(byte: int) -> int | None:
    high = byte >> 4
    low = byte & 0x0F
    if high == low and 1 <= high <= 9:
        return high
    return None


def find_contract_years(data: bytes, start: int, end: int) -> int | str:
    for offset in range(start, end):
        years = repeated_nibble_years(data[offset])
        if years is not None:
            return years
    return ""


def contract_years_from_code(byte: int) -> tuple[int, int] | None:
    high = byte >> 4
    low = byte & 0x0F
    # High nibble is years remaining; low nibble is the original/total term.
    if 0 <= high <= low <= 9:
        return high, low
    return None


def decoded_contract_years(tail: bytes) -> tuple[int | str, int | str]:
    if len(tail) >= 8 and looks_like_money(little_f32(tail[:4]), 2_000_000_000):
        years = contract_years_from_code(tail[7])
        if years is not None:
            return years

    if len(tail) >= 7 and tail[4] == 0x14:
        years = contract_years_from_code(tail[6])
        if years is not None:
            return years

    if len(tail) >= 6:
        years = contract_years_from_code(tail[5])
        if years is not None:
            return years
        if tail[5] == 0xFF:
            return 0, 0

    if len(tail) >= 7:
        years = contract_years_from_code(tail[6])
        if years is not None:
            return years

    return "", ""


def contract_candidate_score(candidate: ContractCandidate) -> tuple[int, int]:
    return (1 if candidate.legacy_years_hint != "" else 0, candidate.offset)


def renewal_candidate_for(
    candidate: ContractCandidate,
    candidates: Sequence[ContractCandidate],
) -> ContractCandidate | None:
    if not isinstance(candidate.years_left, int) or candidate.years_left != 1:
        return None

    possible_renewals = [
        renewal
        for renewal in candidates
        if renewal.offset > candidate.offset
        and renewal.team_id == candidate.team_id
        and 20 <= renewal.offset - candidate.offset <= 32
        and isinstance(renewal.years_left, int)
        and renewal.years_left > 0
    ]
    if not possible_renewals:
        return None
    return min(possible_renewals, key=lambda renewal: renewal.offset)


def contract_candidate_fields(
    candidate: ContractCandidate,
    renewal: ContractCandidate | None = None,
) -> dict[str, Any]:
    years_left = candidate.years_left
    renewal_years: int | str = 0 if isinstance(years_left, int) else ""
    renewal_salary: int | str = ""

    if renewal is not None and isinstance(years_left, int) and isinstance(renewal.years_left, int):
        renewal_years = renewal.years_left
        renewal_salary = display_money(renewal.yearly_salary)
        years_left = years_left + renewal.years_left

    return {
        "team_id": candidate.team_id,
        "team": candidate.team.name,
        "team_country": candidate.team.country,
        "team_league": candidate.team.league,
        "current_yearly_salary": display_money(candidate.yearly_salary),
        "contract_years_left": years_left,
        "contract_years_total": candidate.years_total,
        "contract_current_years_left": candidate.years_left,
        "contract_renewal_years": renewal_years,
        "contract_renewal_yearly_salary": renewal_salary,
    }


def empty_contract_fields() -> dict[str, Any]:
    return {
        "team_id": "",
        "team": "",
        "team_country": "",
        "team_league": "",
        "current_yearly_salary": "",
        "contract_years_left": "",
        "contract_years_total": "",
        "contract_current_years_left": "",
        "contract_renewal_years": "",
        "contract_renewal_yearly_salary": "",
    }


def contract_fields(data: bytes, marker_offset: int, stat_offset: int, teams: dict[int, TeamInfo]) -> dict[str, Any]:
    candidates: list[ContractCandidate] = []
    for offset in range(marker_offset + 34, max(marker_offset + 34, stat_offset - 9)):
        team_id = little_u16(data[offset : offset + 2])
        if team_id not in teams:
            continue

        market_value = little_f32(data[offset + 2 : offset + 6])
        yearly_salary = little_f32(data[offset + 6 : offset + 10])
        if not looks_like_money(market_value, 10_000_000_000):
            continue
        if not looks_like_money(yearly_salary, 2_000_000_000):
            continue

        contract_tail = data[offset + 10 : stat_offset]
        legacy_years_hint = find_contract_years(data, offset + 10, stat_offset)
        years_left, years_total = decoded_contract_years(contract_tail)
        team = teams[team_id]
        candidates.append(
            ContractCandidate(
                offset=offset,
                team_id=team_id,
                team=team,
                market_value=market_value,
                yearly_salary=yearly_salary,
                years_left=years_left,
                years_total=years_total,
                legacy_years_hint=legacy_years_hint,
            )
        )

    if not candidates:
        return empty_contract_fields()

    renewal_pairs = [
        (candidate, renewal)
        for candidate in candidates
        if (renewal := renewal_candidate_for(candidate, candidates)) is not None
    ]
    if renewal_pairs:
        candidate, renewal = max(renewal_pairs, key=lambda pair: contract_candidate_score(pair[0]))
        return contract_candidate_fields(candidate, renewal)

    candidate = max(candidates, key=contract_candidate_score)
    return contract_candidate_fields(candidate)


def parse_live_player_record(data: bytes, offset: int, teams: dict[int, TeamInfo]) -> LivePlayerRecord | None:
    if offset + 80 > len(data):
        return None

    context_id = little_u16(data[offset : offset + 2])
    live_player_id = little_u16(data[offset + 23 : offset + 25])
    if context_id not in teams:
        return None
    if data[offset + 2 : offset + 4] != data[offset : offset + 2]:
        return None
    if data[offset + 4] != 0 or data[offset + 26] != 0:
        return None
    if live_player_id < 40_000:
        return None

    stat_pack = list(data[offset + 5 : offset + 21])
    if not all(value <= 99 for value in stat_pack):
        return None
    if max(stat_pack[:10]) < 20:
        return None
    if stat_pack[:10].count(0) >= 3:
        return None

    short_name_len = data[offset + 27]
    if not 1 <= short_name_len <= 32:
        return None
    short_name_start = offset + 28
    short_name_end = short_name_start + short_name_len
    if short_name_end >= len(data):
        return None

    full_name_len = data[short_name_end]
    if not 1 <= full_name_len <= 80:
        return None
    full_name_start = short_name_end + 1
    full_name_end = full_name_start + full_name_len
    if full_name_end + 28 > len(data):
        return None

    short_name = decode_pc_calcio_text(data[short_name_start:short_name_end])
    full_name = decode_pc_calcio_text(data[full_name_start:full_name_end])
    if "<" in short_name + full_name:
        return None
    if not any(character.isalpha() for character in full_name):
        return None

    birth_day = data[full_name_end]
    birth_month = data[full_name_end + 1]
    birth_year = little_u16(data[full_name_end + 2 : full_name_end + 4])
    if not valid_date_parts(birth_day, birth_month, birth_year):
        return None

    technical_pack = list(data[full_name_end + 4 : full_name_end + 14])
    if not all(value <= 99 for value in technical_pack):
        return None
    if data[full_name_end + 14 : full_name_end + 18] != b"\x00\x00\x00\x00":
        return None

    contract_offset = full_name_end + 18
    team_id = little_u16(data[contract_offset : contract_offset + 2])
    if team_id not in teams:
        return None

    market_value = little_f32(data[contract_offset + 2 : contract_offset + 6])
    yearly_salary = little_f32(data[contract_offset + 6 : contract_offset + 10])
    if not looks_like_money(market_value, 10_000_000_000):
        return None
    if not looks_like_money(yearly_salary, 2_000_000_000):
        return None

    years_left, years_total = decoded_contract_years(data[contract_offset + 10 : contract_offset + 25])
    renewal_years: int | str = 0 if isinstance(years_left, int) else ""
    return LivePlayerRecord(
        offset=offset,
        context_id=context_id,
        source_player_id=little_u16(data[offset + 21 : offset + 23]),
        live_player_id=live_player_id,
        full_name=full_name,
        birth_day=birth_day,
        birth_month=birth_month,
        birth_year=birth_year,
        stat_pack=stat_pack,
        team_id=team_id,
        current_yearly_salary=display_money(yearly_salary),
        contract_years_left=years_left,
        contract_years_total=years_total,
        contract_current_years_left=years_left,
        contract_renewal_years=renewal_years,
        contract_renewal_yearly_salary="",
    )


def find_live_player_records(data: bytes, teams: dict[int, TeamInfo]) -> list[LivePlayerRecord]:
    records: list[LivePlayerRecord] = []
    for offset in range(0, len(data) - 80):
        record = parse_live_player_record(data, offset, teams)
        if record is not None:
            records.append(record)
    return records


def live_player_rows(
    data: bytes,
    players: dict[int, StaticPlayer],
    teams: dict[int, TeamInfo],
    season_year: int,
    reference_date: GameDate | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in find_live_player_records(data, teams):
        source_player = players.get(record.source_player_id)
        team = teams[record.team_id]
        if source_player is not None and source_player.base_stats is not None and len(source_player.base_stats) >= 4:
            current_me = displayed_me(source_player.base_stats)
        else:
            current_me = displayed_me(record.stat_pack)
        row: dict[str, Any] = {
            "player_id": record.live_player_id,
            "name": record.full_name,
            "age": player_age(record.birth_day, record.birth_month, record.birth_year, season_year, reference_date),
            "role": source_player.role if source_player is not None else "",
            "current_me": current_me,
            "nationality": source_player.nationality if source_player is not None else "",
            "nationality_code": source_player.nationality_code if source_player is not None else "",
            "team_id": record.team_id,
            "team": team.name,
            "team_country": team.country,
            "team_league": team.league,
            "current_yearly_salary": record.current_yearly_salary,
            "contract_years_left": record.contract_years_left,
            "contract_years_total": record.contract_years_total,
            "contract_current_years_left": record.contract_current_years_left,
            "contract_renewal_years": record.contract_renewal_years,
            "contract_renewal_yearly_salary": record.contract_renewal_yearly_salary,
            "save_offset": record.offset_hex,
            "id_marker_offset": record.offset_hex,
        }
        rows.append(row)
    return rows


def current_player_rows(
    data: bytes,
    players: dict[int, StaticPlayer],
    teams: dict[int, TeamInfo],
    season_year: int,
    reference_date: GameDate | None,
) -> list[dict[str, Any]]:
    best_by_player_id: dict[int, dict[str, Any]] = {}
    rows = sorted(find_player_rows(data, players, teams), key=lambda row: row.offset)

    for marker_index, marker in enumerate(rows[:-1]):
        player = players.get(marker.next_player_id)
        if player is None:
            continue

        expected_stats: list[int] = []
        if player.base_stats is not None and len(player.base_stats) >= 10:
            expected_stats = static_stats_in_save_order(player.base_stats)

        # The marker row carries the next player's id/contract; the following row carries their main stats.
        stat_row = rows[marker_index + 1]
        if stat_row.offset - marker.offset >= 512:
            continue

        stats = stat_row.stat_pack
        display_name = player.display_name or player.name or player.surname
        row: dict[str, Any] = {
            "player_id": player.player_id,
            "name": display_name,
            "age": player.age,
            "role": player.role,
            "current_me": displayed_me(stats),
            "nationality": player.nationality,
            "nationality_code": player.nationality_code,
            **contract_fields(data, marker.offset, stat_row.offset, teams),
            "save_offset": stat_row.offset_hex,
            "id_marker_offset": marker.offset_hex,
        }

        existing = best_by_player_id.get(player.player_id)
        if existing is None:
            best_by_player_id[player.player_id] = row
        elif expected_stats and stats[:10] == expected_stats:
            best_by_player_id[player.player_id] = row

    for row in live_player_rows(data, players, teams, season_year, reference_date):
        best_by_player_id[int(row["player_id"])] = row

    return [best_by_player_id[player_id] for player_id in sorted(best_by_player_id)]


def extract_current_players(
    input_path: Path = DEFAULT_INPUT,
    static_db: Path = DEFAULT_STATIC_DB,
    team_db: Path = DEFAULT_TEAM_DB,
    season_year: int | None = None,
) -> list[dict[str, Any]]:
    data = input_path.read_bytes()
    reference_date = None if season_year is not None else save_current_date(data)
    effective_season_year = season_year or (reference_date.year if reference_date else DEFAULT_SEASON_YEAR)
    players = load_static_players(static_db, effective_season_year, reference_date)
    league_by_id = dict(TEAM_LEAGUE_BY_ID)
    league_by_id.update(league_membership_from_save(data))
    teams = load_teams(team_db, league_by_id)
    return current_player_rows(data, players, teams, effective_season_year, reference_date)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "player_id",
        "name",
        "age",
        "role",
        "current_me",
        "nationality",
        "nationality_code",
        "team_id",
        "team",
        "team_country",
        "team_league",
        "current_yearly_salary",
        "contract_years_left",
        "contract_years_total",
        "contract_current_years_left",
        "contract_renewal_years",
        "contract_renewal_yearly_salary",
        "save_offset",
        "id_marker_offset",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--static-db", type=Path, default=DEFAULT_STATIC_DB)
    parser.add_argument("--team-db", type=Path, default=DEFAULT_TEAM_DB)
    parser.add_argument("--season-year", type=int, default=None)
    args = parser.parse_args()

    rows = extract_current_players(args.input, args.static_db, args.team_db, args.season_year)
    write_csv(args.output, rows)
    print(f"Wrote {len(rows)} players to {args.output}")


if __name__ == "__main__":
    main()
