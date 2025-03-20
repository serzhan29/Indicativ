from django.http import HttpResponse
from docx import Document
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from docx.enum.section import WD_ORIENT
from docx.shared import RGBColor, Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from urllib.parse import quote_plus
from .models import AggregatedIndicator, Direction, Year, Indicator, TeacherReport


@login_required
def download_teacher_report(request, direction_id, year_id):
    """Генерация отчета в Word с таблицей в альбомном формате"""
    teacher = request.user
    direction = get_object_or_404(Direction, id=direction_id)
    year = get_object_or_404(Year, id=year_id)

    aggregated_data = AggregatedIndicator.objects.filter(
        teacher=teacher,
        year=year,
        main_indicator__direction=direction
    )

    doc = Document()

    # Верхний текст
    para = doc.add_paragraph('Қожа Ахмет Ясауи атындағы Халықаралық қазақ-түрік университеті', style='Heading 1')
    run = para.runs[0]
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 0, 0)
    para.alignment = 1  # Центр

    para = doc.add_paragraph('«БЕКІТЕМІН»', style='Heading 2')
    run = para.runs[0]
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 0, 0)
    para.alignment = 2  # Право

    para = doc.add_paragraph('Инженерия факультетінің деканы ____________________ Нажи Генч')
    para.alignment = 2

    para = doc.add_paragraph('«____» ______________ 2024 ж.')
    para.alignment = 2

    para = doc.add_paragraph('КОМПЬЮТЕРЛІК ИНЖЕНЕРИЯ кафедрасының', style='Heading 2')
    para.alignment = 1

    para = doc.add_paragraph(
        f'{year.year} ОҚУ ЖЫЛЫНДАҒЫ {direction.name} БОЙЫНША ИНДИКАТИВТІ ЖӘНЕ {year.year} СТРАТЕГИЯЛЫҚ КӨРСЕТКІШТЕРІНІҢ ЕСЕБІ',
        style='Heading 1'
    )
    para.alignment = 1

    # Устанавливаем альбомную ориентацию
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    new_width, new_height = section.page_height, section.page_width
    section.page_width = new_width
    section.page_height = new_height

    # Создаем таблицу
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'

    # Устанавливаем ширину колонок
    table.columns[0].width = Inches(8)
    table.columns[1].width = Inches(1)
    table.columns[2].width = Inches(1)

    # Заголовки
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Главный индикатор и подиндикаторы"
    hdr_cells[1].text = "Единица измерения"
    hdr_cells[2].text = "Жоспар"

    for cell in hdr_cells:
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
        cell.paragraphs[0].alignment = 1  # Центр

    # Заполнение данных
    for data in aggregated_data:
        row = table.add_row().cells
        row[0].text = data.main_indicator.name
        row[1].text = data.main_indicator.unit
        row[2].text = str(data.total_value)

        # Форматирование строк
        for i, cell in enumerate(row):
            run = cell.paragraphs[0].runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.font.color.rgb = RGBColor(0, 0, 0)
            cell.paragraphs[0].alignment = 0 if i == 0 else 1  # Главный индикатор слева, остальное в центре

        # Подиндикаторы
        sub_indicators = Indicator.objects.filter(main_indicator=data.main_indicator, years=year)
        for ind in sub_indicators:
            sub_row = table.add_row().cells
            sub_row[0].text = ind.name
            sub_row[1].text = ind.unit
            sub_row[2].text = str(
                TeacherReport.objects.filter(
                    teacher=teacher,
                    indicator=ind,
                    year=year
                ).first().value or 0
            )

            # Форматирование подиндикаторов
            for i, cell in enumerate(sub_row):
                run = cell.paragraphs[0].runs[0]
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
                run.font.color.rgb = RGBColor(0, 0, 0)
                cell.paragraphs[0].alignment = 0 if i == 0 else 1  # Подиндикаторы слева, остальное в центре

    # Отправляем файл пользователю
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    file_name = f"Отчет учителя {teacher.first_name} {year.year}.docx"
    encoded_file_name = quote_plus(file_name)
    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_file_name}'

    doc.save(response)
    return response
