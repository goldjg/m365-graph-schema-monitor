from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from xml.etree import ElementTree


@dataclass(frozen=True)
class PropertyInfo:
    name: str
    property_type: str
    nullable: bool
    is_collection: bool


@dataclass(frozen=True)
class TypeInfo:
    namespace: str
    name: str
    full_name: str
    kind: str
    properties: Dict[str, PropertyInfo]


@dataclass(frozen=True)
class SchemaSnapshot:
    types: Dict[str, TypeInfo]


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_nullable(value: str | None) -> bool:
    # OData nullable defaults to true when omitted.
    if value is None:
        return True
    return value.strip().lower() == "true"


def _unwrap_collection(type_name: str) -> tuple[str, bool]:
    value = type_name.strip()
    if value.startswith("Collection(") and value.endswith(")"):
        return value[len("Collection(") : -1], True
    return value, False


def parse_csdl_file(path: str | Path) -> SchemaSnapshot:
    xml_path = Path(path)
    root = ElementTree.parse(xml_path).getroot()

    parsed_types: Dict[str, TypeInfo] = {}
    for schema in root.iter():
        if _local_name(schema.tag) != "Schema":
            continue
        namespace = schema.attrib.get("Namespace")
        if not namespace:
            continue

        for type_node in list(schema):
            type_kind = _local_name(type_node.tag)
            if type_kind not in {"EntityType", "ComplexType"}:
                continue

            type_name = type_node.attrib.get("Name")
            if not type_name:
                continue
            full_name = f"{namespace}.{type_name}"

            properties: Dict[str, PropertyInfo] = {}
            for member in list(type_node):
                if _local_name(member.tag) != "Property":
                    continue

                property_name = member.attrib.get("Name")
                raw_type = member.attrib.get("Type")
                if not property_name or not raw_type:
                    continue

                unwrapped_type, is_collection = _unwrap_collection(raw_type)
                properties[property_name] = PropertyInfo(
                    name=property_name,
                    property_type=unwrapped_type,
                    nullable=_parse_nullable(member.attrib.get("Nullable")),
                    is_collection=is_collection,
                )

            parsed_types[full_name] = TypeInfo(
                namespace=namespace,
                name=type_name,
                full_name=full_name,
                kind=type_kind,
                properties={name: properties[name] for name in sorted(properties)},
            )

    return SchemaSnapshot(types={name: parsed_types[name] for name in sorted(parsed_types)})
