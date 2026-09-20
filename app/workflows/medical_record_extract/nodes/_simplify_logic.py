import json
import re
from copy import deepcopy

target = ['血常规', '大生化', '凝血四项', '血栓四项', '乙丙艾梅8项', '尿常规', '心电图检查', '血液凝血功能检查', 'CRP',
          'DIC全套7项', '微生物检验报告单', '血型', '血液生化检查', 'TEG常规检测', '输血前传染病检测', '尿液电解质',
          '尿液电解质', '冠状动脉CTA+钙化积分', '心肌酶2项']


def parse2markdown_table(html_table: list[list]) -> str:
    if not html_table:
        return ""

    # 生成表头行
    headers = html_table[0]
    header_row = "| " + " | ".join(headers) + " |"

    # 生成分隔线行
    separator_row = "| " + " | ".join(["---" for _ in headers]) + " |"

    # 生成数据行
    data_rows = []
    for row in html_table[1:]:
        # 确保每行数据与表头列数一致
        if len(row) != len(headers):
            # 如果列数不匹配，用空字符串填充缺少的列
            row = row + [""] * (len(headers) - len(row))
        data_row = "| " + " | ".join(row) + " |"
        data_rows.append(data_row)

    # 组合所有行
    markdown_table = header_row + "\n" + separator_row
    if data_rows:
        markdown_table += "\n" + "\n".join(data_rows)

    return markdown_table


def simplify_html_table(html_table: str) -> str:
    pattern = r'<th\b[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*)</th>'
    matches = re.findall(pattern, html_table, re.IGNORECASE)
    table = []
    row = []
    for i, match in enumerate(matches, 1):
        # print(f"{i}: {match.strip()}")
        row.append(match.strip())

    table.append(deepcopy(row))
    row.clear()

    pattern = r'<td\b[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*)</td>'
    matches = re.findall(pattern, html_table, re.IGNORECASE)
    for i, match in enumerate(matches, 1):
        # print(f"{i}: {match.strip()}")
        row.append(match.strip())
        if len(row) >= len(table[0]):
            table.append(deepcopy(row))
            row.clear()

    return parse2markdown_table(table)


def main(text: str) -> dict:
    document = json.loads(text)
    # 入院日期和出院日期
    ryrq = ''
    cyrq = ''

    # 出院记录-治疗经过
    zljg = ''

    # 医嘱单+手术记录
    sample_records = []
    # 医嘱单：
    yz = []

    # 入院记录.
    ryjl = []
    for item in document:
        # 初始化content变量
        content = item.get("content", {})

        # 提取入院日期和出院日期：
        if item.get('title') in ['出院记录', '24小时内入出院记录']:
            content = item.get("content", item.get("structured", {}))

            # 适配24小时内入出院记录的结构：
            if '出院记录' in content:
                content = content.get('出院记录')

            if isinstance(content, dict) and content:
                ryrq = content.get('入院日期', '')
                cyrq = content.get('出院日期', '')
                zljg = content.get('治疗经过','')
            else:
                content = item.get("structured", {})
                if isinstance(content, dict) and content:
                    ryrq = content.get('入院日期', '')
                    cyrq = content.get('出院日期', '')
                    zljg = content.get('治疗经过','')

        if item.get("title") in ['临时医嘱单', '长期医嘱单']:
            if isinstance(content, dict) and content:
                medical_advice_content = content.get("医嘱内容", "")
                if medical_advice_content != "":
                    simplified_table = simplify_html_table(medical_advice_content)
                    item["content"]["医嘱内容"] = simplified_table

        # 屏蔽入院记录和出院记录。目的是为了后面提取治疗方式使用，避免入院和出院记录的内容造成干扰；
        if item.get('title') not in ['出院记录', '入院记录', '住院病案首页']:
            content = item.get("content", item.get("structured", {}))
            if item.get("title") == '检验检查记录':
                if isinstance(content, list) and content:
                    temp_content = []
                    for record in content:
                        if '报告标题' in record:
                            report_title = record.get("报告标题", "")
                            if all(t not in report_title for t in target):
                                temp_content.append(record)
                    content = temp_content
            sample_records.append({
                'title': item.get("title"),
                'content': content
            })

        # 只提取入院记录的主诉、现病史、既往史、手术史
        if item.get('title', '') in ['入院记录', '24小时内入出院记录']:
            content = item.get("content", item.get("structured", {}))

            if not isinstance(content, dict):
                continue

            # 兼容提取的JSON数据格式不标准：{"title":"入院记录","content":{"入院记录":[]}}
            if '入院记录' in content:
                content = content.get('入院记录')
            if isinstance(content, list):
                content = content[0]
            elif isinstance(content, dict):
                # 如果本身就是字典，直接使用
                content = content

            # 防止出院记录提取不到入院日期
            if not ryrq:
                ryrq = content.get('入院日期', '')

            if not cyrq:
                cyrq = content.get('出院日期', '')

            ryjl.append({
                "主诉": content.get('主诉', ''),
                "现病史": content.get('现病史', ''),
                "既往史": content.get('既往史', ''),
                "手术外伤史": content.get('手术外伤史', '')
            })

        # 只提取医嘱的内容：
        if sample_records:
            for item in sample_records:
                if item.get("title") in ['临时医嘱单', '长期医嘱单']:
                    yz.append({
                        'title': item.get('title', ''),
                        'content': item.get('content')
                    })

    return {
        'text': json.dumps(document, ensure_ascii=False),
        'ryrq': ryrq,
        'cyrq': cyrq,
        'zljg':zljg,#治疗经过
        'sample_records': json.dumps(sample_records, ensure_ascii=False),
        'ryjl': json.dumps(ryjl, ensure_ascii=False),
        'yz': json.dumps(yz, ensure_ascii=False),
    }