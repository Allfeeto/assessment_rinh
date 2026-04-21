from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from io import BytesIO
from xml.etree import ElementTree as ET

from .exceptions import PlxParsingError, PlxValidationError
from .validators import validate_uploaded_plx_file

DIFFGRAM_NS = 'urn:schemas-microsoft-com:xml-diffgram-v1'
DATASET_NS = 'http://tempuri.org/dsMMISDB.xsd'


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[-1]


def _attrs_dict(element: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, value in element.attrib.items():
        attrs[_strip_ns(key)] = value
    return attrs


@dataclass(slots=True)
class ParsedPlxDocument:
    source_filename: str
    document_attrs: dict[str, str]
    tables: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def table(self, name: str) -> list[dict[str, str]]:
        return self.tables.get(name, [])


class PlxParser:
    """Слой парсинга XML/PLX без бизнес-сопоставления к моделям Django."""

    def parse_upload(self, uploaded_file) -> ParsedPlxDocument:
        validate_uploaded_plx_file(uploaded_file)
        filename = uploaded_file.name

        try:
            content = uploaded_file.read()
        except Exception as exc:  # pragma: no cover - защитный периметр
            raise PlxValidationError('Не удалось прочитать загруженный файл.') from exc

        if not content:
            raise PlxValidationError('Загружен пустой файл.')

        return self.parse_bytes(content=content, source_filename=filename)

    def parse_bytes(self, *, content: bytes, source_filename: str) -> ParsedPlxDocument:
        try:
            root = ET.parse(BytesIO(content)).getroot()
        except ET.ParseError as exc:
            raise PlxParsingError('Файл не является корректным PLX/XML документом.') from exc

        if _strip_ns(root.tag) != 'Документ':
            raise PlxParsingError('Некорректный формат PLX: не найден корневой узел "Документ".')

        document_attrs = _attrs_dict(root)
        diffgram = root.find(f'{{{DIFFGRAM_NS}}}diffgram')
        if diffgram is None:
            raise PlxParsingError('Некорректный PLX: отсутствует блок diffgram.')

        dataset = diffgram.find(f'{{{DATASET_NS}}}dsMMISDB')
        if dataset is None:
            raise PlxParsingError('Некорректный PLX: отсутствует набор данных dsMMISDB.')

        tables: dict[str, list[dict[str, str]]] = defaultdict(list)

        for element in dataset:
            table_name = _strip_ns(element.tag)
            row_attrs = _attrs_dict(element)
            tables[table_name].append(row_attrs)

            # Вложенные строки ООП (профили внутри направления) извлекаем отдельной таблицей.
            if table_name == 'ООП':
                for nested in element:
                    tables['ООП_вложенные'].append(_attrs_dict(nested))

        return ParsedPlxDocument(
            source_filename=source_filename,
            document_attrs=document_attrs,
            tables=dict(tables),
        )

