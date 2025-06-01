from modeltranslation.translator import register, TranslationOptions
from .models import Direction


@register(Direction)
class DirectionTranslationOptions(TranslationOptions):
    fields = ('name',)
