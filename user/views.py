from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .forms import CustomUserCreationForm, LoginForm, ProfileUpdateForm
from .models import Profile
from django.contrib import messages
from django.utils.translation import gettext as _


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаем профиль и связываем его с пользователем
            Profile.objects.create(
                user=user,
                faculty=form.cleaned_data["faculty"],
                role=form.cleaned_data["role"],
                phone=form.cleaned_data["phone"]
            )
            login(request, user)  # Авторизуем пользователя сразу после регистрации
            return redirect("direction_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "user/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, _("Error: incorrect username or password."))
    else:
        form = LoginForm()

    return render(request, "user/login.html", {"form": form})



def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def edit_profile(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile_edit')
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)

    return render(request, 'user/edit_profile.html', {'form': form})

