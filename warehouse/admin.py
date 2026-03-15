from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html
from import_export import resources

# Правильные импорты от Unfold (исправляют ошибку args or kwargs)
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.decorators import display

from .models import Category, Device, DeviceSpec, AuditLog, Client, Transaction

# --- РЕСУРСЫ ДЛЯ ИМПОРТА/ЭКСПОРТА ---
class DeviceResource(resources.ModelResource):
    class Meta:
        model = Device
        fields = ('id', 'name', 'brand', 'model_name', 'serial_number', 'status', 'condition', 'purchase_price', 'retail_price')

class TransactionResource(resources.ModelResource):
    class Meta:
        model = Transaction

# --- INLINE ДЛЯ ХАРАКТЕРИСТИК (ЗАМЕНА JSON) ---
class DeviceSpecInline(TabularInline):
    model = DeviceSpec
    extra = 1 # Сколько пустых строк показывать по умолчанию
    fields = ['name', 'value']

# --- АДМИНКА КАТЕГОРИЙ ---
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "icon", "color"]
    search_fields = ["name"]
    ordering = ["name"]

# --- АДМИНКА КЛИЕНТОВ ---
@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin, ModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = ["first_name", "last_name", "phone", "email", "created_at"]
    search_fields = ["first_name", "last_name", "phone", "email"]
    list_filter = ["created_at"]

# --- АДМИНКА УСТРОЙСТВ ---
@admin.register(Device)
class DeviceAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = DeviceResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = ["name", "serial_number", "category_badge", "condition_badge", "status_badge", "retail_price", "purchase_date"]
    list_filter = ["status", "condition", "category", "purchase_date"]
    search_fields = ["name", "serial_number", "brand", "model_name"]
    list_per_page = 20
    
    # Добавляем таблицу характеристик внутрь карточки устройства
    inlines = [DeviceSpecInline]
    
    fieldsets = [
        ("Основная информация", {
            "fields": [("name", "category"), ("brand", "model_name"), "serial_number"],
            "classes": ["tab"],
        }),
        ("Финансы и статус", {
            "fields": [("purchase_price", "retail_price"), ("status", "condition"), ("purchase_date", "warranty_months")],
            "classes": ["tab"],
        }),
    ]

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
            'in_stock': 'bg-green-100 text-green-700',
            'sold': 'bg-purple-100 text-purple-700',
            'issued': 'bg-blue-100 text-blue-700',
            'repair': 'bg-red-100 text-red-700',
        }
        labels = dict(Device.STATUS_CHOICES)
        return format_html(f'<span class="px-2.5 py-1 rounded-full text-xs font-medium {colors.get(obj.status, "bg-gray-100")}">{labels.get(obj.status)}</span>')

    @display(description="Состояние")
    def condition_badge(self, obj):
        labels = dict(Device.CONDITION_CHOICES)
        return labels.get(obj.condition)

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Device.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                AuditLog.objects.create(
                    device=obj, user=request.user,
                    action=f"Изменение статуса: {old_obj.get_status_display()} -> {obj.get_status_display()}",
                    old_status=old_obj.status, new_status=obj.status
                )
        super().save_model(request, obj, form, change)

# --- АДМИНКА ТРАНЗАКЦИЙ ---
@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = TransactionResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = ["device", "client", "type_badge", "amount", "manager", "date"]
    list_filter = ["transaction_type", "date", "manager"]
    search_fields = ["device__name", "device__serial_number", "client__first_name", "client__phone"]
    autocomplete_fields = ["device", "client"]
    
    @display(description="Тип")
    def type_badge(self, obj):
        colors = {'sale': 'bg-green-100 text-green-800', 'rent': 'bg-blue-100 text-blue-800', 'return': 'bg-orange-100 text-orange-800'}
        return format_html(f'<span class="px-2.5 py-1 rounded text-xs font-bold {colors.get(obj.transaction_type, "")}">{obj.get_transaction_type_display()}</span>')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.manager = request.user
        super().save_model(request, obj, form, change)

# --- ДАШБОРД ---
def dashboard_callback(request, context):
    total_devices = Device.objects.count()
    in_stock = Device.objects.filter(status='in_stock').count()
    total_sales_amount = Transaction.objects.filter(transaction_type='sale').aggregate(Sum('amount'))['amount__sum'] or 0
    total_clients = Client.objects.count()

    context.update({
        "stats": [
            {"title": "Устройств на складе", "value": in_stock, "icon": "inventory", "color": "green"},
            {"title": "Всего устройств", "value": total_devices, "icon": "devices", "color": "primary"},
            {"title": "Выручка (продажи)", "value": f"{total_sales_amount:,.0f} ₽", "icon": "payments", "color": "purple"},
            {"title": "Клиентов в базе", "value": total_clients, "icon": "groups", "color": "blue"},
        ],
    })
    return context

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ["timestamp", "device", "user", "action"]
    readonly_fields = ["timestamp", "device", "user", "action", "old_status", "new_status"]
    
    def has_add_permission(self, request):
        return False