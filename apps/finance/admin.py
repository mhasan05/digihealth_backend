from django.contrib import admin
from .models import MonthlyFinancial


@admin.register(MonthlyFinancial)
class MonthlyFinancialAdmin(admin.ModelAdmin):
    list_display    = ('hospital', 'month', 'revenue', 'expenses', 'get_profit', 'created_at')
    list_filter     = ('hospital',)
    search_fields   = ('hospital__name_en', 'month')
    readonly_fields = ('id', 'created_at', 'get_profit')
    raw_id_fields   = ('hospital',)

    @admin.display(description='Profit')
    def get_profit(self, obj):
        return obj.profit
