from django.db.models import Sum
from django.http import HttpResponse
from docx import Document
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from .models import AggregatedIndicator, Direction, Year, Indicator, TeacherReport, User, MainIndicator
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_PARAGRAPH_ALIGNMENT
from django.views import View
from urllib.parse import quote
from user.models import Department, Faculty
from docx.shared import Cm
from docx.enum.table import WD_ALIGN_VERTICAL
from django.db import models
from datetime import datetime
from django.utils.timezone import now


def create_first_page(doc, faculty_name, year):
    """Функция для создания первой страницы отчета"""
    next_year = year + 1  # Следующий учебный год

    # --- Первая страница ---
    doc.add_paragraph("Қожа Ахмет Ясауи атындағы Халықаралық қазақ-түрік университеті").alignment = WD_ALIGN_PARAGRAPH.CENTER

    para = doc.add_paragraph(
        "«БЕКІТЕМІН»\n"
        "Сапа бойынша басшылық өкілі, Ғылым және стратегиялық даму вице-ректоры\n"
        "__________________________ А.Ошибаева\n"
        f"«____» _______________ {year}ж."
    )
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # Пустые строки
    for _ in range(6):
        doc.add_paragraph("")

    doc.add_paragraph(f"{faculty_name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"{year} - {next_year} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("\nКентау").alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Добавляем разрыв страницы для следующей части отчета
    doc.add_page_break()

def init_document(selected_year, faculty):
    document = Document()

    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    new_width, new_height = section.page_height, section.page_width
    section.page_width = new_width
    section.page_height = new_height
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)

    footer = section.footer
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.text = f"Жүктеу күні мен уақыты: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"

    document.add_paragraph("Қожа Ахмет Ясауи атындағы Халықаралық қазақ-түрік университеті").alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = document.add_paragraph(
        "«БЕКІТЕМІН»\nСапа бойынша басшылық өкілі, Ғылым және стратегиялық даму вице-ректоры\n"
        f"__________________________ А.Ошибаева\n«____» _______________ {selected_year.year}ж."
    )
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for _ in range(6):
        document.add_paragraph("")

    document.add_paragraph(f"{faculty.name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"{selected_year.year} - {selected_year.year + 1} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("\nТүркістан").alignment = WD_ALIGN_PARAGRAPH.CENTER

    document.add_page_break()

    return document

def add_direction_title(document, selected_year, faculty, direction):
    for _ in range(6):
        document.add_paragraph("")
    document.add_paragraph(f"{faculty.name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"{selected_year.year} - {selected_year.year + 1} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"{direction.id}  {direction.name.upper()}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_page_break()

def create_indicator_table(document, departments):
    # Создаем таблицу с 3 + количеством департаментов столбцов
    table = document.add_table(rows=1, cols=3 + len(departments))
    table.style = 'Table Grid'

    cols = table.columns

    # Устанавливаем ширину столбцов
    cols[0].width = Inches(1)  # Код (меньше)
    cols[1].width = Inches(5)  # Индикатор атауы (больше)
    for idx in range(2, len(cols) - 1):  # столбцы для департаментов
        cols[idx].width = Inches(2)
    cols[-1].width = Inches(1)  # Сумма (меньше)

    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Код'
    hdr_cells[1].text = 'Индикатор атауы'
    for idx, dept in enumerate(departments):
        hdr_cells[2 + idx].text = dept.name
    hdr_cells[-1].text = 'Сумма'

    # Выравнивание текста в заголовках по центру
    for cell in hdr_cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    return table

def set_cell_font(cell, bold=False, align_center=False):
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if align_center else WD_ALIGN_PARAGRAPH.LEFT
        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
            run.font.size = Pt(12)
            run.font.bold = bold
            run.font.color.rgb = None  # чёрный

def add_footer(section):
    """
    Время нижный колонтинул
    """
    footer = section.footer
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.text = f"Жүктеу күні мен уақыты: {now().strftime('%d-%m-%Y %H:%M:%S')}"

def generate_docx_response(doc, teacher, year):
    """
    Генерирует HttpResponse с Word-документом для скачивания.

    :param doc: Объект Document (python-docx)
    :param teacher: Объект учителя
    :param year: Объект года
    :return: HttpResponse с документом
    """
    file_name = f"Мұғалім {teacher.last_name} {teacher.first_name} - {year.year}ж.docx"
    encoded_file_name = quote(file_name)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_file_name}'

    doc.save(response)
    return response

def configure_page(doc):
    """
    Настраивает ориентацию и отступы страницы документа Word.

    :param doc: объект docx.Document
    """
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    # Меняем местами ширину и высоту, т.к. ландшафт
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)

@login_required
def download_teacher_report(request, teacher_id, direction_id, year_id):
    """Генерация отчета в Word с правильным форматированием"""
    teacher = get_object_or_404(User, id=teacher_id)
    direction = get_object_or_404(Direction, id=direction_id)
    year = get_object_or_404(Year, id=year_id)
    next_year = year.year + 1  # Следующий учебный год
    faculty_name = teacher.profile.faculty.name if teacher.profile.faculty else "Көрсетілмеген"

    aggregated_data = AggregatedIndicator.objects.filter( teacher=teacher, year=year, main_indicator__direction=direction)
    doc = Document()
    # --- Первая страница ---
    create_first_page(doc, faculty_name, year.year)

    for _ in range(6):
        doc.add_paragraph("")

    doc.add_paragraph(f"{faculty_name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"{year.year} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"{direction.id}  {direction.name.upper()}").alignment = WD_ALIGN_PARAGRAPH.CENTER

    # --- Страница с таблицей ---
    doc.add_page_break()
    # --- Настройка страницы ---
    configure_page(doc)
    # Время
    section = doc.sections[-1]
    add_footer(section)
    # --- Таблица ---
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    # Установка ширины столбцов
    column_widths = [Cm(1), Cm(24), Cm(1), Cm(1)]
    # Заголовки
    hdr_cells = table.rows[0].cells
    headers = ["Код", "Индикатор атауы", "Өлшем бірлігі", "Сумма"]
    for idx, text in enumerate(headers):
        hdr_cells[idx].text = text
        # Установка ширины ячеек
        hdr_cells[idx].width = column_widths[idx]
        hdr_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = hdr_cells[idx].paragraphs[0].runs[0]
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)

    # Данные
    for data in aggregated_data:
        row = table.add_row().cells
        row_data = [
            data.main_indicator.code or "-",
            data.main_indicator.name,
            data.main_indicator.unit,
            str(data.total_value),
        ]
        for idx, value in enumerate(row_data):
            row[idx].text = value
            row[idx].width = column_widths[idx]  # Устанавливаем ширину для каждой ячейки
            run = row[idx].paragraphs[0].runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            row[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if idx == 1 else WD_ALIGN_PARAGRAPH.CENTER

        # Подиндикаторы
        sub_indicators = Indicator.objects.filter(main_indicator=data.main_indicator, years=year)
        for ind in sub_indicators:
            sub_row = table.add_row().cells
            sub_row_data = [
                ind.code or "-",
                ind.name,
                ind.unit,
                str(
                    TeacherReport.objects.filter(
                        teacher=teacher,
                        indicator=ind,
                        year=year
                    ).first().value or 0
                ),
            ]
            for idx, value in enumerate(sub_row_data):
                sub_row[idx].text = value
                sub_row[idx].width = column_widths[idx]
                run = sub_row[idx].paragraphs[0].runs[0]
                run.font.name = 'Times New Roman'
                run.font.size = Pt(14)
                sub_row[idx].paragraphs[
                    0].alignment = WD_ALIGN_PARAGRAPH.LEFT if idx == 1 else WD_ALIGN_PARAGRAPH.CENTER

    # Файлды қайтару
    return generate_docx_response(doc, teacher, year)


class TeacherReportWordExportView(View):
    def get(self, request, *args, **kwargs):
        year_id = request.GET.get('year')
        teacher_id = request.GET.get('teacher')

        if not year_id:
            return HttpResponse("Оқу жылы көрсетілмеген", status=400)

        year = get_object_or_404(Year, id=year_id)
        teacher = get_object_or_404(User, id=teacher_id) if teacher_id else request.user
        directions = Direction.objects.all().order_by('id')

        next_year = year.year + 1

        # Получаем факультет из профиля
        faculty_name = (teacher.profile.faculty.name if hasattr(teacher, 'profile') and teacher.profile.faculty else "Факультет")

        doc = Document()
        # --- Настройка страницы ---
        configure_page(doc)
        # --- Первая страница ---
        create_first_page(doc, faculty_name, year.year)
        # Время
        section = doc.sections[-1]
        add_footer(section)

        for direction in directions:

            for _ in range(6):
                doc.add_paragraph("")

            doc.add_paragraph(f"{faculty_name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph(f"{year.year} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph(f"{direction.id}  {direction.name.upper()}").alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Кесте беті
            doc.add_page_break()
            main_indicators = MainIndicator.objects.filter(direction=direction, years=year)

            if not main_indicators.exists():
                doc.add_paragraph("Индикаторлар бойынша деректер жоқ.")
                continue

            # Создание таблицы с правильным порядком столбцов
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Код'
            hdr_cells[1].text = 'Индикатор'
            hdr_cells[2].text = 'Өлшем бірлігі'
            hdr_cells[3].text = 'Мәні'
            set_cell_font(hdr_cells[0], bold=True, align_center=True)
            set_cell_font(hdr_cells[1], bold=True)
            set_cell_font(hdr_cells[2], bold=True, align_center=True)
            set_cell_font(hdr_cells[3], bold=True, align_center=True)

            # Устанавливаем ширину столбцов
            for col in table.columns:
                if col.cells[0].text == 'Код':
                    col.width = Cm(2)  # Код индикатора
                elif col.cells[0].text == 'Индикатор':
                    col.width = Cm(14)  # Название индикатора — широкий столбец
                elif col.cells[0].text == 'Өлшем бірлігі':
                    col.width = Cm(2)  # Единица измерения
                else:
                    col.width = Cm(2)  # Значение


            # Центрируем заголовки столбцов
            for cell in hdr_cells:
                set_cell_font(cell, bold=True, align_center=True)

            for main_indicator in main_indicators:
                aggregated_data = AggregatedIndicator.objects.filter(
                    teacher=teacher, main_indicator=main_indicator, year=year
                ).first()

                # Если агрегированные данные есть, используем их
                if aggregated_data:
                    total_value = aggregated_data.total_value
                else:
                    total_value = 0  # Если данных нет, ставим 0

                # Если сумма равна 0, то показываем "Жоқ"
                if total_value == 0:
                    total_value = "0"

                row = table.add_row().cells
                row[0].text = main_indicator.code  # Отображаем код индикатора
                row[1].text = main_indicator.name
                row[2].text = main_indicator.unit  # Отображаем единицу измерения
                row[3].text = str(total_value)  # Отображаем значение
                set_cell_font(row[0], bold=True, align_center=True)
                set_cell_font(row[1], bold=True)
                set_cell_font(row[2], bold=True, align_center=True)
                set_cell_font(row[3], bold=True, align_center=True)

                # Обрабатываем подиндикаторы для главного индикатора
                indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)

                for indicator in indicators:
                    value = TeacherReport.objects.filter(
                        teacher=teacher, indicator=indicator, year=year
                    ).aggregate(Sum('value'))['value__sum'] or 0

                    ind_row = table.add_row().cells
                    ind_row[0].text = f'{indicator.code}'  # Отображаем код индикатора
                    ind_row[1].text = indicator.name
                    ind_row[2].text = indicator.unit  # Отображаем единицу измерения
                    ind_row[3].text = str(value)  # Отображаем значение
                    set_cell_font(ind_row[0], align_center=True)
                    set_cell_font(ind_row[1])
                    set_cell_font(ind_row[2], align_center=True)
                    set_cell_font(ind_row[3], align_center=True)
            if direction != directions.last():
                doc.add_page_break()

        # Файлды қайтару
        return generate_docx_response(doc, teacher, year)

# -----====== Dean ======--------
def generate_dean(document, filename_base):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    filename = f"{filename_base}.docx"
    encoded_file_name = quote(filename)
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_file_name}"
    document.save(response)
    return response


def export_report(request, faculty_id):
    """ с учителем """
    year_id = request.GET.get('year')

    if year_id:
        selected_year = Year.objects.get(id=year_id)
    else:
        selected_year = Year.objects.latest('year')

    faculty = Faculty.objects.get(id=faculty_id)
    departments = Department.objects.filter(faculty=faculty)
    directions = Direction.objects.all()

    document = init_document(selected_year, faculty)

    for direction in directions:
        add_direction_title(document, selected_year, faculty, direction)

        table = create_indicator_table(document, departments)

        main_indicators = MainIndicator.objects.filter(direction=direction, years=selected_year).prefetch_related("indicators")

        for main in main_indicators:
            has_sub_indicators = main.indicators.exists()

            if has_sub_indicators:
                sub_indicators = main.indicators.filter(years=selected_year)
                dept_sums = [0] * len(departments)

                for sub in sub_indicators:
                    for idx, dept in enumerate(departments):
                        value = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept,
                            value__gte=1
                        ).aggregate(total=models.Sum('value'))['total'] or 0
                        dept_sums[idx] += value

                summary_row = table.add_row().cells
                summary_row[0].text = f'{main.code}'
                summary_row[1].text = f'{main.name}'
                summary_row[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                summary_row[1].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                for idx, value in enumerate(dept_sums):
                    summary_row[2 + idx].text = str(value)
                summary_row[-1].text = str(sum(dept_sums))


                summary_row[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                summary_row[-1].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

                for sub in sub_indicators:
                    row = table.add_row().cells
                    row[0].text = sub.code
                    row[1].text = sub.name

                    sub_total = 0
                    for idx, dept in enumerate(departments):
                        reports = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept,
                            value__gte=1
                        )
                        cell_text = "\n".join(f"{r.teacher.get_full_name()}: {r.value}" for r in reports)
                        value_sum = sum(r.value for r in reports)
                        sub_total += value_sum
                        row[2 + idx].text = cell_text if cell_text else "—"

                    row[-1].text = str(sub_total)

                    # Выравнивание для "Код" и "Сумма"
                    row[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                    row[-1].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            else:
                row = table.add_row().cells
                row[0].text = main.code
                row[1].text = main.name

                total = 0
                for idx, dept in enumerate(departments):
                    aggr_reports = AggregatedIndicator.objects.filter(
                        main_indicator=main,
                        year=selected_year,
                        teacher__profile__department=dept,
                        total_value__gte=1
                    )
                    values = [(r.teacher.get_full_name(), r.total_value) for r in aggr_reports]
                    cell_text = "\n".join(f"{t[0]}: {t[1]}" for t in values)
                    row[2 + idx].text = cell_text if cell_text else "—"
                    total += sum(val for _, val in values)

                row[-1].text = str(total)

                # Выравнивание для "Код" и "Сумма"
                row[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                row[-1].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        if direction != directions.last():
            document.add_page_break()

    filename_base = f"Факультет есебі - {faculty.name} {selected_year.year} (мұғаліммен)"
    return generate_dean(document, filename_base)


def align_cell_center(cell):
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

# Отчет без списков учителей
@login_required
def export_department_report_docx(request, faculty_id):
    year_id = request.GET.get('year')
    selected_year = Year.objects.get(id=year_id) if year_id else Year.objects.latest('year')

    faculty = Faculty.objects.get(id=faculty_id)
    departments = Department.objects.filter(faculty=faculty)
    directions = Direction.objects.all()

    document = init_document(selected_year, faculty)  # Инициализация документа, с нужным заголовком и форматированием

    for direction in directions:
        add_direction_title(document, selected_year, faculty, direction)  # Добавляем заголовок с новой страницы

        num_depts = len(departments)
        table = document.add_table(rows=1, cols=3 + num_depts)
        table.style = 'Table Grid'

        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Код'
        hdr_cells[1].text = 'Индикатор атауы'
        for idx, dept in enumerate(departments):
            hdr_cells[2 + idx].text = dept.name
        hdr_cells[-1].text = 'Жалпы сумма'

        # Индивидуальные ширины ячеек
        column_widths = [Cm(1), Cm(23)] + [Cm(1) for _ in departments] + [Cm(1)]
        for idx, cell in enumerate(hdr_cells):
            cell.width = column_widths[idx]
            align_cell_center(cell)

        main_indicators = MainIndicator.objects.filter(
            direction=direction, years=selected_year
        ).prefetch_related("indicators")

        for main in main_indicators:
            has_sub_indicators = main.indicators.exists()

            if has_sub_indicators:
                sub_indicators = main.indicators.filter(years=selected_year)
                dept_sums = [0] * num_depts

                for sub in sub_indicators:
                    for idx, dept in enumerate(departments):
                        value = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        ).aggregate(total=Sum('value'))['total'] or 0
                        dept_sums[idx] += value

                summary_row = table.add_row().cells
                summary_row[0].text = f'{main.code}'
                summary_row[1].text = f'Барлығы: {main.name}'
                for idx, value in enumerate(dept_sums):
                    summary_row[2 + idx].text = str(value)
                summary_row[-1].text = str(sum(dept_sums))

                align_cell_center(summary_row[0])
                for idx in range(2, len(summary_row)):
                    align_cell_center(summary_row[idx])

                for sub in sub_indicators:
                    row = table.add_row().cells
                    row[0].text = sub.code
                    row[1].text = sub.name

                    sub_total = 0
                    for idx, dept in enumerate(departments):
                        value = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        ).aggregate(total=Sum('value'))['total'] or 0
                        row[2 + idx].text = str(value)
                        sub_total += value

                    row[-1].text = str(sub_total)

                    align_cell_center(row[0])
                    for idx in range(2, len(row)):
                        align_cell_center(row[idx])

            else:
                row = table.add_row().cells
                row[0].text = main.code
                row[1].text = main.name

                total = 0
                for idx, dept in enumerate(departments):
                    value = AggregatedIndicator.objects.filter(
                        main_indicator=main,
                        year=selected_year,
                        teacher__profile__department=dept
                    ).aggregate(total=Sum('total_value'))['total'] or 0
                    row[2 + idx].text = str(value)
                    total += value

                row[-1].text = str(total)

                align_cell_center(row[0])
                for idx in range(2, len(row)):
                    align_cell_center(row[idx])
        document.add_page_break()

    filename_base = f"Факультет есебі - {faculty.name} {selected_year.year} (мұғалімсіз)"
    return generate_dean(document, filename_base)

