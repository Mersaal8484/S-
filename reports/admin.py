from django.contrib import admin
from .models import ReportDefinition, ReportExecution


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_scheduled', 'is_active', 'created_at']
    list_filter = ['report_type', 'is_scheduled', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['report', 'status', 'row_count', 'duration_seconds', 'executed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['report__name']
    readonly_fields = ['started_at', 'completed_at', 'created_at']
