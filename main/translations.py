from modeltranslation.translator import register, TranslationOptions

from .models import Direction, TeacherReport, MainIndicator, SubIndicator

@register(Direction)
class DirectionTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(TeacherReport)
class TeacherReportTranslationOptions(TranslationOptions):
    fields = ('subindicator', )

@register(MainIndicator)
class MainIndicationTranslationOptions(TranslationOptions):
    fields = ('name', )

@register(SubIndicator)
class SubIndicationTranslationOptions(TranslationOptions):
    fields = ('name', )