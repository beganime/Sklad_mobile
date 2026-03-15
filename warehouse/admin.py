# warehouse/admin.py
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Category, Device, AuditLog
from django import forms
from unfold.widgets import UnfoldAdminSplitDateTimeWidget, UnfoldAdminTextInputWidget

# --- ВИДЖЕТ ДЛЯ JSON (Красивые теги) ---
class SpecsWidget(forms.Textarea):
    class Media:
        js = ('warehouse/js/specs_editor.js',) # Скрипт для парсинга JSON в форму
        css = {'all': ('warehouse/css/specs_editor.css',)}

    def render(self, name, value, attrs=None, renderer=None):
        # Преобразуем dict в строку для textarea, но в UI сделаем красиво через JS/CSS
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        return super().render(name, value, attrs, renderer)

import json

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "icon", "color"]
    search_fields = ["name"]
    ordering = ["name"]

@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    # Настройка списка
    list_display = ["name", "serial_number", "category_badge", "status_badge", "price", "purchase_date"]
    list_filter = ["status", "category", "purchase_date"]
    search_fields = ["name", "serial_number", "specs"]
    list_per_page = 20
    
    # Поля для детального просмотра
    fieldsets = [
        (None, {
            "fields": ["name", "serial_number", "category", "status", "price", "purchase_date"],
            "classes": ["w-full", "lg:w-2/3"],
        }),
        ("Характеристики", {
            "fields": ["specs"],
            "classes": ["collapse", "w-full", "lg:w-2/3"],
            "description": "Введите JSON или используйте редактор пар ключ-значение."
        }),
    ]
    
    formfield_overrides = {
        # models.JSONField: {"widget": SpecsWidget}, # Можно подключить кастомный виджет
    }

    # Кастомные колонки
    @display(description="Категория", ordering="category__name")
    def category_badge(self, obj):
        if obj.category:
            color = obj.category.color
            return format_html(
                f'<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium" style="background-color: {color}20; color: {color}; border: 1px solid {color}40;">'
                f'<span class="material-icons text-[14px]">{obj.category.icon}</span> {obj.category.name}'
                f'</span>'
            )
        return "-"

    @display(description="Статус")
    def status_badge(self, obj):
        colors = {
            'in_stock': 'bg-green-100 text-green-700 border-green-200',
            'issued': 'bg-blue-100 text-blue-700 border-blue-200',
            'repair': 'bg-red-100 text-red-700 border-red-200',
        }
        labels = dict(Device.STATUS_CHOICES)
        return format_html(
            f'<span class="px-2.5 py-1 rounded-full text-xs font-medium border {colors.get(obj.status, "bg-gray-100")}">'
            f'{labels.get(obj.status)}'
            f'</span>'
        )

    # Массовые действия
    actions = ["mark_as_repair", "mark_as_issued", "export_csv"]

    @admin.action(description="Перевести в ремонт")
    def mark_as_repair(self, request, queryset):
        queryset.update(status='repair')
        self.log_action(request, queryset, "Массовое изменение статуса: В ремонт")

    @admin.action(description="Выдать со склада")
    def mark_as_issued(self, request, queryset):
        queryset.update(status='issued')
        self.log_action(request, queryset, "Массовое изменение статуса: Выдано")

    def log_action(self, request, queryset, action_text):
        # Простое логирование (можно расширить до модели AuditLog)
        pass 

    def save_model(self, request, obj, form, change):
        # Логирование изменений
        if change:
            old_obj = Device.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                AuditLog.objects.create(
                    device=obj,
                    user=request.user,
                    action=f"Изменение статуса с {old_obj.get_status_display()} на {obj.get_status_display()}",
                    old_status=old_obj.status,
                    new_status=obj.status
                )
        super().save_model(request, obj, form, change)

# --- DASHBOARD CALLBACK ---
def dashboard_callback(request, context):
    """
    Добавляет статистику в контекст дашборда Unfold
    """
    total_devices = Device.objects.count()
    in_stock = Device.objects.filter(status='in_stock').count()
    repair = Device.objects.filter(status='repair').count()
    issued = Device.objects.filter(status='issued').count()
    
    # Топ категорий
    top_categories = Category.objects.annotate(device_count=Count('devices')).order_by('-device_count')[:5]

    context.update({
        "stats": [
            {"title": "Всего устройств", "value": total_devices, "icon": "inventory_2", "color": "primary"},
            {"title": "На складе", "value": in_stock, "icon": "check_circle", "color": "green"},
            {"title": "В ремонте", "value": repair, "icon": "build", "color": "red"},
            {"title": "Выдано", "value": issued, "icon": "handyman", "color": "blue"},
        ],
        "top_categories": top_categories
    })
    return context

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ["timestamp", "device", "user", "action"]
    readonly_fields = ["timestamp", "device", "user", "action", "old_status", "new_status"]
    
    def has_add_permission(self, request):
        return False