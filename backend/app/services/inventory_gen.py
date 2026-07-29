import os
from typing import List, Optional, Tuple

from ..config import TMP_DIR
from ..models import Credential, Host, Inventory
from ..security import decrypt_secret


def generate_inventory_file(
    inventory: Inventory,
    hosts: List[Host],
    credential: Optional[Credential],
    task_id: int,
) -> Tuple[str, Optional[str]]:
    """把 inventory + hosts 生成 ansible INI 格式临时文件。

    返回 (inventory 文件路径, 私钥临时文件路径或 None)。
    无分组主机列在文件顶部,其余按 group_name 分组。
    凭据变量直接写进每台主机的行内变量。
    """
    key_file = None
    cred_vars = ""
    if credential is not None and credential.secret_encrypted:
        secret = decrypt_secret(credential.secret_encrypted)
        if credential.type == "password":
            cred_vars = "ansible_user={} ansible_password={}".format(
                _quote(credential.username or "root"), _quote(secret)
            )
        elif credential.type == "key":
            key_file = os.path.join(TMP_DIR, "task_{}_key.pem".format(task_id))
            with open(key_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(secret)
                if not secret.endswith("\n"):
                    f.write("\n")
            try:
                os.chmod(key_file, 0o600)
            except OSError:
                pass
            cred_vars = "ansible_user={} ansible_ssh_private_key_file={}".format(
                _quote(credential.username or "root"), key_file
            )

    ungrouped: List[str] = []
    groups = {}
    for host in hosts:
        parts = [host.hostname]
        if host.port:
            parts.append("ansible_port={}".format(host.port))
        if cred_vars:
            parts.append(cred_vars)
        if host.vars:
            parts.append(host.vars.strip())
        line = " ".join(parts)
        group = (host.group_name or "").strip()
        if group:
            groups.setdefault(group, []).append(line)
        else:
            ungrouped.append(line)

    lines: List[str] = []
    lines.extend(ungrouped)
    for group in sorted(groups.keys()):
        if lines:
            lines.append("")
        lines.append("[{}]".format(group))
        lines.extend(groups[group])

    inv_file = os.path.join(TMP_DIR, "task_{}_inventory.ini".format(task_id))
    with open(inv_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
        f.write("\n")
    return inv_file, key_file


def _quote(value: str) -> str:
    """包含空格或特殊字符时用双引号包裹。"""
    if any(c in value for c in ' \t"\''):
        return '"{}"'.format(value.replace('"', '\\"'))
    return value
