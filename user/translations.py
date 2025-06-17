from modeltranslation.translator import register, TranslationOptions
from .models import Faculty


@register(Faculty)
class FacultyTranslationOptions(TranslationOptions):
    fields = ('name',)
