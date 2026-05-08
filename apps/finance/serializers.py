from rest_framework import serializers
from .models import MonthlyFinancial


class MonthlyFinancialSerializer(serializers.ModelSerializer):
    profit = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyFinancial
        fields = ['id', 'month', 'revenue', 'expenses', 'profit', 'created_at']

    def get_profit(self, obj):
        return float(obj.profit)
