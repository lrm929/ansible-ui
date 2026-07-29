import csv
import io

from ..models import Host

# 表头列名 -> Host 字段(不区分大小写)
_HEADER_MAP = {
    "hostname": "hostname",
    "port": "port",
    "group_name": "group_name",
    "vars": "vars",
    "comment": "comment",
}


def decode_csv_bytes(data: bytes) -> str:
    """bytes -> 文本,先试 utf-8-sig 再 gbk。"""
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def parse_csv(text: str):
    """解析 CSV 文本,返回 (rows, errors)。

    首行若含 hostname(不区分大小写)则为表头,按列名映射,多余列忽略;
    否则无表头,每行第一列 hostname,第二列若为数字则为 port。
    rows 元素为 dict:hostname/port/group_name/vars/comment。
    """
    rows = []
    errors = []
    reader = csv.reader(io.StringIO(text))
    records = [r for r in reader if any(cell.strip() for cell in r)]
    if not records:
        return rows, errors

    first = [cell.strip().lower() for cell in records[0]]
    has_header = "hostname" in first

    if has_header:
        col_map = {}  # 列下标 -> 字段名
        for idx, name in enumerate(first):
            field = _HEADER_MAP.get(name)
            if field and field not in col_map.values():
                col_map[idx] = field
        data_records = records[1:]
        line_offset = 1
    else:
        col_map = None
        data_records = records
        line_offset = 0

    for i, record in enumerate(data_records):
        line_no = i + 1 + line_offset
        if col_map is not None:
            item = {field: "" for field in ("hostname", "port", "group_name", "vars", "comment")}
            for idx, field in col_map.items():
                if idx < len(record):
                    item[field] = record[idx].strip()
        else:
            item = {
                "hostname": record[0].strip(),
                "port": record[1].strip() if len(record) > 1 else "",
                "group_name": "",
                "vars": "",
                "comment": "",
            }
        if not item["hostname"]:
            errors.append("第{}行: 主机名为空".format(line_no))
            continue
        item["port"] = _parse_port(item["port"])
        rows.append(item)
    return rows, errors


def _parse_port(value) -> int:
    try:
        port = int(str(value).strip())
        if 1 <= port <= 65535:
            return port
    except (TypeError, ValueError):
        pass
    return 22


def upsert_hosts(db, inventory_id: int, rows):
    """按 (inventory_id, hostname) upsert,返回 (added, updated)。"""
    added = 0
    updated = 0
    for item in rows:
        host = (
            db.query(Host)
            .filter(Host.inventory_id == inventory_id, Host.hostname == item["hostname"])
            .first()
        )
        if host is None:
            db.add(
                Host(
                    inventory_id=inventory_id,
                    hostname=item["hostname"],
                    port=item["port"],
                    group_name=item.get("group_name", ""),
                    vars=item.get("vars", ""),
                    comment=item.get("comment", ""),
                )
            )
            added += 1
        else:
            host.port = item["port"]
            host.group_name = item.get("group_name", "")
            host.vars = item.get("vars", "")
            host.comment = item.get("comment", "")
            updated += 1
    db.commit()
    return added, updated
