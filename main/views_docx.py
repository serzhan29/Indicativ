from django.db.models import Sum
from django.http import HttpResponse
from docx import Document
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from docx.enum.section import WD_ORIENT, WD_ORIENTATION
from docx.shared import RGBColor, Pt, Inches
from docx.oxml.ns import qn
from urllib.parse import quote_plus
from .models import AggregatedIndicator, Direction, Year, Indicator, TeacherReport, User, MainIndicator
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from django.views import View
from urllib.parse import quote


@login_required
def download_teacher_report(request, teacher_id, direction_id, year_id):
    """Генерация отчета в Word с таблицей в альбомном формате"""
    # Получаем учителя по переданному ID
    teacher = get_object_or_404(User, id=teacher_id)  # Получаем учителя по ID
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

    para = doc.add_paragraph(
        f'Инженерия факультетінің деканы ____________________ {teacher.first_name} {teacher.last_name}')
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
    file_name = f"Отчет учителя {teacher.first_name} {teacher.last_name} {year.year}.docx"
    encoded_file_name = quote_plus(file_name)
    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_file_name}'

    doc.save(response)
    return response

###### Indicator

def indicator_report_view(request):
    try:
        # Получаем параметр года из запроса
        year_id = request.GET.get("year")
        years = Year.objects.all().order_by("-year")

        # Если год передан, то выбираем его, если нет — выбираем первый из списка
        if year_id:
            selected_year = Year.objects.get(id=year_id)
        else:
            selected_year = years.first()

        # Логируем выбранный год
        print(f"Выбранный год: {selected_year.year}")

        # Проверка на наличие направлений
        directions = Direction.objects.all()
        if not directions:
            return HttpResponse("Нет доступных направлений для отчета.", status=404)

        data = []
        for direction in directions:
            direction_data = {
                "name": direction.name,
                "main_indicators": []
            }

            # Получаем основные индикаторы для выбранного года и направления
            main_indicators = MainIndicator.objects.filter(direction=direction, years=selected_year).prefetch_related(
                "indicators")

            for main in main_indicators:
                has_sub_indicators = main.indicators.exists()
                main_data = {
                    "name": main.name,
                    "unit": main.unit,
                    "teachers": [],
                    "total": 0,
                    "sub_indicators": [],
                    "has_sub_indicators": has_sub_indicators
                }

                if has_sub_indicators:
                    # Если подиндикаторы есть, то обрабатываем их
                    for sub in main.indicators.filter(years=selected_year):
                        reports = TeacherReport.objects.filter(indicator=sub, year=selected_year)
                        teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.value) for r in reports]
                        total = sum(v for _, v in teacher_values)

                        sub_data = {
                            "name": sub.name,
                            "unit": sub.unit,
                            "teachers": teacher_values,
                            "total": total
                        }

                        main_data["sub_indicators"].append(sub_data)
                else:
                    # Если подиндикаторов нет, смотрим агрегированные значения
                    aggr_reports = AggregatedIndicator.objects.filter(main_indicator=main, year=selected_year)
                    teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.total_value) for r in
                                      aggr_reports]
                    total = sum(v for _, v in teacher_values)

                    main_data["teachers"] = teacher_values
                    main_data["total"] = total

                direction_data["main_indicators"].append(main_data)

            data.append(direction_data)

        # Суммируем по подиндикаторам
        for direction in data:
            for main in direction['main_indicators']:
                if main['has_sub_indicators']:
                    main['sub_total_sum'] = sum(sub['total'] for sub in main['sub_indicators'])

        # Создаем документ Word
        doc = Document()
        doc.add_heading(f"Отчет за {selected_year.year} год", 0)

        for direction in data:
            doc.add_heading(direction['name'], level=1)

            for main in direction['main_indicators']:
                doc.add_heading(main['name'], level=2)
                doc.add_paragraph(f"Единица измерения: {main['unit']}")

                if main['has_sub_indicators']:
                    doc.add_paragraph(f"Итого по подиндикаторам: {main['sub_total_sum']}")
                    for sub in main['sub_indicators']:
                        doc.add_paragraph(f"{sub['name']} ({sub['unit']}) - Сумма: {sub['total']}")
                else:
                    doc.add_paragraph(f"Итого: {main['total']}")

        # Возвращаем файл Word
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="report_{selected_year.year}.docx"'
        doc.save(response)

        return response
    except Exception as e:
        # Логируем ошибку и возвращаем сообщение
        print(f"Ошибка при создании отчета: {e}")
        return HttpResponse("Произошла ошибка при создании отчета", status=500)


def set_cell_font(cell, bold=False, align_center=False):
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if align_center else WD_ALIGN_PARAGRAPH.LEFT
        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
            run.font.size = Pt(12)
            run.font.bold = bold
            run.font.color.rgb = None  # чёрный


class TeacherReportWordExportView(View):
    def get(self, request, *args, **kwargs):
        year_id = request.GET.get('year')
        teacher_id = request.GET.get('teacher')

        if not year_id:
            return HttpResponse("Оқу жылы көрсетілмеген", status=400)

        year = get_object_or_404(Year, id=year_id)
        teacher = get_object_or_404(User, id=teacher_id) if teacher_id else request.user
        directions = Direction.objects.all().order_by('id')

        next_year = year.year +1

        # Получаем факультет из профиля
        faculty_name = (
            teacher.profile.faculty.name
            if hasattr(teacher, 'profile') and teacher.profile.faculty
            else "Факультет"
        )

        doc = Document()

        # Альбом бет
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        new_width, new_height = section.page_height, section.page_width
        section.page_width = new_width
        section.page_height = new_height
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)

        # Бастапқы бет
        doc.add_paragraph("Қожа Ахмет Ясауи атындағы Халықаралық қазақ-түрік университеті").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(
            "«БЕКІТЕМІН»\nСапа бойынша басшылық өкілі, Ғылым және стратегиялық даму вице-ректоры\n"
            f"__________________________ А.Ошибаева\n«____» _______________ {year.year}ж."
        ).alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Пустые строки для вертикальной центрировки
        for _ in range(6):
            doc.add_paragraph("")

        doc.add_paragraph(f"{faculty_name} факультетінің").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"{year.year} - {next_year} оқу жылына").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("ИНДИКАТИВТІ ЖОСПАРЫ").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("\nТүркістан").alignment = WD_ALIGN_PARAGRAPH.CENTER

        for direction in directions:
            # Отдельная страница - заголовок направления
            doc.add_page_break()

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

            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Индикатор'
            hdr_cells[1].text = 'Мәні'
            set_cell_font(hdr_cells[0], bold=True)
            set_cell_font(hdr_cells[1], bold=True, align_center=True)

            for main_indicator in main_indicators:
                indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)

                total_value = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).aggregate(Sum('value'))['value__sum'] or 0

                row = table.add_row().cells
                row[0].text = main_indicator.name
                row[1].text = str(total_value)
                set_cell_font(row[0], bold=True)
                set_cell_font(row[1], bold=True, align_center=True)

                for indicator in indicators:
                    value = TeacherReport.objects.filter(
                        teacher=teacher, indicator=indicator, year=year
                    ).aggregate(Sum('value'))['value__sum'] or 0

                    ind_row = table.add_row().cells
                    ind_row[0].text = f'– {indicator.name}'
                    ind_row[1].text = str(value)
                    set_cell_font(ind_row[0])
                    set_cell_font(ind_row[1], align_center=True)

        # Файлды қайтару
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        file_name = f"Мұғалім {teacher.last_name} {teacher.first_name} - {year.year}ж.docx"
        encoded_file_name = quote(file_name)
        response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_file_name}'
        doc.save(response)
        return response
