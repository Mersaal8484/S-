from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Integration, IntegrationConfig, IntegrationLog
from .forms import IntegrationForm, IntegrationConfigForm


@login_required
def integration_list(request):
    integrations = Integration.objects.filter(is_active=True).order_by('name')
    categories = Integration.Category.choices

    return render(request, 'integrations/integration_list.html', {
        'integrations': integrations,
        'categories': categories,
    })


@login_required
def integration_register(request):
    if request.method == 'POST':
        form = IntegrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Integration registered successfully')
            return redirect('integration_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = IntegrationForm()

    return render(request, 'integrations/integration_form.html', {
        'form': form,
        'title': 'Register New Integration',
        'categories': Integration.Category.choices,
    })


@login_required
def integration_detail(request, pk):
    integration = get_object_or_404(Integration, pk=pk)
    configs = integration.configs.filter(is_active=True).order_by('-is_default', 'name')

    return render(request, 'integrations/integration_detail.html', {
        'integration': integration,
        'configs': configs,
    })


@login_required
def integration_config_create(request, integration_pk):
    integration = get_object_or_404(Integration, pk=integration_pk)

    if request.method == 'POST':
        form = IntegrationConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.integration = integration
            config.save()
            messages.success(request, 'Configuration added successfully')
            return redirect('integration_detail', pk=integration.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = IntegrationConfigForm()

    return render(request, 'integrations/config_form.html', {
        'form': form,
        'title': f'Add Configuration - {integration.name}',
        'integration': integration,
        'config': None,
        'auth_types': IntegrationConfig.AuthType.choices,
    })


@login_required
def integration_config_edit(request, pk):
    config = get_object_or_404(IntegrationConfig, pk=pk)
    integration = config.integration

    if request.method == 'POST':
        form = IntegrationConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuration updated successfully')
            return redirect('integration_detail', pk=integration.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = IntegrationConfigForm(instance=config)

    return render(request, 'integrations/config_form.html', {
        'form': form,
        'title': f'Edit Configuration - {config.name}',
        'integration': integration,
        'config': config,
        'auth_types': IntegrationConfig.AuthType.choices,
    })


@login_required
def integration_config_delete(request, pk):
    config = get_object_or_404(IntegrationConfig, pk=pk)
    integration = config.integration

    if request.method == 'POST':
        config.delete()
        messages.success(request, 'Configuration deleted')
        return redirect('integration_detail', pk=integration.pk)

    return render(request, 'integrations/config_confirm_delete.html', {
        'config': config,
        'integration': integration,
    })


@login_required
def integration_logs(request, config_pk):
    config = get_object_or_404(IntegrationConfig, pk=config_pk)
    logs = IntegrationLog.objects.filter(config=config).order_by('-created_at')

    paginator = Paginator(logs, 25)
    page = request.GET.get('page')

    return render(request, 'integrations/integration_logs.html', {
        'config': config,
        'logs': paginator.get_page(page),
    })
