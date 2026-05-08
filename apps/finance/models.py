import uuid
from django.db import models
from apps.hospitals.models import Hospital


class MonthlyFinancial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='financials')
    month = models.CharField(max_length=7)  # YYYY-MM format
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_monthly_financial'
        ordering = ['month']
        unique_together = [['hospital', 'month']]

    @property
    def profit(self):
        return self.revenue - self.expenses

    def __str__(self):
        return f"{self.hospital.name_en} - {self.month}"
