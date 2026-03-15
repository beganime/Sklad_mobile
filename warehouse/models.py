# warehouse/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    icon = models.CharField("Иконка (Material Icon)", max_length=50, default="devices")
    color = models.CharField("Цвет (Hex)", max_length=7, default="#8B5CF6")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

class Device(models.Model):
    STATUS_CHOICES = [
        ('in_stock', 'На складе'),
        ('issued', 'Выдано/Продано'),
        ('repair', 'В ремонте'),
        ('write_off', 'Списано'),
    ]

    name = models.CharField("Название устройства", max_length=200)
    serial_number = models.CharField("Серийный номер", max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="devices")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='in_stock')
    price = models.DecimalField("Цена закупки", max_digits=10, decimal_places=2)
    sale_price = models.DecimalField("Цена продажи", max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField("Дата поступления", default=timezone.now)
    
    # Поле "Кому продан/выдан"
    customer = models.CharField("Кому выдан/Продан (ФИО/Компания)", max_length=200, blank=True, null=True)
    issue_date = models.DateTimeField("Дата выдачи", null=True, blank=True)

    class Meta:
        verbose_name = "Устройство"
        verbose_name_plural = "Устройства"
        ordering = ['-purchase_date']

    def clean(self):
        # Валидация: если статус 'issued', поле customer обязательно
        if self.status == 'issued' and not self.customer:
            raise ValidationError({"customer": "Укажите кому выдано устройство при статусе 'Выдано'."})
        
        # Если статус 'in_stock', очищаем поле customer
        if self.status == 'in_stock':
            self.customer = None
            self.issue_date = None

    def save(self, *args, **kwargs):
        self.clean()
        if self.status == 'issued' and not self.issue_date:
            self.issue_date = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

class Characteristic(models.Model):
    """
    Отдельная модель для характеристик.
    Позволяет добавлять неограниченное кол-во пар Ключ-Значение через админку.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="characteristics")
    key = models.CharField("Название (например, RAM)", max_length=100)
    value = models.CharField("Значение (например, 16GB)", max_length=200)

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики устройства"
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value}"

class AuditLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_status = models.CharField(max_length=50, null=True, blank=True)
    new_status = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Лог действий"
        ordering = ['-timestamp']