from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from .forms import CustomUserCreationForm, LoginForm
from .models import Profile
from django.contrib import messages
from django.shortcuts import render, redirect
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