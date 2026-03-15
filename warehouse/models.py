from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

class Client(models.Model):
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Формат: '+99999999999'. До 15 цифр.")
    phone = models.CharField("Телефон", validators=[phone_regex], max_length=17, unique=True)
    email = models.EmailField("Email", blank=True, null=True)
    address = models.TextField("Адрес", blank=True)
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"

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
        ('sold', 'Продано'),
        ('issued', 'Выдано (Аренда)'),
        ('repair', 'В ремонте'),
    ]
    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('used', 'Б/У'),
        ('refurbished', 'Восстановленное'),
    ]

    name = models.CharField("Название устройства", max_length=200)
    brand = models.CharField("Бренд", max_length=100, blank=True)
    model_name = models.CharField("Модель", max_length=100, blank=True)
    serial_number = models.CharField("IMEI / Серийный номер", max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="devices", verbose_name="Категория")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='in_stock')
    condition = models.CharField("Состояние", max_length=20, choices=CONDITION_CHOICES, default='new')
    
    purchase_price = models.DecimalField("Закупочная цена", max_digits=10, decimal_places=2, help_text="Для внутреннего учета")
    retail_price = models.DecimalField("Цена продажи", max_digits=10, decimal_places=2)
    
    purchase_date = models.DateField("Дата поступления", default=timezone.now)
    warranty_months = models.PositiveIntegerField("Гарантия (мес)", default=12)
    
    # Поле specs убрано, теперь характеристики хранятся в DeviceSpec

    class Meta:
        verbose_name = "Устройство"
        verbose_name_plural = "Устройства"
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

# --- НОВАЯ МОДЕЛЬ ДЛЯ ХАРАКТЕРИСТИК ---
class DeviceSpec(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="specifications", verbose_name="Устройство")
    name = models.CharField("Название характеристики", max_length=100, help_text="Например: Память, Цвет, Процессор")
    value = models.CharField("Значение", max_length=255, help_text="Например: 256 ГБ, Черный, Apple M1")

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"

    def __str__(self):
        return f"{self.name}: {self.value}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('sale', 'Продажа'),
        ('rent', 'Аренда'),
        ('return', 'Возврат'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='transactions', verbose_name="Устройство")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='transactions', verbose_name="Клиент")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Менеджер")
    transaction_type = models.CharField("Тип операции", max_length=20, choices=TYPE_CHOICES, default='sale')
    amount = models.DecimalField("Сумма операции", max_digits=10, decimal_places=2)
    date = models.DateTimeField("Дата операции", auto_now_add=True)
    notes = models.TextField("Примечание", blank=True)

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Журнал операций"
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if self.pk is None:
            if self.transaction_type == 'sale':
                self.device.status = 'sold'
            elif self.transaction_type == 'rent':
                self.device.status = 'issued'
            elif self.transaction_type == 'return':
                self.device.status = 'in_stock'
            self.device.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.device.name}"

class AuditLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_status = models.CharField(max_length=50, null=True, blank=True)
    new_status = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Системный лог"
        verbose_name_plural = "Системные логи"
        ordering = ['-timestamp']