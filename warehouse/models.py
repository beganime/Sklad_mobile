# warehouse/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    icon = models.CharField("Иконка (HeroIcon name)", max_length=50, default="device-phone-mobile")
    color = models.CharField("Цвет (Hex)", max_length=7, default="#8B5CF6")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

class Device(models.Model):
    STATUS_CHOICES = [
        ('in_stock', 'На складе'),
        ('issued', 'Выдано'),
        ('repair', 'В ремонте'),
    ]

    name = models.CharField("Название устройства", max_length=200)
    serial_number = models.CharField("Серийный номер", max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="devices")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='in_stock')
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    purchase_date = models.DateField("Дата поступления", default=timezone.now)
    
    # Характеристики хранятся в JSON: {"RAM": "16GB", "CPU": "Intel i7"}
    specs = models.JSONField("Характеристики", default=dict, blank=True)

    class Meta:
        verbose_name = "Устройство"
        verbose_name_plural = "Устройства"
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

class AuditLog(models.Model):
    """Логирование действий менеджера"""
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_status = models.CharField(max_length=50, null=True, blank=True)
    new_status = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Лог действий"
        ordering = ['-timestamp']