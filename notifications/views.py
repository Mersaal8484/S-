from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from .models import ChannelProvider, MessageTemplate, Notification, SMSLog
from .forms import ChannelProviderForm, MessageTemplateForm, NotificationForm


@login_required
def notification_list(request):
    notifications = Notification.objects.select_related('template', 'provider').order_by('-created_at')
    query = request.GET.get('q')
    if query:
        notifications = notifications.filter(
            Q(title__icontains=query) |
            Q(recipient__icontains=query)
        )
    status = request.GET.get('status')
    if status:
        notifications = notifications.filter(status=status)

    paginator = Paginator(notifications, 25)
    page = request.GET.get('page')

    return render(request, 'notifications/notification_list.html', {
        'notifications': paginator.get_page(page),
    })


@login_required
def notification_create(request):
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            if notification.status == Notification.Status.PENDING:
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
            notification.save()
            messages.success(request, 'Notification sent')
            return redirect('notification_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = NotificationForm()

    templates = MessageTemplate.objects.filter(is_active=True)
    providers = ChannelProvider.objects.filter(is_active=True)

    return render(request, 'notifications/notification_form.html', {
        'form': form,
        'title': 'Send Notification',
        'templates': templates,
        'providers': providers,
    })


@login_required
def template_list(request):
    templates = MessageTemplate.objects.order_by('name')
    query = request.GET.get('q')
    if query:
        templates = templates.filter(
            Q(name__icontains=query) |
            Q(body__icontains=query)
        )
    channel = request.GET.get('channel')
    if channel:
        templates = templates.filter(channel=channel)

    paginator = Paginator(templates, 25)
    page = request.GET.get('page')

    return render(request, 'notifications/template_list.html', {
        'templates': paginator.get_page(page),
    })


@login_required
def template_create(request):
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.variables = form.clean_variables()
            template.save()
            messages.success(request, 'Template created')
            return redirect('template_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = MessageTemplateForm()

    return render(request, 'notifications/template_form.html', {
        'form': form,
        'title': 'Add Template',
        'template': None,
    })


@login_required
def template_edit(request, pk):
    template = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            template.variables = form.clean_variables()
            template.save()
            messages.success(request, 'Template updated')
            return redirect('template_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = MessageTemplateForm(instance=template)

    return render(request, 'notifications/template_form.html', {
        'form': form,
        'title': 'Edit Template',
        'template': template,
    })


@login_required
def provider_list(request):
    providers = ChannelProvider.objects.order_by('-is_default', 'name')
    query = request.GET.get('q')
    if query:
        providers = providers.filter(
            Q(name__icontains=query) |
            Q(provider_type__icontains=query)
        )
    channel = request.GET.get('channel')
    if channel:
        providers = providers.filter(channel=channel)

    paginator = Paginator(providers, 25)
    page = request.GET.get('page')

    return render(request, 'notifications/provider_list.html', {
        'providers': paginator.get_page(page),
    })


@login_required
def provider_create(request):
    if request.method == 'POST':
        form = ChannelProviderForm(request.POST)
        if form.is_valid():
            provider = form.save()
            if provider.is_default:
                ChannelProvider.objects.filter(
                    channel=provider.channel, is_default=True
                ).exclude(pk=provider.pk).update(is_default=False)
            messages.success(request, 'Provider created')
            return redirect('provider_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ChannelProviderForm()

    return render(request, 'notifications/provider_form.html', {
        'form': form,
        'title': 'Add Provider',
    })


@login_required
def sms_log_list(request):
    logs = SMSLog.objects.select_related('provider').order_by('-created_at')
    query = request.GET.get('q')
    if query:
        logs = logs.filter(
            Q(to_number__icontains=query) |
            Q(body__icontains=query)
        )
    status = request.GET.get('status')
    if status:
        logs = logs.filter(status=status)

    paginator = Paginator(logs, 25)
    page = request.GET.get('page')

    return render(request, 'notifications/sms_log_list.html', {
        'logs': paginator.get_page(page),
    })
