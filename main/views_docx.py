from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.section import WD_SECTION, WD_ORIENTATION
from django.shortcuts import get_object_or_404
from .models import Direction, Year, MainIndicator, Indicator, TeacherReport
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.oxml.ns import qn
from urllib.parse import quote


def set_bold(run, bold=True):
    run.bold = bold
    return run

def set_table_borders(table):
    for row in table.rows:
        for cell in row.cells:
            cell_xml = cell._element
            tbl_cell_properties = cell_xml.get_or_add_tcPr()

            borders_xml = '''
            <w:tcBorders {}>
                <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            </w:tcBorders>
            '''.format(nsdecls('w'))

            borders_element = parse_xml(borders_xml)
            tbl_cell_properties.append(borders_element)

def set_landscape(doc):
    section = doc.sections[0]
    section.orientation = WD_ORIENTATION.LANDSCAPE  # Устанавливаем альбомную ориентацию
    section.page_height, section.page_width = section.page_width, section.page_height

def set_font(run, font_name='Times New Roman', size=14):
    run.font.name = font_name
    r = run._element
    r.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    run.font.size = Pt(size)

@login_required
def generate_word_report(request, direction_id, year_id):
    direction = get_object_or_404(Direction, id=direction_id)
    year = get_object_or_404(Year, id=year_id)
    main_indicators = MainIndicator.objects.filter(direction=direction, years=year)

    doc = Document()
    set_landscape(doc)  # Устанавливаем альбомную ориентацию

    # Добавляем заголовок
    p = doc.add_paragraph("Қожа Ахмет Ясауи атындағы Халықаралық қазақ-түрік университеті")
    set_font(p.add_run())
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    p = doc.add_paragraph("\n«БЕКІТЕМІН»\nИнженерия факультетінің деканы ____________________ Нажи Генч\n«____» ______________ 2024 ж.")
    set_font(p.add_run())
    p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

    p = doc.add_paragraph(f"КОМПЬЮТЕРЛІК ИНЖЕНЕРИЯ кафедрасының\n{year.year} ОҚУ ЖЫЛЫНДАҒЫ ҒЫЛЫМ САЛАСЫ БОЙЫНША ИНДИКАТИВТІ ЖӘНЕ СТРАТЕГИЯЛЫҚ КӨРСЕТКІШТЕРІНІҢ ЕСЕБІ ЖӘНЕ {year.year + 1} ОҚУ ЖЫЛЫНА ЖОСПАРЫ")
    set_font(p.add_run())
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # Создаем таблицу
    table = doc.add_table(rows=1, cols=8)
    hdr_cells = table.rows[0].cells
    headers = ["Индикатор атауы", "Өлшеу бірлігі", "Жоспар 2022-2023 оқу жылы", "Есеп 2023-2024 оқу жылы",
               "Жоспар 2024-2025 оқу жылы", "Өткен жылғы орындалған көрсеткішке +20%", "Ескерту"]
    for i, text in enumerate(headers):
        hdr_cells[i].text = text
        set_bold(hdr_cells[i].paragraphs[0].runs[0])
        set_font(hdr_cells[i].paragraphs[0].runs[0])  # Устанавливаем шрифт для заголовков

    for main_indicator in main_indicators:
        row_cells = table.add_row().cells
        row_cells[0].text = f"IV. {main_indicator.name}"
        row_cells[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

        indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)
        for indicator in indicators:
            report = TeacherReport.objects.filter(indicator=indicator, year=year, teacher=request.user).first()
            values = [
                indicator.name, "Саны",
                str(report.value if report else 0), "-", "-", "-", "-"
            ]
            row_cells = table.add_row().cells
            for i, value in enumerate(values):
                row_cells[i].text = value
                set_font(row_cells[i].paragraphs[0].runs[0])  # Устанавливаем шрифт для значений

    set_table_borders(table)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    user = request.user
    file_name = f'Отчет - {year.year} - {user.first_name or "Без_имени"} {user.last_name or "Без_фамилии"}.docx'

    encoded_file_name = quote(file_name.encode('utf-8'))
    response['Content-Disposition'] = f'attachment; filename="{encoded_file_name}"; filename*=UTF-8\'\'{encoded_file_name}'
    doc.save(response)
    return response