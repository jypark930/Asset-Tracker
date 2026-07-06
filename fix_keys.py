import sys
import re

file_path = 'pages/4_📈_투자현황.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update function signatures
content = content.replace('def render_detail_table(owner_key):', 'def render_detail_table(owner_key, prefix=""):')
content = content.replace('def _render_group(title, icon, invs):', 'def _render_group(title, icon, invs, prefix=""):')
content = content.replace('_render_group("현금성 자산 원금", "💰", cash_invs)', '_render_group("현금성 자산 원금", "💰", cash_invs, prefix)')
content = content.replace('_render_group("비현금성 자산 원금", "🏠", non_cash_invs)', '_render_group("비현금성 자산 원금", "🏠", non_cash_invs, prefix)')

# 2. Update keys in f-strings
content = content.replace('stk_edit_key = f"se_{inv[\'id\']}_{i}"', 'stk_edit_key = f"{prefix}se_{inv[\'id\']}_{i}"')
content = content.replace('key=f"q_{inv[\'id\']}_{sname}"', 'key=f"{prefix}q_{inv[\'id\']}_{sname}"')
content = content.replace('key=f"a_{inv[\'id\']}_{sname}"', 'key=f"{prefix}a_{inv[\'id\']}_{sname}"')
content = content.replace('key=f"del_{inv[\'id\']}_{sname}"', 'key=f"{prefix}del_{inv[\'id\']}_{sname}"')
content = content.replace('key=f"save_{inv[\'id\']}_{sname}"', 'key=f"{prefix}save_{inv[\'id\']}_{sname}"')

content = content.replace('edit_key_p = f"ep_{inv[\'id\']}"', 'edit_key_p = f"{prefix}ep_{inv[\'id\']}"')
content = content.replace('key=f"p_{inv[\'id\']}"', 'key=f"{prefix}p_{inv[\'id\']}"')
content = content.replace('key=f"a_{inv[\'id\']}"', 'key=f"{prefix}a_{inv[\'id\']}"')
content = content.replace('key=f"save_acc_{inv[\'id\']}"', 'key=f"{prefix}save_acc_{inv[\'id\']}"')

content = content.replace('edit_key_s = f"es_{inv[\'id\']}"', 'edit_key_s = f"{prefix}es_{inv[\'id\']}"')
content = content.replace('edit_key = f"e_{inv[\'id\']}"', 'edit_key = f"{prefix}e_{inv[\'id\']}"')

# 3. Update calls at the bottom
content = content.replace('render_detail_table("준영")', 'render_detail_table("준영", prefix="fam_jy_")', 1)
content = content.replace('render_detail_table("지윤")', 'render_detail_table("지윤", prefix="fam_ji_")', 1)
content = content.replace('render_detail_table("준영")', 'render_detail_table("준영", prefix="tab_jy_")', 1)
content = content.replace('render_detail_table("지윤")', 'render_detail_table("지윤", prefix="tab_ji_")', 1)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
