from modeltranslation.translator import register, TranslationOptions
from .models import Profile, Faculty


@register(Faculty)
class FacultyTranslationOptions(TranslationOptions):
    fields = ('name',)
