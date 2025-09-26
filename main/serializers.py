from django.contrib.gis import serializers

from main.models import Year


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = "__all__"
        read_only_fields = ("id",)

