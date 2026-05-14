from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ReportDefinition(models.Model):
    """تعريفات التقارير القابلة للتخصيص"""
    
    REPORT_TYPES = [
        ('kpi', 'مؤشرات الأداء'),
        ('consumption', 'تقرير الاستهلاك'),
        ('collection', 'تقرير المحصلين'),
        ('invoicing', 'تقرير الفواتير'),
        ('notifications', 'تقرير الإشعارات'),
        ('financial', 'تقرير مالي'),
        ('custom', 'تقرير مخصص'),
    ]
    
    name = models.CharField('اسم التقرير', max_length=200)
    report_type = models.CharField('نوع التقرير', max_length=20, choices=REPORT_TYPES)
    description = models.TextField('الوصف', blank=True)
    
    # Configuration
    filters = models.JSONField('فلاتر', default=dict, blank=True)
    columns = models.JSONField('الأعمدة', default=list, blank=True)
    aggregations = models.JSONField('التجميعات', default=dict, blank=True)
    
    # Schedule
    is_scheduled = models.BooleanField('مجدول', default=False)
    schedule_frequency = models.CharField('التكرار', max_length=20, blank=True)  # daily, weekly, monthly
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField('نشط', default=True)
    
    class Meta:
        db_table = 'report_definitions'
        verbose_name = 'تعريف تقرير'
        verbose_name_plural = 'تعريفات التقارير'
        ordering = ['-created_at']
    
    def __str__(self):
      return self.name


class ReportExecution(models.Model):
    """سجل تنفيذ التقارير"""
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('running', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
    ]
    
    report = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Execution details
    started_at = models.DateTimeField('بدء التنفيذ', null=True, blank=True)
    completed_at = models.DateTimeField('انتهاء التنفيذ', null=True, blank=True)
    duration_seconds = models.IntegerField('المدة (ثواني)', null=True, blank=True)
    
    # Results
    result_data = models.JSONField('بيانات النتيجة', default=dict, blank=True)
    row_count = models.IntegerField('عدد الصفوف', default=0)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    # File output
    file_path = models.CharField('مسار الملف', max_length=500, blank=True)
    file_format = models.CharField('صيغة الملف', max_length=10, blank=True)  # pdf, xlsx, csv
    
    # Execution context
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'report_executions'
        verbose_name = 'تنفيذ تقرير'
        verbose_name_plural = 'تنفيذات التقارير'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report.name} - {self.get_status_display()}"
