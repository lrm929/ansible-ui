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
    凭据变量直接写进每台主机的行内变量;windows 连接参数与清单级
    默认账号密码写到 [all:vars](行内变量优先级更高)。
    credential 为「模板凭据 > 清单凭据」裁决后的有效凭据,由调用方传入。
    """
    os_type = ((inventory.os_type if inventory else None) or "linux").lower()

    key_file = None
    cred_vars = ""
    use_default_account = True
    if credential is not None and credential.secret_encrypted:
        if os_type == "windows" and credential.type == "key":
            # key 类型凭据对 windows(winrm)无意义,回落到清单默认账号密码
            pass
        else:
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
            use_default_account = False

    # [all:vars]:连接方式、兜底端口、清单默认账号密码
    all_vars: List[str] = []
    if os_type == "windows":
        all_vars.append("ansible_connection=winrm")
        all_vars.append("ansible_winrm_server_cert_validation=ignore")
    default_port = inventory.default_port if inventory else None
    if default_port:
        all_vars.append("ansible_port={}".format(default_port))
    elif os_type == "windows":
        all_vars.append("ansible_port=5985")
    # linux 不显式写 22,沿用 ansible 默认
    if use_default_account and inventory is not None:
        if inventory.default_username:
            all_vars.append("ansible_user={}".format(_quote(inventory.default_username)))
        if inventory.default_password_encrypted:
            all_vars.append(
                "ansible_password={}".format(
                    _quote(decrypt_secret(inventory.default_password_encrypted))
                )
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
    if all_vars:
        if lines:
            lines.append("")
        lines.append("[all:vars]")
        lines.extend(all_vars)

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
