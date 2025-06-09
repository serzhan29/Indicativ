from modeltranslation.translator import register, TranslationOptions
from .models import Direction, MainIndicator, Indicator
from user.models import User, Department, Faculty


@register(Direction)
class DirectionTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Faculty)
class FacultyTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Department)
class DepartmentTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(MainIndicator)
class MainIndicatorTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Indicator)
class IndicatorTranslationOptions(TranslationOptions):
    fields = ('name',)
